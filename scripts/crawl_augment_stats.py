"""Crawl tft-match-v1 -> data/augment_stats.csv - feedback Tier 1 #1 va #5.

Thay bo so gia lap MOCK-NOT-REAL bang so DO DUOC tu match that.

    python scripts/crawl_augment_stats.py --dry-run       # xem se goi bao nhieu request
    python scripts/crawl_augment_stats.py --matches 300   # crawl that
    python scripts/crawl_augment_stats.py --matches 300 --overwrite

NGAN SACH REQUEST - doc truoc khi chay
    Personal Key cho 100 request / 2 phut, tuc ~0.83 req/s trung binh. Mot
    dot crawl N match ton xap xi:

        3 (bang xep hang apex) + P (danh sach match cua P nguoi choi) + N

    N = 300 match voi P = 60 nguoi choi -> ~363 request -> ~7-8 phut.
    Moi match cho 8 quan sat, nen 300 match ~ 2400 quan sat participant.

CO MAU BAO NHIEU LA DU
    tuning.base.min_sample_n = 200 trong config/scoring_weights.yaml. Duoi
    nguong do BaseScorer keo diem ve trung tinh. Augment pho bien se dat
    nguong nhanh; augment hiem thi khong - va do la ket qua DUNG, khong phai
    loi: he thong noi "chua du bang chung" thay vi doan.

    --min-sample-n loc bo cac augment qua thua truoc khi ghi. Mac dinh 1
    (ghi het) de con nhin thay duoc phan phoi co mau that.

GIOI HAN PHAI NEU TRONG BAO CAO
    Day la ti le placement TRUNG BINH CO DIEU KIEN khi cam mot augment,
    KHONG phai hieu ung nhan qua cua no. Nguoi choi gioi chon augment tot
    hon VA choi tot hon - hai thu tuong quan. Day la du lieu quan sat.
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

from scripts.build_mock_stats import COLUMNS, write_csv  # noqa: E402
from src.knowledge.riot_api import (  # noqa: E402
    APEX_TIERS,
    RANKED_TFT_QUEUE_ID,
    TARGET_SET_NUMBER,
    AugmentAggregator,
    RiotApiError,
    RiotClient,
)
from src.utils.env import load_env, require  # noqa: E402
from src.utils.settings import Settings  # noqa: E402

DEFAULT_OUT = ROOT / "data" / "augment_stats.csv"


def source_label(platform: str, tiers: tuple[str, ...], n_matches: int) -> str:
    """Provenance ghi vao tung dong CSV.

    Phai doc duoc tren overlay va trong bao cao: nguon nao, hang nao, bao
    nhieu match. BaseScorer in nguyen van chuoi nay ra man hinh.
    """
    return f"riot:tft-match-v1/{platform}/{'+'.join(t[:2] for t in tiers)}/n={n_matches}"


def crawl(
    client: RiotClient,
    n_matches: int,
    tiers: tuple[str, ...],
    per_player: int,
    on_progress=None,
) -> AugmentAggregator:
    puuids = client.apex_puuids(tiers)
    if not puuids:
        raise RiotApiError(
            f"khong co nguoi choi nao o hang {tiers} tren {client.platform}. "
            "Dau mua xep hang thi bang apex co the con rong - thu tier thap hon."
        )

    seen: set[str] = set()
    ordered: list[str] = []
    for puuid in puuids:
        for match_id in client.match_ids(puuid, count=per_player):
            if match_id not in seen:
                seen.add(match_id)
                ordered.append(match_id)
        if len(ordered) >= n_matches:
            break

    agg = AugmentAggregator()
    for i, match_id in enumerate(ordered[:n_matches], start=1):
        agg.add_match(
            client.match(match_id),
            set_number=TARGET_SET_NUMBER,
            queue_id=RANKED_TFT_QUEUE_ID,
        )
        if on_progress:
            on_progress(i, min(n_matches, len(ordered)), agg)
    return agg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", default=None, help="mac dinh: riot.platform trong settings")
    parser.add_argument("--regional", default=None, help="suy ra tu platform neu bo trong")
    parser.add_argument("--matches", type=int, default=300, help="so match can lay")
    parser.add_argument("--per-player", type=int, default=20, help="so match id lay moi nguoi choi")
    parser.add_argument(
        "--tiers", nargs="*", default=list(APEX_TIERS), choices=list(APEX_TIERS)
    )
    parser.add_argument(
        "--min-sample-n",
        type=int,
        default=1,
        help="bo augment co co mau duoi nguong nay truoc khi ghi",
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument(
        "--dry-run", action="store_true", help="chi in ngan sach request roi thoat"
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="bat buoc neu file dau ra da ton tai"
    )
    args = parser.parse_args(argv)

    settings = Settings.load()
    platform = args.platform or str(settings.get("riot", "platform", "vn2"))
    tiers = tuple(args.tiers)

    if args.dry_run:
        est = len(tiers) + (args.matches // max(1, args.per_player)) + args.matches
        print(f"platform      : {platform}")
        print(f"hang          : {'+'.join(tiers)}")
        print(f"so match       : {args.matches}")
        print(f"request uoc tinh: ~{est}")
        print(f"thoi gian uoc tinh: ~{est / 0.83 / 60:.1f} phut (100 req / 2 phut)")
        print("\n--dry-run: khong goi mang, khong ghi file.")
        return 0

    out = Path(args.out)
    if out.exists() and not args.overwrite:
        print(
            f"{out} da ton tai. Them --overwrite de de len.\n"
            "(File hien tai co the la du lieu mock, hoac mot dot crawl truoc.)",
            file=sys.stderr,
        )
        return 1

    load_env()
    api_key = require(
        "RIOT_API_KEY",
        "Personal Key het han sau 24 gio - lay lai tai https://developer.riotgames.com/",
    )

    client = RiotClient(api_key=api_key, platform=platform, regional=args.regional)
    print(f"platform {client.platform} -> regional {client.regional}, hang {'+'.join(tiers)}")

    def progress(i: int, total: int, agg: AugmentAggregator) -> None:
        if i % 25 == 0 or i == total:
            print(f"  {i}/{total} match  |  dung duoc {agg.matches_used}  |  {len(agg.tallies)} augment")

    try:
        agg = crawl(client, args.matches, tiers, args.per_player, on_progress=progress)
    except RiotApiError as exc:
        print(f"\nFAIL: {exc}", file=sys.stderr)
        return 1

    if not agg.matches_used:
        print(
            f"\nKhong match nao thuoc Set {TARGET_SET_NUMBER} queue {RANKED_TFT_QUEUE_ID}. "
            "Khong ghi de file - kiem tra lai set number truoc khi tin ket qua.",
            file=sys.stderr,
        )
        return 1

    if not agg.tallies:
        print(
            f"\nDoc duoc {agg.matches_used} match Set {TARGET_SET_NUMBER} hop le "
            f"({agg.participants} participant) nhung KHONG augment nao.\n"
            "\n"
            "Do khong phai loi cua script. Do duoc 2026-09-01 tren vn2: participant\n"
            "cua tft-match-v1 o Set 18 KHONG con truong `augments`. Toan bo payload\n"
            "match khong chua chuoi 'augment' nao. Cac truong con lai: units, traits,\n"
            "level, placement, gold_left...\n"
            "\n"
            "Nghia la Riot API HIEN KHONG CAP duoc so lieu augment. Xem\n"
            "research/open-questions.md. Cac lua chon:\n"
            "  - giu data/augment_stats.csv gia lap (MOCK-NOT-REAL, tu khai bao)\n"
            "  - dung scripts/crawl_meta_comps.py: units/traits/placement VAN co,\n"
            "    nen doi hinh meta thi crawl duoc that\n"
            "\n"
            "KHONG ghi de file - mot CSV rong con te hon du lieu gia co nhan.",
            file=sys.stderr,
        )
        return 1

    label = source_label(client.platform, tiers, agg.matches_used)
    rows = list(agg.rows(label, min_sample_n=args.min_sample_n))
    write_csv(rows, out)

    summary = agg.summary()
    meta_path = out.with_suffix(".meta.json")
    with io.open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "source": label,
                "platform": client.platform,
                "regional": client.regional,
                "tiers": list(tiers),
                "set_number": TARGET_SET_NUMBER,
                "queue_id": RANKED_TFT_QUEUE_ID,
                "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "summary": summary,
                # Truy nguoc duoc den tung match la diem manh nhat cua nguon nay.
                "match_ids": agg.match_ids,
            },
            fh,
            indent=2,
        )

    print(f"\nda ghi {len(rows)} augment -> {out}")
    print(f"provenance -> {meta_path}")
    for k, v in summary.items():
        print(f"  {k:18s} {v}")
    below = sum(1 for r in rows if int(r["sample_n"]) < 200)
    print(
        f"\n{below}/{len(rows)} augment co co mau < 200 -> BaseScorer se keo ve trung tinh. "
        "Do la hanh vi DUNG: chua du bang chung thi khong duoc chi phoi xep hang."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
