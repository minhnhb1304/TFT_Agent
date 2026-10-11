#!/usr/bin/env python
"""Ap nhan duyet tay (augment_feature_review.json) vao bang feature.

Nhan tay cua mot loi = `original` (nhan luc duyet) de `fix` len tren. Chi loi co
verdict ok/wrong duoc ap; "unsure" giu nguyen dong may. Chi cac truong trong
MANUAL_AUDITABLE duoc ghi, va truong nao doi thi khai trong label
"manual-audit:<truong,...> (from <method goc>)" de build_augment_features.py
--write giu lai (keep_manual_audits).

KHONG ap `item_grants` / `trait_affinity`: day la truong dinh danh, luon sinh lai
tu tang 1 (test_committed_table_is_reproducible), va nhan tay dung ca key chi co
o trang duyet (ComponentAnvil, Artifact, RadiantItem...). Script chi dem va in
cac loi nay. Tach `Anvil` + them key moi la viec rieng, xem docs/next-steps.md.

    python scripts/apply_manual_review.py            # chi in bao cao
    python scripts/apply_manual_review.py --write    # ghi de bang feature
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from review_augment_features import migrate_review  # noqa: E402
from src.knowledge.augment_features import (  # noqa: E402
    MANUAL_AUDITABLE,
    AugmentFeature,
    check_feature,
    mandatory_categories,
    parse_manual_audit,
)

DEFAULT_FEATURES = ROOT / "data" / "augment_features.json"
DEFAULT_REVIEW = ROOT / "data" / "eval" / "augment_feature_review.json"
APPLIED_VERDICTS = ("ok", "wrong")
# Truong nguoi duyet sua duoc tren trang nhung bang khong nhan sua tay.
IDENTITY_FIELDS = ("item_grants", "trait_affinity")


def manual_labels(entry: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    """Nhan tay cua mot loi: original + fix, theo schema hien tai."""
    e = migrate_review(entry, row)
    labels = dict(e.get("original") or {})
    labels.update(e.get("fix") or {})
    if labels.get("categories"):
        labels["category"] = labels["categories"][0]
    return labels


def origin_kind(method: str) -> str:
    """Nhom nguon cua mot dong: llm / deterministic / manual-audit (da audit truoc do)."""
    if parse_manual_audit(method):
        return "manual-audit"
    return "llm" if method.startswith("llm:") else "deterministic"


def apply_review(
    payload: dict[str, Any], reviews: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """(payload moi, bao cao). Khong sua `payload` dau vao."""
    out = json.loads(json.dumps(payload))
    report: dict[str, Any] = {
        "applied": {}, "skipped_unsure": [], "not_reviewed": [], "identity": {},
        "forced": {}, "invalid": {}, "agree": Counter(), "total": Counter(),
    }
    for api, row in out["augments"].items():
        entry = reviews.get(api)
        if entry is None:
            report["not_reviewed"].append(api)
            continue
        if entry.get("verdict") not in APPLIED_VERDICTS:
            report["skipped_unsure"].append(api)
            continue
        labels = manual_labels(entry, row)
        method = str(row["extraction_method"])
        kind = origin_kind(method)
        changed = []
        for f in MANUAL_AUDITABLE:
            if f not in labels:
                continue
            same = labels[f] == row[f]
            report["total"][(kind, f)] += 1
            report["agree"][(kind, f)] += same
            if not same:
                changed.append(f)
        ident = {f: labels[f] for f in IDENTITY_FIELDS if f in labels and labels[f] != row[f]}
        if ident:
            report["identity"][api] = ident
        # Truong dinh danh khong ap, nen nhan bat buoc cua no phai o lai: nguoi duyet
        # bo `item` cung luc xoa item_grants thi bang van con item_grants.
        missing = [c for c in mandatory_categories(
            labels.get("econ_value", row["econ_value"]), row["item_grants"],
            row["trait_affinity"], row["trait_count_reward"],
        ) if c not in labels.get("categories", row["categories"])]
        if missing:
            labels["categories"] = [*labels.get("categories", row["categories"]), *missing]
            report["forced"][api] = missing
            if labels["categories"] == row["categories"] and "categories" in changed:
                changed.remove("categories")
        if not changed:
            continue
        audit = parse_manual_audit(method)
        fields = set(audit[0] if audit else ()) | set(changed)
        # Da cham vao nhan chinh hoac tap nhan thi khai ca hai: keep_manual_audits
        # chep `categories` nguyen van, khong ghep lai tu tang 1.
        if fields & {"category", "categories"}:
            fields |= {"category", "categories"}
        for f in changed:
            row[f] = labels[f]
        row["category"] = row["categories"][0]
        origin = audit[1] if audit else method
        row["extraction_method"] = f"manual-audit:{','.join(sorted(fields))} (from {origin})"
        errs = check_feature(AugmentFeature(**row))
        if errs:
            report["invalid"][api] = errs
        report["applied"][api] = changed
    return out, report


def format_report(report: dict[str, Any], names: dict[str, str]) -> str:
    lines = [
        f"ap nhan tay: {len(report['applied'])} dong doi | unsure bo qua: "
        f"{len(report['skipped_unsure'])} | chua duyet: {len(report['not_reviewed'])}",
        "truong doi: " + ", ".join(
            f"{f}={n}" for f, n in Counter(
                f for fs in report["applied"].values() for f in fs).most_common()),
        "",
        "do khop cua bang TRUOC khi ap, theo nguon dong (so dong khop nhan tay / so dong duyet):",
    ]
    kinds = sorted({k for k, _ in report["total"]})
    lines.append("  " + f"{'truong':16s}" + "".join(f"{k:>22s}" for k in kinds))
    for f in MANUAL_AUDITABLE:
        cells = []
        for k in kinds:
            n = report["total"][(k, f)]
            a = report["agree"][(k, f)]
            cells.append(f"{a}/{n} = {a / n:.1%}" if n else "-")
        lines.append("  " + f"{f:16s}" + "".join(f"{c:>22s}" for c in cells))
    if report["skipped_unsure"]:
        lines += ["", "unsure (giu dong may): " + ", ".join(names[a] for a in report["skipped_unsure"])]
    if report["identity"]:
        lines += ["", f"KHONG ap {len(report['identity'])} loi sua truong dinh danh "
                      f"({', '.join(IDENTITY_FIELDS)}):"]
        lines += [f"  {names[a]}: {v}" for a, v in report["identity"].items()]
    if report["forced"]:
        lines += ["", "GIU nhan bat buoc ma nguoi duyet da bo (bang van con truong dinh danh do):"]
        lines += [f"  {names[a]}: +{', '.join(v)}" for a, v in report["forced"].items()]
    if report["invalid"]:
        lines += ["", f"VI PHAM BAT BIEN sau khi ap ({len(report['invalid'])}):"]
        lines += [f"  {names[a]}: {'; '.join(v)}" for a, v in report["invalid"].items()]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--features", default=str(DEFAULT_FEATURES))
    ap.add_argument("--review", default=str(DEFAULT_REVIEW))
    ap.add_argument("--write", action="store_true", help="ghi de bang feature")
    args = ap.parse_args(argv)

    path = Path(args.features)
    payload = json.loads(path.read_text(encoding="utf-8"))
    reviews = json.loads(Path(args.review).read_text(encoding="utf-8"))["reviews"]
    out, report = apply_review(payload, reviews)
    names = {a: r["name"] for a, r in payload["augments"].items()}
    print(format_report(report, names))

    if report["invalid"]:
        print("\ncon vi pham bat bien: khong ghi", file=sys.stderr)
        return 1
    if not args.write:
        print("\nchua ghi file. Them --write de ghi de.")
        return 0
    with io.open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"\nda ghi {len(out['augments'])} augment -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
