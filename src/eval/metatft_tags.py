"""Doi chieu bang feature augment voi nhan tag cua MetaTFT (audit, KHONG phai ground truth).

NGUON
    GET https://api-hc.metatft.com/tft-stat-api/augments_tiers?tft_set=TFTSet18
    truong content.content.tags: apiName -> chuoi tag cach nhau dau phay, lay trong
    {combat, items, econ, trait, scaling, misc}. Mot augment co 0..3 tag; thu tu giu nguyen
    vi tag dau tien thuong la nhan "chinh".

GIOI HAN PHAI NEU TRONG BAO CAO
    - Day la nhan CHU QUAN do mot nguoi (META Spencer) gan, khong co tai lieu dinh nghia.
      Bat dong voi MetaTFT la TIN HIEU de doc lai mo ta augment, khong phai bang chung loi.
    - Hai bo nhan khong cung tu vung: ta co categories (1-3 nhan, categories[0] = category
      chinh) + tempo + econ_value, MetaTFT co multi-label. CATEGORY_TO_TAG la anh xa gan
      dung, vd reroll -> econ. Tag `scaling` khong co category tuong ung nen phep so tap
      hop chi cham cac tag anh xa duoc (SET_LABELS).

Module nay chi doc file va tinh so; khong goi mang. Crawl o scripts/crawl_metatft_tags.py.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

VALID_TAGS = ("combat", "items", "econ", "trait", "scaling", "misc")

# category cua ta -> tag MetaTFT gan nghia nhat (anh xa gan dung, xem docstring)
CATEGORY_TO_TAG = {
    "econ": "econ",
    "combat": "combat",
    "trait": "trait",
    "item": "items",
    "utility": "misc",
    "reroll": "econ",
}

# Tag MetaTFT ma categories cua ta co the sinh ra qua CATEGORY_TO_TAG.
SET_LABELS = tuple(sorted(set(CATEGORY_TO_TAG.values())))

SNAPSHOT_NOTE = (
    "Subjective expert labeling by MetaTFT (META Spencer), undocumented. "
    "Audit signal only, NOT ground truth."
)


class MetaTFTTagError(ValueError):
    """Payload hoac snapshot tag khong dung dinh dang."""


def parse_tags(payload: Mapping[str, Any]) -> dict[str, list[str]]:
    """Tach map apiName -> list tag tu payload augments_tiers.

    Chap nhan ca payload day du (content.content.tags) lan dang da boc (content.tags / tags).
    Tag rong bi bo; tag la (ngoai VALID_TAGS) lam fail to, vi do la dau hieu API doi schema.
    """
    raw = None
    inner = payload.get("content")
    if isinstance(inner, dict):
        deeper = inner.get("content")
        if isinstance(deeper, dict) and isinstance(deeper.get("tags"), dict):
            raw = deeper["tags"]
        elif isinstance(inner.get("tags"), dict) and inner["tags"]:
            raw = inner["tags"]
    if raw is None and isinstance(payload.get("tags"), dict) and payload["tags"]:
        raw = payload["tags"]
    if not raw:
        raise MetaTFTTagError("Payload khong chua map 'tags' hop le")

    out: dict[str, list[str]] = {}
    for api_name, value in raw.items():
        tags = [t.strip() for t in str(value or "").split(",") if t.strip()]
        unknown = [t for t in tags if t not in VALID_TAGS]
        if unknown:
            raise MetaTFTTagError(f"Tag la {unknown} o {api_name}")
        out[str(api_name)] = tags
    return out


def build_snapshot(
    tags: Mapping[str, list[str]],
    catalog: list[str] | set[str],
    meta: Mapping[str, Any],
) -> dict[str, Any]:
    """Chi giu tag cua apiName co trong catalog; ghi lai cac augment MetaTFT khong co."""
    catalog_set = set(catalog)
    kept = {k: list(tags[k]) for k in sorted(catalog_set) if k in tags}
    missing = sorted(catalog_set - set(tags))
    return {
        "meta": {
            **meta,
            "note": meta.get("note", SNAPSHOT_NOTE),
            "n_catalog": len(catalog_set),
            "n_tagged": len(kept),
            "missing_from_metatft": missing,
        },
        "tags": kept,
    }


def load_snapshot(path: str | Path) -> dict[str, list[str]]:
    """Doc data/augment_tags.metatft.json -> map apiName -> list tag."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    tags = data.get("tags")
    if not isinstance(tags, dict):
        raise MetaTFTTagError(f"{path}: thieu truong 'tags'")
    for api_name, value in tags.items():
        if not isinstance(value, list) or any(t not in VALID_TAGS for t in value):
            raise MetaTFTTagError(f"{path}: tag sai dinh dang o {api_name}: {value!r}")
    return {k: list(v) for k, v in tags.items()}


