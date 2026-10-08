"""Sinh data/augment_features.json - chay MOT LAN moi set, khong phai moi tran.

    python scripts/build_augment_features.py                     # tang 1, khong can key
    python scripts/build_augment_features.py --llm --diff        # xem tang 2 doi gi
    python scripts/build_augment_features.py --llm --write       # ghi de sau khi da xem
    python scripts/build_augment_features.py --offline --migrate --write
                                                # doi sang extractor moi, KHONG goi LLM

Dau ra la file JSON COMMIT vao repo va SUA TAY DUOC. Do la ca diem cua thiet
ke nay: hoi dong cham do an mo file ra doc duoc 254 dong, khong phai tin vao
mot loi goi LLM khong tai lap duoc.

Tang 2 (--llm) khong bao gio ghi de tang 1 mot cach am tham: no ghi
`extraction_method = "gemini-<model>"` va giu nguyen cac truong no khong
quyet duoc, de audit tay biet chinh xac dong nao do may sinh ra.

--migrate (khong goi mang/LLM): sinh lai tang 1 bang extractor hien tai,
roi lay PHAN DOAN LLM cua file cu cho cac dong "llm:..." (ke ca dong audit
"(from llm:...)"): category cu lam nhan chinh, cac truong LLM_REFINABLE giu
nguyen (carry_type "tank" cu -> "none" + frontline). Truong suy dien
(categories = nhan chinh + nhan bat buoc + goi y tang 1; frontline = tang 1
HOAC "tank" cu/frontline cu) tinh lai theo luat. Dong tang 1 sinh lai het,
dong audit tay ap lai nhu moi lan ghi. Chay lai --migrate tren chinh file ra
phai cho ra file y het (test_committed_table_is_reproducible khoa dieu nay).
Dung khi doi EXTRACTOR_VERSION ma khong muon (hoac khong duoc) goi lai LLM.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.knowledge.augment_catalog import AugmentCatalog  # noqa: E402
from src.knowledge.augment_features import (  # noqa: E402
    CATEGORIES,
    EXTRACTOR_VERSION,
    AugmentFeature,
    FeatureTable,
    compose_categories,
    extract_deterministic,
    load_offer_rounds,
    mandatory_categories,
    parse_manual_audit,
)
from src.knowledge.cdragon_client import CDragonClient, select_set_data  # noqa: E402
from src.utils.env import load_env  # noqa: E402

DEFAULT_OUT = ROOT / "data" / "augment_features.json"
# Luot chao augment (datatft, may chu CN). Xem docs/offer-rounds/source.md.
DEFAULT_ROUNDS = ROOT / "data" / "augment_rounds.datatft.json"

# Vai tro A trong SPEC 3.5.3 - trich dac trung, chay offline.
EXTRACT_PROMPT = """Cho mo ta mot Augment trong Teamfight Tactics, tra ve JSON PHANG:
{"carry_type": "AD|AP|both|none",
 "trait_affinity": ["trait_id", ...],
 "econ_value": 0-3,
 "tempo": "immediate|scaling",
 "item_grants": ["component", ...],
 "board_condition": "dieu kien board can co, hoac null"}

Chi dua vao mo ta duoc cung cap. Khong suy doan chi so khong co trong text.
Neu khong xac dinh duoc mot truong, tra ve null - KHONG BIA.

carry_type: huong carry SAT THUONG ma augment phuc vu. "AD" / "AP"; "both" khi
cho ro ca chi so phia AD lan phia AP, hoac buff "carry/tuong manh nhat" bat ke
loai sat thuong; "none" cho buff chung ca doi hoac chi so chong chiu (mau,
giap, khang phep, khien, hoi mau) - "tank" KHONG phai huong carry.

tempo: do bang SO VONG DAU, khong phai so giay trong mot tran.
- "scaling": phan lon gia tri den TRE hon ~3 vong - tich luy qua cac vong
  (moi vong/moi stage/moi lan len cap, cong don vinh vien), hoac phan thuong
  cho moc xa (dat cap 8-9, sau N tran, sau khi tieu X mana/sat thuong).
