"""Crawl doi hinh meta tu TFT Academy -> data/meta_comps.tftacademy.json.

    python scripts/crawl_tftacademy_comps.py
    python scripts/crawl_tftacademy_comps.py --overwrite --primary
    python scripts/crawl_tftacademy_comps.py --dry-run

VI SAO CRAWL DUOC
    TFT Academy cung cap REST API noi bo cong khai:
        https://tftacademy.com/api/tierlist/comps?set=18
    chua 53 doi hinh meta Set 18 hoan chinh do Dishsoap & Frodan bien soan.
    Moi comp co day du core_units, core_items, va dac biet la best_augments (Riot apiName).
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.knowledge.tftacademy_comps import (  # noqa: E402
    TFTAcademyCompsClient,
    TFTAcademyCompsError,
    build_meta_comps_payload,
    parse_tftacademy_comps,
)

DEFAULT_OUT = ROOT / "data" / "meta_comps.tftacademy.json"
DEFAULT_PRIMARY_OUT = ROOT / "data" / "meta_comps.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crawl doi hinh meta tu TFT Academy cho Set 18"
    )
    parser.add_argument("--set", type=int, default=18, help="So thu tu Set (mac dinh 18)")
    parser.add_argument(
        "--patch",
        default="18.1d",
        help="Patch cua bang doi hinh meta (mac dinh: 18.1d)",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help=f"Duong dan file JSON dau ra (mac dinh: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--primary",
        action="store_true",
        help=f"Ghi de thang vao data/meta_comps.json de lam nguon chinh thuc",
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
    primary_out = DEFAULT_PRIMARY_OUT if args.primary else None

    if not args.dry_run:
        if out_path.exists() and not args.overwrite:
            print(f"File {out_path} da ton tai. Them --overwrite de ghi de.", file=sys.stderr)
            return 1

    print(f"Dang ket noi den TFT Academy Comps (Set {args.set})...")
    client = TFTAcademyCompsClient()

    try:
        raw_payload = client.get_comps(args.set)
    except TFTAcademyCompsError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    try:
        comps = parse_tftacademy_comps(raw_payload, patch=args.patch)
    except TFTAcademyCompsError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    print(f"Da thu thap {len(comps)} doi hinh meta tu TFT Academy:")
    tier_counts: dict[str, int] = {}
    aug_counts = 0
    for c in comps:
        tier_counts[c.tier] = tier_counts.get(c.tier, 0) + 1
        aug_counts += len(c.best_augments)

    for t in sorted(tier_counts):
        print(f"  Tier {t}: {tier_counts[t]} comps")
    print(f"  Tong so anh xa best_augments: {aug_counts}")

    if comps:
        print("\nVi du 3 doi hinh dau:")
        for c in comps[:3]:
            print(f"  - [{c.tier}] {c.name}: {len(c.core_units)} tuong core, {len(c.core_items)} do, {len(c.best_augments)} augments")

    if args.dry_run:
        print("\n[DRY RUN] Khong ghi file.")
        return 0

    meta = {
        "source": f"tftacademy:Dishsoap & Frodan/patch={args.patch}",
        "patch": args.patch,
    }
    payload = build_meta_comps_payload(comps, meta)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"\nDa ghi JSON -> {out_path}")

    if primary_out:
        with io.open(primary_out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"Da cap nhat file meta comps chinh -> {primary_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