@dataclass(frozen=True)
class BinaryCheck:
    name: str
    tag: str
    tp: int
    fp: int
    fn: int
    tn: int
    fp_names: tuple[str, ...] = ()
    fn_names: tuple[str, ...] = ()

    @property
    def n(self) -> int:
        return self.tp + self.fp + self.fn + self.tn

    @property
    def agree(self) -> float:
        return (self.tp + self.tn) / self.n if self.n else 0.0


@dataclass(frozen=True)
class LabelPRF:
    """Precision/recall/F1 cua MOT tag tren phep so tap hop categories vs tag MetaTFT."""

    tag: str
    tp: int
    fp: int
    fn: int

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if p + r else 0.0


def _primary(v: Mapping[str, Any]) -> str | None:
    """Nhan chinh dang chuoi (an toan de lam khoa dict du row loi ghi list vao category)."""
    cats = _categories(v)
    return cats[0] if cats else None


def _categories(v: Mapping[str, Any]) -> list[str]:
    """categories cua row; row cu chi co `category` thi coi nhu mot nhan."""
    cats = v.get("categories")
    if isinstance(cats, (list, tuple)) and cats:
        return [str(c) for c in cats]
    cat = v.get("category")
    if isinstance(cat, (list, tuple)):
        return [str(c) for c in cat]
    return [str(cat)] if cat is not None else []


def predicted_tags(v: Mapping[str, Any]) -> frozenset[str]:
    """Tap tag MetaTFT suy tu categories (reroll va econ cung ve `econ`)."""
    return frozenset(CATEGORY_TO_TAG[c] for c in _categories(v) if c in CATEGORY_TO_TAG)


def jaccard(a: frozenset[str] | set[str], b: frozenset[str] | set[str]) -> float:
    """|A giao B| / |A hop B|; hai tap rong coi nhu khop hoan toan."""
    union = a | b
    return len(a & b) / len(union) if union else 1.0


@dataclass
class Comparison:
    n: int
    category_in_tags: int
    category_is_first_tag: int
    confusion: dict[str, Counter] = field(default_factory=dict)
    checks: list[BinaryCheck] = field(default_factory=list)
    mismatches: list[tuple[str, dict[str, Any], list[str]]] = field(default_factory=list)
    by_method: dict[str, tuple[int, int]] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    # So tap hop categories vs tag MetaTFT (chi tren SET_LABELS)
    set_jaccard: float = 0.0
    set_exact: int = 0
    label_prf: dict[str, LabelPRF] = field(default_factory=dict)
    set_by_method: dict[str, tuple[float, int]] = field(default_factory=dict)

    def check(self, name: str) -> BinaryCheck:
        for c in self.checks:
            if c.name == name:
                return c
        raise KeyError(name)


# (ten, vi tu tren row feature, tag MetaTFT) - ten dung lam khoa on dinh trong test/doc
CHECKS: list[tuple[str, Callable[[dict[str, Any]], bool], str]] = [
    ("econ_value>0 vs econ", lambda v: (v.get("econ_value") or 0) > 0, "econ"),
    ("tempo==scaling vs scaling", lambda v: v.get("tempo") == "scaling", "scaling"),
    ("trait_affinity vs trait", lambda v: bool(v.get("trait_affinity")), "trait"),
    # trait_count_reward (vertical/wide) phu augment thuong theo so trait ma
    # trait_affinity (chi trait cu the) khong thay.
    (
        "trait_affinity|count_reward vs trait",
        lambda v: bool(v.get("trait_affinity")) or bool(v.get("trait_count_reward")),
        "trait",
    ),
    ("category==trait vs trait", lambda v: _primary(v) == "trait", "trait"),
    ("item_grants vs items", lambda v: bool(v.get("item_grants")), "items"),
    ("category==item vs items", lambda v: _primary(v) == "item", "items"),
    ("category==combat vs combat", lambda v: _primary(v) == "combat", "combat"),
    (
        "category==econ/reroll vs econ",
        lambda v: _primary(v) in ("econ", "reroll"),
        "econ",
    ),
]


