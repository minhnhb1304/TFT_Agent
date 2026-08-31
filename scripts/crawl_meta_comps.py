"""Crawl tft-match-v1 -> data/meta_comps.json - thay bo mock bang so THAT.

    python scripts/crawl_meta_comps.py --dry-run
    python scripts/crawl_meta_comps.py --matches 300 --overwrite

VI SAO LA COMP CHU KHONG PHAI AUGMENT
    Do 2026-09-01 tren vn2: participant cua tft-match-v1 o Set 18 KHONG con
    truong `augments`, va toan bo payload match khong chua chuoi "augment"
    nao. Riot hien khong cap duoc so lieu augment.

    Nhung `units`, `traits`, `placement` va `level` thi VAN CO. Doi hinh meta
    vi the do duoc that - va do la thu thay the duoc phan gia lap.

    Ket qua: data/meta_comps.json thanh du lieu THAT, con
    data/augment_stats.csv van phai la MOCK-NOT-REAL cho den khi tim duoc
    nguon khac. Xem research/open-questions.md.

DOI HINH DUOC NHOM THE NAO - va gioi han cua cach do
    Moi participant duoc gan vao doi hinh theo TRAIT BAT O BAC CAO NHAT.

    Day la mot XAP XI va phai neu trong bao cao: nguoi choi dinh nghia doi
    hinh boi carry + item, khong chi boi trait. Hai van cung "Riftbeast" co
    the la hai doi hinh khac han. Nhung trait la tin hieu on dinh duy nhat co
    san trong du lieu match, va no du de nhom cac van giong nhau lai.

    `best_augments` de RONG - khong doan. CompSelector coi day la khong co
    tin hieu, dung hon la mot danh sach bia.
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
from src.knowledge.riot_api import (  # noqa: E402
    APEX_TIERS,
    RANKED_TFT_QUEUE_ID,
    TARGET_SET_NUMBER,
    CompAggregator,
    RiotApiError,
    RiotClient,
)
from src.utils.env import load_env, require  # noqa: E402
from src.utils.settings import Settings  # noqa: E402

DEFAULT_OUT = ROOT / "data" / "meta_comps.json"


def crawl(
    client: RiotClient,
    n_matches: int,
    tiers: tuple[str, ...],
    per_player: int,
    on_progress=None,
) -> CompAggregator:
    puuids = client.apex_puuids(tiers)
    if not puuids:
        raise RiotApiError(
            f"khong nguoi choi nao o hang {tiers} tren {client.platform}. "
            "Dau mua thi bang apex con rong - doi vai ngay hoac them tier thap hon."
        )
    print(f"  {len(puuids)} nguoi choi hang cao")

    seen: set[str] = set()
    ordered: list[str] = []
    for puuid in puuids:
        for match_id in client.match_ids(puuid, count=per_player):
            if match_id not in seen:
                seen.add(match_id)
                ordered.append(match_id)
        if len(ordered) >= n_matches:
            break
    print(f"  {len(ordered)} match id duy nhat")

    agg = CompAggregator()
    target = min(n_matches, len(ordered))
    for i, match_id in enumerate(ordered[:n_matches], start=1):
        agg.add_match(
            client.match(match_id),
            set_number=TARGET_SET_NUMBER,
            queue_id=RANKED_TFT_QUEUE_ID,
        )
        if on_progress:
            on_progress(i, target, agg)
    return agg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", default=None)
    parser.add_argument("--regional", default=None)
    parser.add_argument("--matches", type=int, default=300)
    parser.add_argument("--per-player", type=int, default=20)
    parser.add_argument("--tiers", nargs="*", default=list(APEX_TIERS), choices=list(APEX_TIERS))
    parser.add_argument(
        "--min-sample-n",
        type=int,
        default=20,
        help="bo doi hinh duoi nguong nay. 20 la muc toi thieu de con dang ke.",
    )
    parser.add_argument("--limit", type=int, default=12, help="so doi hinh giu lai")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    settings = Settings.load()
    platform = args.platform or str(settings.get("riot", "platform", "vn2"))
    tiers = tuple(args.tiers)

    if args.dry_run:
        est = len(tiers) + (args.matches // max(1, args.per_player)) + args.matches
        print(f"platform          : {platform}")
        print(f"hang              : {'+'.join(tiers)}")
        print(f"so match           : {args.matches}")
        print(f"request uoc tinh   : ~{est}")
        print(f"thoi gian uoc tinh : ~{est / 0.83 / 60:.1f} phut")
        print("\n--dry-run: khong goi mang, khong ghi file.")
        return 0

    out = Path(args.out)
    if out.exists() and not args.overwrite:
        print(f"{out} da ton tai. Them --overwrite de de len.", file=sys.stderr)
        return 1

    load_env()
    api_key = require(
        "RIOT_API_KEY",
        "Personal Key het han sau 24 gio - lay lai tai https://developer.riotgames.com/",
    )

    client = RiotClient(api_key=api_key, platform=platform, regional=args.regional)
    print(f"platform {client.platform} -> regional {client.regional}, hang {'+'.join(tiers)}")

    def progress(i: int, total: int, agg: CompAggregator) -> None:
        if i % 25 == 0 or i == total:
            print(
                f"  {i}/{total} match  |  dung duoc {agg.matches_used}  "
                f"|  {agg.participants} participant  |  {len(agg.comps)} doi hinh",
                flush=True,
            )

    try:
        agg = crawl(client, args.matches, tiers, args.per_player, on_progress=progress)
    except RiotApiError as exc:
        print(f"\nFAIL: {exc}", file=sys.stderr)
        return 1

    label = f"riot:tft-match-v1/{client.platform}/{'+'.join(t[:2] for t in tiers)}/n={agg.matches_used}"
    records = agg.comp_records(label, min_sample_n=args.min_sample_n, limit=args.limit)

    if not records:
        print(
            f"\nKhong doi hinh nao dat co mau >= {args.min_sample_n} "
            f"tren {agg.participants} participant. Tang --matches hoac ha "
            "--min-sample-n. KHONG ghi de file.",
            file=sys.stderr,
        )
        return 1

    # Fail sang neu schema lech: MetaComp(**r) se nem TypeError ngay o day
    # thay vi luc CompDatabase.load() chay trong runtime.
    for r in records:
        MetaComp(**r)

    payload = {
        "meta": {
            "set": "TFTSet18",
            "source": label,
            "platform": client.platform,
            "tiers": list(tiers),
            "queue_id": RANKED_TFT_QUEUE_ID,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "grouping": "trait bat o bac cao nhat - xem docstring cua script",
            "note": (
                "best_augments de rong: tft-match-v1 khong tra du lieu augment "
                "cho Set 18 (do 2026-09-01)."
            ),
            "summary": agg.summary(),
            "n": len(records),
        },
        "comps": records,
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print(f"\nda ghi {len(records)} doi hinh -> {out}")
    for k, v in agg.summary().items():
        print(f"  {k:18s} {v}")
    print()
    for c in records:
        print(
            f"  [{c['tier']}] {c['name']:28s} avg={c['avg_placement']:.2f} "
            f"top4={c['top4_rate']:.0%} n={c['sample_n']}"
        )

    assert len(CompDatabase.load(out)) == len(records)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
