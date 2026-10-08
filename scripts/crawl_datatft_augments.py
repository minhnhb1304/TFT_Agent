"""Crawl luot chao augment cua datatft.com -> data/augment_rounds.datatft.json.

    python scripts/crawl_datatft_augments.py --overwrite
    python scripts/crawl_datatft_augments.py --from-file h5-data-cn-18.json --overwrite
    python scripts/crawl_datatft_augments.py --dry-run

NGUON (docs/offer-rounds/source.md)
    Dung HAI request GET moi lan chay, khong hon:
      1. https://www.datatft.com/database -> khoi <script id="h5-data-preload">
         chua bang `var urls = {"18": "/assets/h5-data-cn-18-<hash>.json", ...}`.
         Hash doi moi lan ho cap nhat nen KHONG ghi cung, luon doc tu trang.
      2. file JSON do -> `hexs18` (3 danh sach lose) + `databaseUpdateTime`.
    --from-file dung lai file JSON da tai, khong goi mang (snapshot tai lap duoc).

VE SINH CRAWL ("cua so an danh")
    Moi request la mot `requests.get` rieng: khong Session, khong cookie gui di
    hay luu lai, khong dang nhap, khong ghi gi giua cac lan chay. Khong vong
    lap, khong thu lai: hong thi bao loi va thoat.

HONG THI BAO TO
    Khong tim thay dia chi file, thieu `hexs<set>`, luot la, hoac khop duoi
    MIN_MATCHED api_name cua catalog -> ma thoat 1 va KHONG dung den snapshot cu.

PROVENANCE
    Du lieu may chu Trung Quoc, mot nguoi duy tri, khong tai lieu -> TIN HIEU,
    khong phai ground truth. `list_index` (vi tri trong 3 danh sach) chi giu de
    dieu tra, KHONG phai bac cua lose: xem docs/offer-rounds/overview.md.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.knowledge.augment_features import OFFER_ROUNDS  # noqa: E402

PAGE_URL = "https://www.datatft.com/database"
DEFAULT_OUT = ROOT / "data" / "augment_rounds.datatft.json"
DEFAULT_FEATURES = ROOT / "data" / "augment_features.json"
# Catalog Set 18 co 254 lose; cho phep lech vai cai khi ho chua kip cap nhat.
MIN_MATCHED = 250
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
TIMEOUT_S = 30

RE_PRELOAD = re.compile(r'<script id="h5-data-preload">(.*?)</script>', re.S)
RE_URLS = re.compile(r"var urls\s*=\s*(\{.*?\})\s*;", re.S)


class DataTFTError(RuntimeError):
    """Nguon doi cau truc hoac du lieu khong du tin de ghi snapshot."""


def find_asset_url(html: str, tft_set: int = 18, page_url: str = PAGE_URL) -> str:
    """Dia chi tuyet doi cua file du lieu Set `tft_set`, doc tu khoi preload."""
    block = RE_PRELOAD.search(html)
    if not block:
        raise DataTFTError("khong thay <script id=\"h5-data-preload\"> trong trang")
    urls = RE_URLS.search(block.group(1))
    if not urls:
        raise DataTFTError("khong thay `var urls = {...};` trong khoi preload")
    try:
        table = json.loads(urls.group(1))
    except json.JSONDecodeError as exc:
        raise DataTFTError(f"bang urls khong phai JSON: {exc}") from exc
    path = table.get(str(tft_set)) if isinstance(table, dict) else None
    if not isinstance(path, str) or not path.endswith(".json"):
        raise DataTFTError(f"bang urls khong co Set {tft_set}: {table}")
    return urljoin(page_url, path)


def http_get(url: str) -> str:
    """MOT request khong trang thai: khong Session, khong cookie, khong thu lai."""
    import requests  # noqa: PLC0415 - --from-file va test khong can requests

    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_S)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise DataTFTError(f"GET {url} hong: {exc}") from exc
    resp.encoding = "utf-8"
    return resp.text


def parse_augments(payload: dict[str, Any], tft_set: int = 18) -> dict[str, dict[str, Any]]:
    """hexId -> {rounds, types, list_index} cho moi lose trong `hexs<set>`."""
    lists = payload.get(f"hexs{tft_set}")
    if not isinstance(lists, list) or not lists:
        raise DataTFTError(f"payload thieu `hexs{tft_set}`")
    rank = {r: i for i, r in enumerate(OFFER_ROUNDS)}
    out: dict[str, dict[str, Any]] = {}
    for index, group in enumerate(lists):
        for row in group:
            hex_id = row.get("hexId")
            if not hex_id:
                continue
            rounds = list(dict.fromkeys(row.get("round") or []))
            bad = [r for r in rounds if r not in rank]
            if bad:
                raise DataTFTError(f"{hex_id}: luot la {bad} (chi biet {OFFER_ROUNDS})")
            out[hex_id] = {
                "rounds": sorted(rounds, key=rank.__getitem__),
                "types": list(row.get("type") or []),
                "list_index": index,
            }
    return out


def build_snapshot(
    payload: dict[str, Any],
    catalog: list[str],
    meta: dict[str, Any],
    tft_set: int = 18,
    min_matched: int | None = None,
) -> dict[str, Any]:
    """Snapshot chi giu lose co trong `catalog`. Khop duoi nguong -> DataTFTError."""
    min_matched = MIN_MATCHED if min_matched is None else min_matched
    parsed = parse_augments(payload, tft_set)
    kept = {api: parsed[api] for api in sorted(catalog) if api in parsed}
    if len(kept) < min_matched:
        raise DataTFTError(
            f"chi khop {len(kept)}/{len(catalog)} api_name (can >= {min_matched}) - "
            "nguon doi khoa hoac doi set, khong ghi snapshot"
        )
    updated = payload.get("databaseUpdateTime")
    return {
        "meta": {
            **meta,
            "set": f"TFTSet{tft_set}",
            "database_updated_at": (
                datetime.fromtimestamp(updated / 1000, timezone.utc).isoformat(timespec="seconds")
                if isinstance(updated, (int, float)) else None
            ),
            "matched": len(kept),
            "n_catalog": len(catalog),
            "missing_from_datatft": sorted(set(catalog) - set(kept)),
        },
        "augments": kept,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl luot chao augment cua datatft.com")
    parser.add_argument("--set", type=int, default=18, help="So thu tu Set (mac dinh 18)")
    parser.add_argument(
        "--from-file", default=None, help="Doc file h5-data da tai thay vi goi mang"
    )
    parser.add_argument(
        "--asset-url", default=None, help="Dia chi goc cua --from-file, ghi vao meta"
    )
    parser.add_argument(
        "--crawled-at",
        default=None,
        help="Thoi diem lay payload (ISO). Mac dinh: bay gio, hoac mtime cua --from-file",
    )
    parser.add_argument(
        "--features",
        default=str(DEFAULT_FEATURES),
        help="data/augment_features.json - catalog api_name can giu",
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

    try:
        if args.from_file:
            src = Path(args.from_file)
            payload = json.loads(src.read_text(encoding="utf-8"))
            asset_url = args.asset_url
            crawled_at = args.crawled_at or datetime.fromtimestamp(
                src.stat().st_mtime, timezone.utc
            ).isoformat(timespec="seconds")
            print(f"Doc payload da luu: {src}")
        else:
            print(f"Dang doc {PAGE_URL} (Set {args.set})...")
            asset_url = find_asset_url(http_get(PAGE_URL), args.set)
            print(f"File du lieu: {asset_url}")
            payload = json.loads(http_get(asset_url))
            crawled_at = args.crawled_at or datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            )

        features = json.loads(Path(args.features).read_text(encoding="utf-8"))
        catalog = list((features.get("augments") or {}).keys())
        meta = {
            "source": "datatft.com",
            "source_url": PAGE_URL,
            "server": "CN",
            "asset_url": asset_url,
            "crawled_at": crawled_at,
        }
        # Dung xong TOAN BO snapshot trong bo nho roi moi mo file ghi: moi loi
        # o tren deu thoat truoc khi cham vao snapshot cu.
        snapshot = build_snapshot(payload, catalog, meta, args.set)
    except (DataTFTError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    m = snapshot["meta"]
    dist: dict[str, int] = {}
    for row in snapshot["augments"].values():
        key = "+".join(row["rounds"]) or "(rong)"
        dist[key] = dist.get(key, 0) + 1
    print(
        f"Khop {m['matched']}/{m['n_catalog']} augment trong catalog. "
        f"Thieu: {m['missing_from_datatft'] or '-'}. Nguon cap nhat: {m['database_updated_at']}"
    )
    print(f"Phan bo luot: {dict(sorted(dist.items()))}")

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