def compare(
    features: Mapping[str, dict[str, Any]],
    tags: Mapping[str, list[str]],
) -> Comparison:
    """Tinh do dong thuan giua bang feature va tag MetaTFT tren cac apiName chung."""
    rows = [(k, v, tags[k]) for k, v in sorted(features.items()) if k in tags]
    n = len(rows)
    in_tags = sum(CATEGORY_TO_TAG.get(_primary(v)) in ts for _, v, ts in rows)
    first = sum(bool(ts) and CATEGORY_TO_TAG.get(_primary(v)) == ts[0] for _, v, ts in rows)

    confusion: dict[str, Counter] = defaultdict(Counter)
    for _, v, ts in rows:
        for t in ts or ["(none)"]:
            confusion[_primary(v)][t] += 1

    checks = []
    for name, pred, tag in CHECKS:
        tp, fp, fn, tn = 0, 0, 0, 0
        fp_names, fn_names = [], []
        for k, v, ts in rows:
            p, t = pred(v), tag in ts
            if p and t:
                tp += 1
            elif p:
                fp += 1
                fp_names.append(k)
            elif t:
                fn += 1
                fn_names.append(k)
            else:
                tn += 1
        checks.append(BinaryCheck(name, tag, tp, fp, fn, tn, tuple(fp_names), tuple(fn_names)))

    mismatches = [
        (k, v, ts) for k, v, ts in rows if CATEGORY_TO_TAG.get(_primary(v)) not in ts
    ]
    mismatches.sort(key=lambda r: (str(_primary(r[1])), str(r[1].get("name", r[0]))))

    by_method: dict[str, tuple[int, int]] = {}
    for _, v, ts in rows:
        m = str(v.get("extraction_method"))
        hit, total = by_method.get(m, (0, 0))
        by_method[m] = (hit + (CATEGORY_TO_TAG.get(_primary(v)) in ts), total + 1)

    # So tap hop: categories (qua CATEGORY_TO_TAG) vs tag MT, gioi han trong SET_LABELS
    jac_sum, exact = 0.0, 0
    counts = {t: [0, 0, 0] for t in SET_LABELS}   # tp, fp, fn
    jac_by_method: dict[str, list[float]] = defaultdict(list)
    for _, v, ts in rows:
        ours = predicted_tags(v)
        theirs = frozenset(t for t in ts if t in SET_LABELS)
        j = jaccard(ours, theirs)
        jac_sum += j
        exact += ours == theirs
        jac_by_method[str(v.get("extraction_method"))].append(j)
        for t in SET_LABELS:
            if t in ours and t in theirs:
                counts[t][0] += 1
            elif t in ours:
                counts[t][1] += 1
            elif t in theirs:
                counts[t][2] += 1

    return Comparison(
        n=n,
        category_in_tags=in_tags,
        category_is_first_tag=first,
        confusion=dict(confusion),
        checks=checks,
        mismatches=mismatches,
        by_method=by_method,
        missing=sorted(set(features) - set(tags)),
        set_jaccard=jac_sum / n if n else 0.0,
        set_exact=exact,
        label_prf={t: LabelPRF(t, *c) for t, c in counts.items()},
        set_by_method={m: (sum(js) / len(js), len(js)) for m, js in jac_by_method.items()},
    )


def format_report(cmp: Comparison, list_fp: bool = False) -> str:
    """Bao cao text cho terminal / doc luan van."""
    n = cmp.n
    lines = [f"matched {n} augment (thieu tag MetaTFT: {cmp.missing or '-'})"]
    if not n:
        return "\n".join(lines)
    lines.append(
        f"category in MT tags: {cmp.category_in_tags}/{n} = {cmp.category_in_tags / n:.1%}"
    )
    lines.append(
        f"category == MT first tag: {cmp.category_is_first_tag}/{n} = "
        f"{cmp.category_is_first_tag / n:.1%}"
    )
    lines.append("\nconfusion (our category -> MT tags, multi-label):")
    for c in sorted(cmp.confusion, key=str):
        lines.append(f"  {str(c):8s} {dict(cmp.confusion[c].most_common())}")
    lines.append("")
    for c in cmp.checks:
        lines.append(
            f"{c.name:30s} TP={c.tp:3d} FP={c.fp:3d} FN={c.fn:3d} TN={c.tn:3d} agree={c.agree:.1%}"
        )
        if list_fp:
            lines.append(f"    FP: {', '.join(c.fp_names) or '-'}")
            lines.append(f"    FN: {', '.join(c.fn_names) or '-'}")
    lines.append("\nMISMATCH (category not in MT tags):")
    for k, v, ts in cmp.mismatches:
        lines.append(
            f"  {str(v.get('name', k))[:30]:30s} ours={'+'.join(_categories(v)):20s} "
            f"econ={v.get('econ_value')} tempo={str(v.get('tempo')):9s} "
            f"conf={v.get('confidence')} via={str(v.get('extraction_method'))[:12]:12s} "
            f"MT={','.join(ts) or '-'}"
        )
    lines.append(
        "\nby extraction_method: "
        + ", ".join(f"{m}={h}/{t}" for m, (h, t) in sorted(cmp.by_method.items()))
    )
    lines.append(
        f"\nSET categories vs MT tags (tren {','.join(SET_LABELS)}; scaling bo qua):"
    )
    lines.append(f"mean Jaccard: {cmp.set_jaccard:.3f}")
    lines.append(f"exact set match: {cmp.set_exact}/{n} = {cmp.set_exact / n:.1%}")
    for t in SET_LABELS:
        m = cmp.label_prf[t]
        lines.append(
            f"  {t:7s} TP={m.tp:3d} FP={m.fp:3d} FN={m.fn:3d} "
            f"P={m.precision:.1%} R={m.recall:.1%} F1={m.f1:.3f}"
        )
    lines.append(
        "mean Jaccard by extraction_method: "
        + ", ".join(f"{m}={j:.3f} (n={c})" for m, (j, c) in sorted(cmp.set_by_method.items()))
    )
    return "\n".join(lines)