- "immediate": phan lon gia tri co ngay hoac trong ~3 vong toi. Cong don
  TRONG mot tran ("moi 2 giay", "sau 12 giay giao tranh", "het tran") van la
  immediate vi tran sau da co du. Chi so theo board hien tai (moi trait, moi
  dong minh chung trait) cung la immediate.
- Nua nay nua kia (VD 2 mon bay gio + 1 mon sau 6 tran) -> immediate.

trait_affinity: dung TEN TRAIT tieng Anh nhu hien trong game (VD "Riftbeast").
Neu mo ta khong nhac den trait nao thi tra ve null, KHONG tra ve [].

item_grants: bo qua truong nay, dieu phoi vien tu tinh.

econ_value: CHI tinh vang, XP, reroll/gia tri shop (ke ca tuong duoc tang va
Champion Duplicator, quy ra vang). Item, component, emblem, anvil, Thief's Gloves, Reforger KHONG
tinh - chung da nam o item_grants. Augment chi cho item -> econ_value = 0.
Thang do theo tong gia tri quy ra vang: 0 = khong co; 1 = duoi 8; 2 = 8-19;
3 = tu 20 tro len hoac tang lai (interest).
"""


def load_locale(args: argparse.Namespace) -> dict[str, Any]:
    """Nap locale EN tu file chi dinh, hoac tu cache/mang qua CDragonClient."""
    if args.locale_file:
        return json.loads(Path(args.locale_file).read_text(encoding="utf-8"))
    client = CDragonClient(offline=args.offline)
    return client.load_locale(args.locale)


def trait_display_map(locale: dict[str, Any]) -> dict[str, str]:
    """Map ten trait hien thi -> apiName, tu setData cua Set 18.

    Phai di qua select_set_data: ban locale DAY DU co 35 khoi setData va
    khoi dau tien la TFTSet14. Xem cdragon_client.select_set_data.
    """
    return {t["name"]: t["apiName"] for t in select_set_data(locale).get("traits", [])}


def build_tier1(
    locale: dict[str, Any], offer_rounds: dict[str, list[str]] | None = None
) -> FeatureTable:
    """Trich tang 1 cho toan bo augment trong locale.

    `offer_rounds` (api_name -> luot chao, tu load_offer_rounds) la truong
    DINH DANH: chep thang tu snapshot, khong suy tu van ban. Khong truyen
    hoac thieu augment -> [] (chua biet).
    """
    offer_rounds = offer_rounds or {}
    catalog = AugmentCatalog(locale)
    traits = trait_display_map(locale)
    by_api = {
        str(i.get("apiName")): i
        for i in locale.get("items", [])
        if i.get("isAugment")
    }

    features: dict[str, AugmentFeature] = {}
    for aug in catalog.augments:
        raw = by_api.get(aug.api_name, {})
        feat = extract_deterministic(raw, traits, tier=aug.tier)
        feat.offer_rounds = list(offer_rounds.get(aug.api_name, []))
        features[aug.api_name] = feat
    return FeatureTable(features)


def summarize(table: FeatureTable) -> dict[str, Any]:
    """Thong ke phan bo - in ra de nguoi doc danh gia bang co hop ly khong."""
    def dist(attr: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for f in table.features.values():
            key = str(getattr(f, attr))
            out[key] = out.get(key, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))

    feats = list(table.features.values())
    n_labels: dict[str, int] = {}
    for f in feats:
        k = str(len(f.categories))
        n_labels[k] = n_labels.get(k, 0) + 1
    return {
        "n": len(feats),
        "category": dist("category"),
        "categories_label": {c: sum(1 for f in feats if c in f.categories) for c in CATEGORIES},
        "categories_count": dict(sorted(n_labels.items())),
        "carry_type": dist("carry_type"),
        "frontline": sum(1 for f in feats if f.frontline),
        "tempo": dist("tempo"),
        "econ_value": dist("econ_value"),
        "with_trait_affinity": sum(1 for f in feats if f.trait_affinity),
        "with_item_grants": sum(1 for f in feats if f.item_grants),
        "trait_count_reward": dist("trait_count_reward"),
        "offer_rounds": dist("offer_rounds"),
        "mean_confidence": round(
            sum(f.confidence for f in feats) / len(feats), 3
        ) if feats else 0.0,
    }


def refine_with_llm(
    table: FeatureTable, locale: dict[str, Any], model: str, limit: int = 0
) -> tuple[FeatureTable, list[str]]:
    """Tang 2: goi Gemini de tinh chinh. Can GEMINI_API_KEY.

    Import google.genai o TRONG ham, khong o dau file: toan bo tang 1 phai
    chay duoc tren may khong cai google-genai va khong co key.

    Returns:
        (bang moi, danh sach mo ta thay doi)
    """
    # Doc .env neu co. Bien da co san trong moi truong van thang file.
    load_env()
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit(
            "--llm can GEMINI_API_KEY (hoac GOOGLE_API_KEY) trong file .env o thu muc "
            "goc, hoac trong bien moi truong. Tang 1 van chay duoc khong can key - "
            "bo co --llm di."
        )
    try:
        from google import genai  # noqa: PLC0415
    except ImportError as exc:
        raise SystemExit(f"chua cai google-genai: {exc}") from exc

    by_api = {
        str(i.get("apiName")): i for i in locale.get("items", []) if i.get("isAugment")
    }
    traits = trait_display_map(locale)
    client = genai.Client(api_key=api_key)
    changes: list[str] = []
    refined = dict(table.features)

    items = list(table.features.items())
    if limit:
        items = items[:limit]

    failed: list[str] = []
    for i, (api_name, feat) in enumerate(items, start=1):
        raw = by_api.get(api_name, {})
        prompt = (
            f"{EXTRACT_PROMPT}\n\nTen: {raw.get('name')}\nMo ta: {raw.get('desc')}\n"
        )

        text = _call_with_retry(client, model, prompt)
        if text is None:
            # Mot augment hong khong duoc lam mat ca luot chay. Tang 1 cua no
            # van dung, chi la khong duoc tinh chinh - va ta ghi lai la ai.
            failed.append(api_name)
        else:
            parsed = _parse_json_block(text)
            if parsed:
                merged, diff = _merge(feat, parsed, model, traits)
                refined[api_name] = merged
                changes.extend(f"{api_name}: {d}" for d in diff)

        if i % 10 == 0 or i == len(items):
            print(
                f"  tang 2: {i}/{len(items)}  |  {len(changes)} thay doi  "
                f"|  {len(failed)} loi",
                flush=True,
            )

    if failed:
        print(f"\n{len(failed)} augment goi that bai, giu nguyen tang 1:")
        for api_name in failed[:20]:
            print(f"   {api_name}")
        if len(failed) > 20:
            print(f"   ... con {len(failed) - 20} nua")

    return FeatureTable(refined, table.meta), changes


def _call_with_retry(client: Any, model: str, prompt: str, attempts: int = 3) -> str | None:
    """Goi model, lui dan khi loi. Tra None neu chiu thua - KHONG nem.

    Mot lan goi hong giua chung khong duoc lam mat 253 ket qua da co: tang 1
    cua augment do van dung, no chi khong duoc tinh chinh.
    """
    for attempt in range(attempts):
        try:
            resp = client.models.generate_content(model=model, contents=prompt)
            return getattr(resp, "text", "") or ""
        except Exception as exc:  # noqa: BLE001 - SDK nem nhieu loai, doi het
            if attempt == attempts - 1:
                # In CA NOI DUNG loi, khong chi ten kieu. Loi 404 cua Gemini
                # noi thang model nao thay the model da bi go - nuot mat cau
                # do thi phai di doan, va do la mot lan da mat thoi gian that.
                print(
                    f"    bo qua sau {attempts} lan thu: {type(exc).__name__}: "
                    f"{str(exc)[:300]}",
                    flush=True,
                )
                return None
            time.sleep(2.0 * (attempt + 1))
    return None


def _parse_json_block(text: str) -> dict[str, Any] | None:
    """Doc khoi JSON trong cau tra loi cua model. Hong thi tra None, khong crash."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


