"""Crawl bang tier augment tu TFT Academy -> data/augment_tiers.json.

    python scripts/crawl_tftacademy_tiers.py
    python scripts/crawl_tftacademy_tiers.py --stage All --overwrite
    python scripts/crawl_tftacademy_tiers.py --dry-run

VI SAO CRAWL DUOC
    TFT Academy cung cap endpoint REST API noi bo:
        https://tftacademy.com/api/tierlist/augments?set=18
    chua day du danh sach loi xep theo S/A/B/C/D cua Dishsoap & Frodan.
    Ma loi dung chuan Riot apiName (DA_...), khong can phai mapping tay.

PROVENANCE
    Xep hang boi Dishsoap & Frodan (TFT Academy).
    Thuoc tinh sample_n luon 0, is_ordinal luon True.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.knowledge.stats_provider import ExpertTierListProvider  # noqa: E402
from src.knowledge.tftacademy import (  # noqa: E402
    TIERLIST_PAGE_URL,
    TFTAcademyClient,
    TFTAcademyError,
    build_tierlist_payload,
    format_raw_text,
    parse_tierlist_augments,
)

DEFAULT_OUT = ROOT / "data" / "augment_tiers.json"
DEFAULT_RAW_OUT = ROOT / "data" / "augment_tiers_raw.txt"
DEFAULT_FEATURES = ROOT / "data" / "augment_features.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crawl bang tier augment tu TFT Academy cho Set 18"
    )
    parser.add_argument("--set", type=int, default=18, help="So thu tu Set (mac dinh 18)")
    parser.add_argument(
        "--stage",
        default="All",
        help="Giai doan can lay: 'All' (tong hop), '2-1', '3-2', '4-2' (mac dinh: All)",
    )
    parser.add_argument(
        "--rated-by",
        default="TFT Academy (Dishsoap & Frodan)",
        help="Nguoi danh gia, ghi vao provenance",
    )
    parser.add_argument(
        "--patch",
        default=None,
        help="Patch cua bang tier (mac dinh tu dong lay tu TFT Academy hoac fallback 18.1d)",
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
        help="Khong ghi file text tho data/augment_tiers_raw.txt",
    )
    parser.add_argument(
        "--features",
        default=str(DEFAULT_FEATURES),
        help="Duong dan data/augment_features.json de doi chieu apiName",
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

    print(f"Dang ket noi den TFT Academy (Set {args.set}, Stage '{args.stage}')...")
    client = TFTAcademyClient()

    try:
        raw_payload = client.get_augments_tierlist(args.set)
    except TFTAcademyError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    patch_info = client.get_patch_info()
    detected_patch = patch_info.get("patch") or "18.1d"
    patch = args.patch or detected_patch

    try:
        tiers = parse_tierlist_augments(raw_payload, stage=args.stage)
    except TFTAcademyError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    total_augs = sum(len(v) for v in tiers.values())
    print(f"Da thu thap {total_augs} augment tu TFT Academy:")
    for t in ExpertTierListProvider.TIER_PLACEMENT:
        if t in tiers:
            print(f"  Tier {t}: {len(tiers[t])} augments")

    # Doi chieu voi augment_features.json neu co
    features_file = Path(args.features)
    if features_file.exists():
        try:
            with open(features_file, "r", encoding="utf-8") as f:
                features_data = json.load(f)
            known_augs = set((features_data.get("augments") or {}).keys())
            if known_augs:
                all_crawled = {a for aug_list in tiers.values() for a in aug_list}
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

    print(f"Provenance: {args.rated_by} | Patch: {patch} | Stage: {args.stage}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
