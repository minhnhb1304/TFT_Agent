"""Crawl bang tier augment tu MetaTFT -> data/augment_tiers.metatft.json (SPEC 3.4, Nhiem vu 5).

    python scripts/crawl_metatft_tiers.py
    python scripts/crawl_metatft_tiers.py --overwrite
    python scripts/crawl_metatft_tiers.py --dry-run

VI SAO CRAWL DUOC
    MetaTFT cung cap REST API noi bo cong khai:
        https://api-hc.metatft.com/tft-stat-api/augments_tiers?tft_set=TFTSet18
    chua danh sach loi xep theo S/A/B/C cua META Spencer (MetaTFT).
    Ma loi dung truc tiep ma Riot apiName (DA_...), khong can phai mapping tay.

PROVENANCE
    Xep hang boi META Spencer (MetaTFT).
    Thuoc tinh sample_n luon 0, is_ordinal luon True.
    Dong vai tro nguon du phong thu hai sau TFT Academy.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.knowledge.metatft import (  # noqa: E402
    TIERLIST_PAGE_URL,
    MetaTFTClient,
    MetaTFTError,
    build_tierlist_payload,
    format_raw_text,
    parse_tierlist_augments,
)
from src.knowledge.stats_provider import ExpertTierListProvider  # noqa: E402

DEFAULT_OUT = ROOT / "data" / "augment_tiers.metatft.json"
DEFAULT_RAW_OUT = ROOT / "data" / "augment_tiers.metatft_raw.txt"
DEFAULT_FEATURES = ROOT / "data" / "augment_features.json"
DEFAULT_TFTACADEMY = ROOT / "data" / "augment_tiers.json"

MISSING_TARGETS = [
    "DA_18_InfernoTraitAugment",
    "DA_18_SprykinAugment",
    "DA_BuildABud",
    "DA_CalculatedLoss",
    "DA_ComponentBuffet",
    "DA_ConstructACompanion",
    "DA_DoubleTrouble",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crawl bang tier augment tu MetaTFT lam nguon du phong"
    )
    parser.add_argument("--set", type=int, default=18, help="So thu tu Set (mac dinh 18)")
    parser.add_argument(
        "--stage",
        default="All",
        help="Giai doan can lay (mac dinh: All)",
    )
    parser.add_argument(
        "--rated-by",
        default="MetaTFT (META Spencer)",
        help="Nguoi danh gia, ghi vao provenance",
    )
    parser.add_argument(
        "--patch",
        default=None,
        help="Patch cua bang tier (mac dinh tu dong lay tu MetaTFT games API hoac fallback 18.1d)",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help=f"Duong dan file JSON dau ra (mac dinh: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--raw-out",
        default=str(DEFAULT_RAW_OUT),
        help=f"Duong dan file text tho (mac dinh: {DEFAULT_RAW_OUT})",
    )
    parser.add_argument(
        "--no-raw",
        action="store_true",
        help="Khong ghi file text tho",
    )
    parser.add_argument(
        "--features",
        default=str(DEFAULT_FEATURES),
        help="Duong dan data/augment_features.json de doi chieu apiName",
    )
    parser.add_argument(
        "--tftacademy-tiers",
        default=str(DEFAULT_TFTACADEMY),
        help="Duong dan data/augment_tiers.json de so sanh do phu du phong",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Ghi de len file neu da ton tai",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chi crawl va in ket qua thong ke, khong ghi file",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    out_path = Path(args.out)
    raw_out_path = Path(args.raw_out) if not args.no_raw else None

    if not args.dry_run:
        if out_path.exists() and not args.overwrite:
            print(
                f"File {out_path} da ton tai. Them --overwrite de ghi de.",
                file=sys.stderr,
            )
            return 1

    print(f"Dang ket noi den MetaTFT (Set {args.set})...")
    client = MetaTFTClient()

    try:
        raw_payload = client.get_augments_tierlist(args.set)
    except MetaTFTError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    patch_info = client.get_patch_info()
    detected_patch = patch_info.get("patch") or "18.1d"
    patch = args.patch or detected_patch

    try:
        tiers = parse_tierlist_augments(raw_payload)
    except MetaTFTError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    total_augs = sum(len(v) for v in tiers.values())
    print(f"Da thu thap {total_augs} augment tu MetaTFT:")
    for t in ExpertTierListProvider.TIER_PLACEMENT:
        if t in tiers:
            print(f"  Tier {t}: {len(tiers[t])} augments")

    all_crawled = {a for aug_list in tiers.values() for a in aug_list}

    # 1. Doi chieu voi augment_features.json neu co
    features_file = Path(args.features)
    if features_file.exists():
        try:
            with open(features_file, "r", encoding="utf-8") as f:
                features_data = json.load(f)
            known_augs = set((features_data.get("augments") or {}).keys())
            if known_augs:
                matched = all_crawled.intersection(known_augs)
                unmatched = all_crawled - known_augs
                pct = len(matched) / len(all_crawled) * 100 if all_crawled else 0
                print(
                    f"\nDoi chieu database cuc bo ({features_file.name}): "
                    f"{len(matched)}/{len(all_crawled)} ({pct:.1f}%) hop le."
                )
                if unmatched:
                    print(f"  Chu y: {len(unmatched)} ma chua co trong features: {sorted(unmatched)}")
        except Exception as e:
            print(f"Khong the doc features de doi chieu: {e}", file=sys.stderr)

    # 2. Doi chieu voi TFT Academy de kiem tra do phu bu tru
    tftacad_file = Path(args.tftacademy_tiers)
    if tftacad_file.exists():
        try:
            with open(tftacad_file, "r", encoding="utf-8") as f:
                tftacad_data = json.load(f)
            tftacad_augs = {
                a
                for aug_list in (tftacad_data.get("tiers") or {}).values()
                for a in aug_list
            }
            overlap = all_crawled.intersection(tftacad_augs)
            only_in_metatft = all_crawled - tftacad_augs
            print(
                f"\nSo sanh voi TFT Academy ({tftacad_file.name}):\n"
                f"  Trung lap giua hai nguon: {len(overlap)} augments\n"
                f"  MetaTFT bo sung them: {len(only_in_metatft)} augments chua co trong TFT Academy"
            )

            # Kiem tra 7 loi tung thieu o TFT Academy
            metatft_lookup = {
                a: t for t, aug_list in tiers.items() for a in aug_list
            }
            print("\n  Kiem tra 7 loi tung khong duoc TFT Academy xep hang:")
            resolved_count = 0
            for target in MISSING_TARGETS:
                tier_found = metatft_lookup.get(target)
                if tier_found:
                    resolved_count += 1
                    print(f"    [+] {target}: Tier {tier_found} (da co nguon phu)")
                else:
                    print(f"    [-] {target}: van chua co nguon xep")
            print(f"  Ket qua: MetaTFT da phu duoc {resolved_count}/{len(MISSING_TARGETS)} loi con thieu!")
        except Exception as e:
            print(f"Khong the doi chieu TFT Academy: {e}", file=sys.stderr)

    meta = {
        "rated_by": args.rated_by,
        "patch": patch,
        "stage": args.stage,
        "source_url": TIERLIST_PAGE_URL,
    }

    if args.dry_run:
        print("\n[DRY RUN] Khong ghi file vao he thong.")
        return 0

    # 1. Ghi file JSON cho ExpertTierListProvider
    json_payload = build_tierlist_payload(tiers, meta)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(out_path, "w", encoding="utf-8") as f:
        json.dump(json_payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"\nDa ghi JSON thanh cong -> {out_path}")

    # 2. Ghi file text tho (raw) neu can
    if raw_out_path:
        raw_text = format_raw_text(tiers, meta)
        raw_out_path.parent.mkdir(parents=True, exist_ok=True)
        raw_out_path.write_text(raw_text, encoding="utf-8")
        print(f"Da ghi RAW text thanh cong -> {raw_out_path}")

    print(f"Provenance: {args.rated_by} | Patch: {patch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