# Cac truong tang 2 DUOC PHEP ghi de. Day la danh sach TRANG - moi truong
# khac bi bo qua du model co tra ve.
#
# Vi sao phai gioi han (do duoc tren 8 augment dau, 2026-09-01):
#
#   trait_affinity: ['DA_Riftbeast18'] -> []
#   item_grants:    ['AnyComponent'] -> ['component','component','component',...]
#
# Hai truong nay chua apiName lay tu du lieu CO CAU TRUC (bang trait cua
# setData, va COMPONENT_PATTERNS). Model khong the biet `DA_Riftbeast18` hay
# `BFSword` la chuoi gi, nen no tra ve chuoi tieng Anh chung chung hoac rong
# - tuc la XOA mat du lieu tang 1 VON DA DUNG.
#
# Nguyen tac chung: LLM chi duoc dung cho phan PHAN DOAN doc tu van ban mo
# ta. Phan dinh danh thi luon lay tu du lieu co cau truc.
#
# offer_rounds KHONG o day: no la du lieu cua nguon ngoai (snapshot datatft),
# khong doc duoc tu mo ta. Chi doi bang crawl lai hoac audit tay.
#
# category/categories/frontline KHONG o day (blind-spots.md §2: LLM ghi de
# 13/13 nhan reroll). category = categories[0] nen LLM sua category tuc la
# sua categories. Nhan chi doi bang luat tang 1 hoac audit tay.
LLM_REFINABLE = ("carry_type", "tempo", "econ_value", "board_condition")


