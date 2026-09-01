"""Crawl tactics.tools -> doi hinh meta + stats unit/trait/item.

    python scripts/crawl_tactics_tools.py --dry-run
    python scripts/crawl_tactics_tools.py --rank all --overwrite

VI SAO KHONG GHI DE data/meta_comps.json
    File do la du lieu TU CRAWL tu tft-match-v1: 249 match, truy nguoc duoc
    den tung match_id, luu o meta_comps.meta.json. Do la thu bao ve duoc
    truoc hoi dong. Co mau nho, nhung provenance thi khong the tot hon.

    tactics.tools nguoc lai: hang trieu van, nhung khong cong bo phuong phap
    va khong truy nguoc duoc gi. De len file kia thi mat vinh vien mot thu
    khong mua lai duoc bang cach chay lai script.

    Vi vay mac dinh ghi ra data/meta_comps_tactics.json. Muon dung file nao
    o runtime thi doi `paths.meta_comps` trong config/settings.yaml - mot
    dong config, va lua chon do duoc ghi lai.

CO MAU
    --min-sample-n mac dinh 200, bang nguong MetaComp.is_evidence. Nguon nay
    du lon de loc chat: o rankGroup "all" (1,75 trieu van, do 2026-09-01) van
    con thua doi hinh vuot nguong.

GIOI HAN PHAI NEU TRONG BAO CAO
    Day la so cua ben thu ba, khong kiem chung duoc. Ho khong cong bo cach
    nhom doi hinh, khong cong bo cach loai van bo do, va khong cho match_id
    nao de doi chieu. Moi ban ghi mang `source` bat dau bang "tactics.tools:"
    de dieu do khong bao gio bi quen.

AUGMENT THI VAN KHONG CO
    Payload cua ho co san bon truong augment va ca bon deu RONG - script in
    ro dieu nay sau moi lan chay. Nghia la khong lay duoc so lieu augment
    KHONG phai gioi han cua du an nay: trang stats lon nhat cong khai cung
    khong co. Xem research/open-questions.md.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.knowledge.comp_database import CompDatabase, MetaComp  # noqa: E402
from src.knowledge.tactics_tools import (  # noqa: E402
    RANK_GROUPS,
    SET18_PATCH,
    TacticsToolsClient,
    TacticsToolsError,
    augment_row_count,
    comp_records,
    general_records,
    rank_group_code,
    source_label,
)

DEFAULT_COMPS_OUT = ROOT / "data" / "meta_comps_tactics.json"
DEFAULT_STATS_OUT = ROOT / "data" / "tactics_tools_stats.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rank",
        default="all",
        choices=sorted(RANK_GROUPS),
        help="rank group cua tactics.tools. 'all' co mau lon nhat, 'gm' nho nhat.",
    )
    parser.add_argument(
        "--patch",
        type=int,
        default=SET18_PATCH,
        help="ma patch cua tactics.tools. Sang 18.2 phai doi CO Y THUC.",
    )
    parser.add_argument(
        "--min-sample-n",
        type=int,
        default=200,
        help="bo doi hinh duoi nguong nay. 200 = nguong MetaComp.is_evidence.",
    )
    parser.add_argument("--limit", type=int, default=12, help="so doi hinh giu lai")
    parser.add_argument("--out", default=str(DEFAULT_COMPS_OUT))
    parser.add_argument("--stats-out", default=str(DEFAULT_STATS_OUT))
    parser.add_argument("--skip-stats", action="store_true", help="chi lay doi hinh")
    parser.add_argument("--dry-run", action="store_true", help="in URL se goi roi thoat")
    parser.add_argument("--overwrite", action="store_true", help="bat buoc neu file da co")
    args = parser.parse_args(argv)

    code = rank_group_code(args.rank)
    client = TacticsToolsClient(patch=args.patch)

    if args.dry_run:
        print(f"rank group  : {args.rank} (ma {code})")
        print(f"patch       : {args.patch}")
        print("se goi 2 request:")
        print(f"  https://api.tft.tools/team-compositions/{code}/{args.patch}")
        print(f"  https://d3.tft.tools/stats2/general/{client.queue_id}/{args.patch}/{code}")
        print("\n--dry-run: khong goi mang, khong ghi file.")
        return 0

    out = Path(args.out)
    stats_out = Path(args.stats_out)
    for path in (out,) + (() if args.skip_stats else (stats_out,)):
        if path.exists() and not args.overwrite:
            print(f"{path} da ton tai. Them --overwrite de de len.", file=sys.stderr)
            return 1

    try:
        comps_payload = client.team_compositions(code)
        stats_payload = None if args.skip_stats else client.general_stats(code)
    except TacticsToolsError as exc:
        print(f"\nFAIL: {exc}", file=sys.stderr)
        return 1

    total = int(comps_payload.get("count") or 0)
    label = source_label("team-compositions", args.rank, args.patch, total)
    records = comp_records(
        comps_payload,
        label,
        min_sample_n=args.min_sample_n,
        limit=args.limit,
    )
    if not records:
        print(
            f"\nKhong doi hinh nao dat co mau >= {args.min_sample_n} tren {total} van. "
            "KHONG ghi file - ha --min-sample-n neu that su muon so nho hon.",
            file=sys.stderr,
        )
        return 1

    db = CompDatabase([MetaComp(**r) for r in records])
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    n_augment_rows = augment_row_count(comps_payload)
    db.save(
        out,
        meta={
            "set": "TFTSet18",
            "source": label,
            "provider": "tactics.tools",
            "rank_group": args.rank,
            "patch": args.patch,
            "queue_id": client.queue_id,
            "generated_at": generated_at,
            "grouping": "nhom cua tactics.tools - phuong phap KHONG duoc cong bo",
            "note": (
                "So cua ben thu ba: khong truy nguoc duoc den match_id nao. "
                f"Truong augment trong payload: {n_augment_rows} ban ghi."
            ),
            "total_games": total,
            "n": len(records),
        },
    )
    print(f"da ghi {len(records)} doi hinh -> {out}")
    print(f"  tong {total} van, co mau lon nhat {max(r['sample_n'] for r in records)}")

    if stats_payload is not None:
        stats_label = source_label(
            "stats2/general", args.rank, args.patch, int(stats_payload.get("totalEntries") or 0)
        )
        rows = general_records(stats_payload, stats_label)
        rows["meta"] = {
            "source": stats_label,
            "provider": "tactics.tools",
            "rank_group": args.rank,
            "patch": args.patch,
            "generated_at": generated_at,
            "note": "CHUA noi vao scoring engine - du lieu tho, xem general_records().",
        }
        with io.open(stats_out, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        print(
            f"da ghi {len(rows['units'])} unit / {len(rows['traits'])} trait / "
            f"{len(rows['items'])} item -> {stats_out}"
        )

    print(
        f"\nban ghi augment trong payload: {n_augment_rows}.\n"
        + (
            "  -> Van bang 0: tactics.tools cung KHONG co so lieu augment cho Set 18.\n"
            "     data/augment_stats.csv phai giu nhan MOCK-NOT-REAL."
            if n_augment_rows == 0
            else "  -> KHAC 0! Nguon augment da mo lai - doc lai research/open-questions.md\n"
            "     va cap nhat data/augment_stats.csv."
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
