"""Crawl nhan tag augment cua MetaTFT -> data/augment_tags.metatft.json (audit bang feature).

    python scripts/crawl_metatft_tags.py
    python scripts/crawl_metatft_tags.py --from-file tiers.json --crawled-at 2026-10-05
    python scripts/crawl_metatft_tags.py --dry-run

NGUON
    Cung endpoint voi crawl_metatft_tiers.py:
        https://api-hc.metatft.com/tft-stat-api/augments_tiers?tft_set=TFTSet18
    nhung doc truong content.content.tags (apiName -> "combat,items,...") thay vi tierList.
    --from-file cho phep dung lai payload da luu thay vi goi lai API (snapshot tai lap duoc).

PROVENANCE
    Nhan do META Spencer (MetaTFT) gan tay, khong tai lieu dinh nghia -> CHU QUAN.
    Chi dung lam tin hieu audit (src/eval/metatft_tags.py), KHONG phai ground truth.
    Chi giu tag cua apiName co trong data/augment_features.json.
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

from src.eval.metatft_tags import (  # noqa: E402
    MetaTFTTagError,
    build_snapshot,
    parse_tags,
)
from src.knowledge.metatft import (  # noqa: E402
    TIERLIST_API_URL,
    TIERLIST_PAGE_URL,
    MetaTFTClient,
    MetaTFTError,
)

DEFAULT_OUT = ROOT / "data" / "augment_tags.metatft.json"
DEFAULT_FEATURES = ROOT / "data" / "augment_features.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl nhan tag augment cua MetaTFT")
    parser.add_argument("--set", type=int, default=18, help="So thu tu Set (mac dinh 18)")
    parser.add_argument(
        "--from-file",
        default=None,
        help="Doc payload augments_tiers da luu thay vi goi API",
    )
    parser.add_argument(
        "--crawled-at",
        default=None,
        help="Thoi diem lay payload (ISO). Mac dinh: bay gio, hoac mtime cua --from-file",
    )
    parser.add_argument(
        "--features",
        default=str(DEFAULT_FEATURES),
        help="data/augment_features.json - catalog apiName can giu",
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="File JSON dau ra")
    parser.add_argument("--overwrite", action="store_true", help="Ghi de neu file da ton tai")
    parser.add_argument("--dry-run", action="store_true", help="Chi in thong ke, khong ghi file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_path = Path(args.out)
    if not args.dry_run and out_path.exists() and not args.overwrite:
        print(f"File {out_path} da ton tai. Them --overwrite de ghi de.", file=sys.stderr)
        return 1

    if args.from_file:
        src = Path(args.from_file)
        payload = json.loads(src.read_text(encoding="utf-8"))
        crawled_at = args.crawled_at or datetime.fromtimestamp(
            src.stat().st_mtime, timezone.utc
        ).isoformat(timespec="seconds")
        print(f"Doc payload da luu: {src}")
    else:
        print(f"Dang ket noi den MetaTFT (Set {args.set})...")
        try:
            payload = MetaTFTClient().get_augments_tierlist(args.set)
        except MetaTFTError as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 1
        crawled_at = args.crawled_at or datetime.now(timezone.utc).isoformat(timespec="seconds")

    try:
        tags = parse_tags(payload)
    except MetaTFTTagError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    features = json.loads(Path(args.features).read_text(encoding="utf-8"))
    catalog = list((features.get("augments") or {}).keys())

    content = payload.get("content") if isinstance(payload.get("content"), dict) else {}
    author = content.get("author") if isinstance(content.get("author"), dict) else {}
    meta = {
        "source": "MetaTFT augment tier list tags",
        "source_url": TIERLIST_PAGE_URL,
        "api_endpoint": f"{TIERLIST_API_URL}?tft_set=TFTSet{args.set}",
        "tft_set": payload.get("tft_set") or f"TFTSet{args.set}",
        "crawled_at": crawled_at,
        "metatft_updated_at": content.get("updated_at"),
        "metatft_content_id": content.get("content_id"),
        # chi giu ten hien thi, khong luu puuid
        "labeled_by": author.get("gameName"),
        "tag_vocabulary": ["combat", "items", "econ", "trait", "scaling", "misc"],
    }
    snapshot = build_snapshot(tags, catalog, meta)
    m = snapshot["meta"]
    print(
        f"MetaTFT co tag cho {len(tags)} augment; giu {m['n_tagged']}/{m['n_catalog']} "
        f"augment trong catalog. Thieu: {m['missing_from_metatft'] or '-'}"
    )

    if args.dry_run:
        print("[DRY RUN] Khong ghi file.")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(out_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Da ghi -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