def _merge(
    feat: AugmentFeature,
    parsed: dict[str, Any],
    model: str,
    traits: dict[str, str] | None = None,
) -> tuple[AugmentFeature, list[str]]:
    """Gop ket qua LLM vao entry tang 1. Bo qua moi gia tri None hoac sai mien.

    `traits` la bang ten trait hien thi -> apiName. Neu truyen vao thi
    trait_affinity do model de xuat duoc chap nhan CHI KHI moi phan tu anh xa
    duoc ve mot trait apiName co that. Khong anh xa duoc thi giu nguyen tang 1.
    """
    from src.knowledge.augment_features import CARRY_TYPES, TEMPOS

    allowed = {"carry_type": CARRY_TYPES, "tempo": TEMPOS}
    data = feat.to_dict()
    diff: list[str] = []

    for key, value in parsed.items():
        if key not in LLM_REFINABLE or key not in data or value is None:
            continue
        if key in allowed and value not in allowed[key]:
            continue
        if key == "econ_value":
            try:
                value = max(0, min(3, int(value)))
            except (TypeError, ValueError):
                continue
        if data[key] != value:
            diff.append(f"{key}: {data[key]!r} -> {value!r}")
            data[key] = value

    mapped = _map_trait_affinity(parsed.get("trait_affinity"), traits or {})
    if mapped is not None and mapped != data["trait_affinity"]:
        diff.append(f"trait_affinity: {data['trait_affinity']!r} -> {mapped!r}")
        data["trait_affinity"] = mapped

    if diff:
        # `model` da chua ten nha cung cap ("gemini-3.5-flash-lite"), nen
        # them tien to "gemini-" nua se ra "gemini-gemini-...".
        data["extraction_method"] = f"llm:{model}"
        _restore_mandatory(data)
    return AugmentFeature(**data), diff


def _mandatory(data: dict[str, Any]) -> list[str]:
    return mandatory_categories(
        data["econ_value"], data["item_grants"], data["trait_affinity"],
        data["trait_count_reward"],
    )


def _restore_mandatory(data: dict[str, Any]) -> None:
    """Giu bat bien nhan bat buoc sau khi truong cau truc doi (vd econ_value).

    Nhan chinh giu nguyen; day la suy dien theo luat, khong phai LLM ghi nhan.
    """
    cats = data["categories"]
    data["categories"] = compose_categories(cats[0], _mandatory(data), cats[1:])
    data["category"] = data["categories"][0]


def _origin(method: str) -> str:
    """Method goc cua mot dong: bo vo "manual-audit:... (from X)" neu co."""
    audit = parse_manual_audit(method)
    return audit[1] if audit else method


