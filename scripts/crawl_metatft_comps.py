"""Crawl cum doi hinh meta tu MetaTFT -> data/meta_comps.metatft.json.

    python scripts/crawl_metatft_comps.py
    python scripts/crawl_metatft_comps.py --overwrite
    python scripts/crawl_metatft_comps.py --dry-run

VI SAO CRAWL DUOC
    MetaTFT cung cap REST API noi bo:
        GET https://api-hc.metatft.com/tft-comps-api/latest_cluster_info
        GET https://api-hc.metatft.com/tft-comps-api/comp_builds
    chua 53 cum doi hinh K-means clustering voi sample_n that va avg_placement do duoc.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.knowledge.metatft_comps import (  # noqa: E402
    MetaTFTCompsClient,
    MetaTFTCompsError,
    build_meta_comps_payload,
    parse_metatft_comps,
)

DEFAULT_OUT = ROOT / "data" / "meta_comps.metatft.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crawl cum doi hinh meta tu MetaTFT lam nguon bo tro / du phong"
    )
    parser.add_argument(
        "--patch",
        default="18.1d",
        help="Patch cua du lieu (mac dinh: 18.1d)",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help=f"Duong dan file JSON dau ra (mac dinh: {DEFAULT_OUT})",
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

    if not args.dry_run:
        if out_path.exists() and not args.overwrite:
            print(f"File {out_path} da ton tai. Them --overwrite de ghi de.", file=sys.stderr)
            return 1

    print("Dang ket noi den MetaTFT Comps API (latest_cluster_info & comp_builds)...")
    client = MetaTFTCompsClient()

    try:
        cluster_info = client.get_cluster_info()
        comp_builds = client.get_comp_builds()
    except MetaTFTCompsError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    try:
        comps = parse_metatft_comps(cluster_info, comp_builds, patch=args.patch)
    except MetaTFTCompsError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    print(f"Da thu thap {len(comps)} cum doi hinh tu MetaTFT:")
    total_games = sum(c.sample_n for c in comps)
    print(f"  Tong co mau quan sat: {total_games:,} van dau")
    tier_counts: dict[str, int] = {}
    for c in comps:
        tier_counts[c.tier] = tier_counts.get(c.tier, 0) + 1

    for t in sorted(tier_counts):
        print(f"  Tier {t}: {tier_counts[t]} comps")

    if comps:
        print("\nVi du 3 cum dau:")
        for c in comps[:3]:
            print(f"  - [{c.tier}] {c.name}: {len(c.core_units)} tuong, avg {c.avg_placement:.2f} (n={c.sample_n:,})")

    if args.dry_run:
        print("\n[DRY RUN] Khong ghi file.")
        return 0

    meta = {
        "source": f"metatft:META Spencer/patch={args.patch}",
        "patch": args.patch,
        "total_games": total_games,
    }
    payload = build_meta_comps_payload(comps, meta)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"\nDa ghi JSON -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
