"""Sinh data/augment_features.json - chay MOT LAN moi set, khong phai moi tran.

    python scripts/build_augment_features.py                     # tang 1, khong can key
    python scripts/build_augment_features.py --llm --diff        # xem tang 2 doi gi
    python scripts/build_augment_features.py --llm --write       # ghi de sau khi da xem

Dau ra la file JSON COMMIT vao repo va SUA TAY DUOC. Do la ca diem cua thiet
ke nay: hoi dong cham do an mo file ra doc duoc 254 dong, khong phai tin vao
mot loi goi LLM khong tai lap duoc.

Tang 2 (--llm) khong bao gio ghi de tang 1 mot cach am tham: no ghi
`extraction_method = "gemini-<model>"` va giu nguyen cac truong no khong
quyet duoc, de audit tay biet chinh xac dong nao do may sinh ra.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.knowledge.augment_catalog import AugmentCatalog  # noqa: E402
from src.knowledge.augment_features import (  # noqa: E402
    EXTRACTOR_VERSION,
    AugmentFeature,
    FeatureTable,
    extract_deterministic,
)
from src.knowledge.cdragon_client import CDragonClient  # noqa: E402

DEFAULT_OUT = ROOT / "data" / "augment_features.json"

# Vai tro A trong SPEC 3.5.3 - trich dac trung, chay offline.
EXTRACT_PROMPT = """Cho mo ta mot Augment trong Teamfight Tactics, tra ve JSON PHANG:
{"category": "econ|combat|trait|item|utility|reroll",
 "carry_type": "AD|AP|tank|none",
 "trait_affinity": ["trait_id", ...],
 "econ_value": 0-3,
 "tempo": "immediate|scaling",
 "item_grants": ["component", ...],
 "board_condition": "dieu kien board can co, hoac null"}

Chi dua vao mo ta duoc cung cap. Khong suy doan chi so khong co trong text.
Neu khong xac dinh duoc mot truong, tra ve null - KHONG BIA.
"""


def load_locale(args: argparse.Namespace) -> dict[str, Any]:
    """Nap locale EN tu file chi dinh, hoac tu cache/mang qua CDragonClient."""
    if args.locale_file:
        return json.loads(Path(args.locale_file).read_text(encoding="utf-8"))
    client = CDragonClient(offline=args.offline)
    return client.load_locale(args.locale)


def trait_display_map(locale: dict[str, Any]) -> dict[str, str]:
    """Map ten trait hien thi -> apiName, tu setData cua locale."""
    sets = locale.get("setData") or []
    if not sets:
        return {}
    return {t["name"]: t["apiName"] for t in sets[0].get("traits", [])}


def build_tier1(locale: dict[str, Any]) -> FeatureTable:
    """Trich tang 1 cho toan bo augment trong locale."""
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
        features[aug.api_name] = extract_deterministic(raw, traits, tier=aug.tier)
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
    return {
        "n": len(feats),
        "category": dist("category"),
        "carry_type": dist("carry_type"),
        "tempo": dist("tempo"),
        "econ_value": dist("econ_value"),
        "with_trait_affinity": sum(1 for f in feats if f.trait_affinity),
        "with_item_grants": sum(1 for f in feats if f.item_grants),
        "mean_confidence": round(
            sum(f.confidence for f in feats) / len(feats), 3
        ) if feats else 0.0,
    }


def refine_with_llm(
    table: FeatureTable, locale: dict[str, Any], model: str
) -> tuple[FeatureTable, list[str]]:
    """Tang 2: goi Gemini de tinh chinh. Can GEMINI_API_KEY.

    Import google.genai o TRONG ham, khong o dau file: toan bo tang 1 phai
    chay duoc tren may khong cai google-genai va khong co key.

    Returns:
        (bang moi, danh sach mo ta thay doi)
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit(
            "--llm can GEMINI_API_KEY (hoac GOOGLE_API_KEY) trong bien moi truong. "
            "Tang 1 van chay duoc khong can key - bo co --llm di."
        )
    try:
        from google import genai  # noqa: PLC0415
    except ImportError as exc:
        raise SystemExit(f"chua cai google-genai: {exc}") from exc

    by_api = {
        str(i.get("apiName")): i for i in locale.get("items", []) if i.get("isAugment")
    }
    client = genai.Client(api_key=api_key)
    changes: list[str] = []
    refined = dict(table.features)

    for api_name, feat in table.features.items():
        raw = by_api.get(api_name, {})
        prompt = (
            f"{EXTRACT_PROMPT}\n\nTen: {raw.get('name')}\nMo ta: {raw.get('desc')}\n"
        )
        resp = client.models.generate_content(model=model, contents=prompt)
        parsed = _parse_json_block(getattr(resp, "text", "") or "")
        if not parsed:
            continue
        merged, diff = _merge(feat, parsed, model)
        refined[api_name] = merged
        changes.extend(f"{api_name}: {d}" for d in diff)

    return FeatureTable(refined, table.meta), changes


def _parse_json_block(text: str) -> dict[str, Any] | None:
    """Doc khoi JSON trong cau tra loi cua model. Hong thi tra None, khong crash."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def _merge(
    feat: AugmentFeature, parsed: dict[str, Any], model: str
) -> tuple[AugmentFeature, list[str]]:
    """Gop ket qua LLM vao entry tang 1. Bo qua moi gia tri None hoac sai mien."""
    from src.knowledge.augment_features import CARRY_TYPES, CATEGORIES, TEMPOS

    allowed = {"category": CATEGORIES, "carry_type": CARRY_TYPES, "tempo": TEMPOS}
    data = feat.to_dict()
    diff: list[str] = []

    for key, value in parsed.items():
        if key not in data or value is None:
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

    if diff:
        data["extraction_method"] = f"gemini-{model}"
    return AugmentFeature(**data), diff


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--locale", default="en_us", help="locale nguon (mac dinh en_us)")
    ap.add_argument("--locale-file", help="doc locale tu file thay vi tai ve")
    ap.add_argument("--offline", action="store_true", help="chi doc cache CDragon")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--llm", action="store_true", help="bat tang 2 (can API key)")
    ap.add_argument("--model", default="gemini-2.5-flash-lite")
    ap.add_argument("--diff", action="store_true", help="chi in thay doi, khong ghi")
    ap.add_argument("--write", action="store_true", help="ghi de file dau ra")
    args = ap.parse_args(argv)

    locale = load_locale(args)
    table = build_tier1(locale)
    print(json.dumps(summarize(table), indent=2, ensure_ascii=False))

    if args.llm:
        table, changes = refine_with_llm(table, locale, args.model)
        print(f"\ntang 2 doi {len(changes)} truong:")
        for line in changes[:50]:
            print("  ", line)
        if len(changes) > 50:
            print(f"   ... con {len(changes) - 50} dong nua")

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
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump(table.to_payload(meta), fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"\nda ghi {len(table)} augment -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