def carry_llm_judgements(
    table: FeatureTable, previous: dict[str, Any]
) -> tuple[FeatureTable, list[str]]:
    """--migrate: lay phan doan LLM cua file cu len bang tang 1 vua sinh.

    Voi moi dong co goc "llm:..." trong file cu: cac truong LLM_REFINABLE lay
    tu file cu (doc qua AugmentFeature nen carry_type "tank" da thanh "none" +
    frontline), category cu lam nhan chinh. Phan con lai lay tu tang 1:
    categories = nhan chinh + bat buoc + nhan tang 1 lam goi y; frontline =
    tang 1 HOAC frontline cu (nen chay lai lan hai khong lam mat co "tank").
    Khong goi LLM - khong co gi tai lap kem hon file cu.

    Han che: phep HOAC lam frontline cua dong LLM chi bat, khong tat. Neu sua
    luat extract_frontline thi phai --migrate lai tu file TRUOC lan migrate
    dau (git), khong phai tu file da migrate.
    """
    feats = dict(table.features)
    carried: list[str] = []
    for api, row in previous.get("augments", {}).items():
        origin = _origin(str(row.get("extraction_method", "")))
        if not origin.startswith("llm:") or api not in feats:
            continue
        old = AugmentFeature(**row)
        fresh = feats[api]
        data = fresh.to_dict()
        for f in LLM_REFINABLE:
            data[f] = getattr(old, f)
        data["frontline"] = fresh.frontline or old.frontline
        data["categories"] = compose_categories(old.category, _mandatory(data), fresh.categories)
        data["category"] = data["categories"][0]
        data["extraction_method"] = origin
        feats[api] = AugmentFeature(**data)
        carried.append(api)
    return FeatureTable(feats, table.meta), carried


def _map_trait_affinity(value: Any, traits: dict[str, str]) -> list[str] | None:
    """Doi trait do model de xuat thanh apiName. None = khong chap nhan.

    Chap nhan ca apiName san (`DA_Riftbeast18`) lan ten hien thi (`Riftbeast`).
    Chi mot phan tu khong anh xa duoc la BO CA DANH SACH: mot trait_affinity
    dung mot nua con nguy hiem hon rong, vi BoardFit se tin no.

    Danh sach rong bi tu choi thang - do gan nhu luon la model "khong biet"
    chu khong phai "augment nay that su khong gan trait nao", va chap nhan no
    se xoa mat du lieu tang 1 dung.
    """
    if not isinstance(value, list) or not value or not traits:
        return None

    known = set(traits.values())
    out: list[str] = []
    for raw in value:
        name = str(raw).strip()
        if name in known:
            out.append(name)
        elif name in traits:
            out.append(traits[name])
        else:
            return None
    return sorted(set(out))


def keep_manual_audits(
    table: FeatureTable, previous: dict[str, Any]
) -> tuple[FeatureTable, list[str]]:
    """Ap lai cac dong "manual-audit:" cua file cu len bang vua sinh.

    Chi chep cac truong ghi trong label; moi truong khac lay tu bang moi, va
    "(from ...)" ghi lai method cua dong moi. Khong co buoc nay thi moi lan
    --write xoa sach quyet dinh audit ma khong test nao bao.
    """
    kept: list[str] = []
    feats = dict(table.features)
    for api, row in previous.get("augments", {}).items():
        parsed = parse_manual_audit(str(row.get("extraction_method", "")))
        if parsed is None or api not in feats:
            continue
        fields, _ = parsed
        data = feats[api].to_dict()
        origin = data["extraction_method"]
        for f in fields:
            data[f] = row[f]
        if "categories" in fields:
            data["category"] = data["categories"][0]
        else:
            # Chi audit `category` (nhan chinh) hoac truong cau truc: giu nhan
            # chinh do, nhan con lai tu bang moi, va bu nhan bat buoc.
            primary = data["category"] if "category" in fields else data["categories"][0]
            data["categories"] = compose_categories(primary, _mandatory(data), data["categories"])
            data["category"] = data["categories"][0]
        if data["carry_type"] == "tank":
            # Dong audit cu ghi carry_type "tank": doi o day thay vi de
            # AugmentFeature lam, vi frontline co the cung nam trong label.
            data["carry_type"] = "none"
            data["frontline"] = data["frontline"] or "frontline" not in fields
        data["extraction_method"] = f"manual-audit:{','.join(fields)} (from {origin})"
        feats[api] = AugmentFeature(**data)
        kept.append(api)
    return FeatureTable(feats, table.meta), kept


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--locale", default="en_us", help="locale nguon (mac dinh en_us)")
    ap.add_argument("--locale-file", help="doc locale tu file thay vi tai ve")
    ap.add_argument("--offline", action="store_true", help="chi doc cache CDragon")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument(
        "--rounds-file",
        default=str(DEFAULT_ROUNDS),
        help="snapshot luot chao (crawl_datatft_augments.py). Thieu file -> offer_rounds rong",
    )
    ap.add_argument("--llm", action="store_true", help="bat tang 2 (can API key)")
    ap.add_argument("--model", default="gemini-3.5-flash-lite")
    ap.add_argument(
        "--limit",
        type=int,
        default=0,
        help="tang 2: chi xu ly N augment dau. 0 = het. Dung de thu truoc khi chay ca 254.",
    )
    ap.add_argument(
        "--migrate",
        action="store_true",
        help="giu phan doan LLM cua file --out cu, tinh lai truong suy dien; khong goi LLM",
    )
    ap.add_argument("--diff", action="store_true", help="chi in thay doi, khong ghi")
    ap.add_argument("--write", action="store_true", help="ghi de file dau ra")
    args = ap.parse_args(argv)

    locale = load_locale(args)
    offer_rounds = load_offer_rounds(args.rounds_file)
    if not offer_rounds:
        print(f"CANH BAO: khong co {args.rounds_file} - offer_rounds de rong", file=sys.stderr)
    table = build_tier1(locale, offer_rounds)
    print(json.dumps(summarize(table), indent=2, ensure_ascii=False))

    if args.llm:
        table, changes = refine_with_llm(table, locale, args.model, limit=args.limit)
        print(f"\ntang 2 doi {len(changes)} truong:")
        for line in changes[:50]:
            print("  ", line)
        if len(changes) > 50:
            print(f"   ... con {len(changes) - 50} dong nua")

    out = Path(args.out)
    previous = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    if args.migrate:
        if args.llm:
            raise SystemExit("--migrate va --llm loai tru nhau")
        if not previous:
            raise SystemExit(f"--migrate can file cu: {out} khong ton tai")
        table, carried = carry_llm_judgements(table, previous)
        print(f"\ngiu phan doan LLM cua {len(carried)} dong tu {out.name}")

    if previous:
        table, kept = keep_manual_audits(table, previous)
        print(f"\ngiu {len(kept)} dong manual-audit tu {out.name}")
    if args.migrate:
        # Thong ke o dau la cua tang 1 thuan; day moi la bang se ghi.
        print("\nsau --migrate:")
        print(json.dumps(summarize(table), indent=2, ensure_ascii=False))

    if args.diff and not args.write:
        print("\n--diff: khong ghi file. Them --write de ghi de.")
        return 0

    meta = {
        "set": "TFTSet18",
        "source_locale": args.locale,
        # Ghi ro doc tu dau: fixture hay ban tai ve. Bang nay duoc commit va
        # audit tay, nen nguoi doc phai truy nguoc duoc nguon cua tung dong.
        "source_file": args.locale_file or f"cdragon:{args.locale}",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "extractor_version": EXTRACTOR_VERSION,
        "llm_refined": bool(args.llm),
        "n": len(table),
    }
    if args.migrate:
        old_meta = previous.get("meta", {})
        meta["llm_refined"] = bool(old_meta.get("llm_refined"))
        if "llm_model" in old_meta:
            meta["llm_model"] = old_meta["llm_model"]
        meta["migrated_from"] = old_meta.get("migrated_from") or old_meta.get("extractor_version")
    out.parent.mkdir(parents=True, exist_ok=True)
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump(table.to_payload(meta), fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"\nda ghi {len(table)} augment -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
