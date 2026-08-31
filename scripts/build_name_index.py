"""Sinh data/name_index.json - bang anh xa ten hien thi -> apiName (feedback #6/#7).

VI SAO PHAI SINH TU LOCALE DAY DU
    Bang nay khong the viet tay: 254 augment x 2 ngon ngu, 36 trait, 65
    champion, va moi set lai doi het. Per-set churn la thu da giet moi TFT
    overlay open-source (research/prior-art.md) - bang nao curate tay thi
    chet theo cach y het.

    Fixture trimmed trong tests/ KHONG dung duoc: no co 0 champion. Phai chay
    scripts/fetch_locale.py truoc de co ban day du trong data/cdragon_cache/.

DAU RA DUOC COMMIT VAO REPO
    Cung ly do voi data/augment_features.json: hoi dong mo file ra doc duoc,
    doi chieu duoc, va he thong chay duoc ma khong can mang.

    python scripts/fetch_locale.py        # mot lan, keo locale day du ve cache
    python scripts/build_name_index.py    # sinh bang
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.knowledge.augment_catalog import normalize, strip_tier_token  # noqa: E402
from src.knowledge.cdragon_client import CDragonClient, select_set_data  # noqa: E402
from src.knowledge.name_index import LANGUAGES, NAMESPACES  # noqa: E402
from src.utils.settings import Settings  # noqa: E402

DEFAULT_OUT = ROOT / "data" / "name_index.json"

# locale code cua CommunityDragon <-> nhan ngan dung trong index.
LOCALE_OF = {"vi": "vi_vn", "en": "en_us"}


def augment_pairs(locale: dict[str, Any]) -> list[tuple[str, str]]:
    """(apiName, ten hien thi) cho moi augment Set 18."""
    return [
        (str(i["apiName"]), str(i.get("name", "")))
        for i in locale.get("items", [])
        if str(i.get("apiName", "")).startswith("DA_") and i.get("isAugment")
    ]


def trait_pairs(locale: dict[str, Any]) -> list[tuple[str, str]]:
    """(apiName, ten hien thi) cho 36 trait - qua DUNG khoi setData cua Set 18."""
    return [
        (str(t["apiName"]), str(t.get("name", "")))
        for t in select_set_data(locale).get("traits", [])
    ]


def champion_pairs(locale: dict[str, Any], roster_ids: set[str]) -> list[tuple[str, str]]:
    """(apiName, ten hien thi) cho 65 tuong dang choi duoc.

    setData cua Set 18 liet ke 91 champion, gom ca don vi PvE va trieu hoi
    khong mua duoc trong shop. Loc theo roster tu tftchampions-teamplanner
    (nguon authoritative, 65/65 - xem research/set-data.md).
    """
    return [
        (str(c["apiName"]), str(c.get("name", "")))
        for c in select_set_data(locale).get("champions", [])
        if str(c.get("apiName", "")) in roster_ids
    ]


def index_pairs(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    """Dung ba index tu danh sach (apiName, ten).

    Gia tri LUON la list: mot ten co the ung voi nhieu apiName va do la gioi
    han du lieu that, khong phai loi can sua. Xem name_index.NameIndex.
    """
    by_norm: dict[str, list[str]] = defaultdict(list)
    by_stem: dict[str, list[str]] = defaultdict(list)
    exact: dict[str, list[str]] = defaultdict(list)

    for api, name in sorted(pairs):
        if not name:
            continue
        by_norm[normalize(name)].append(api)
        by_stem[normalize(strip_tier_token(name))].append(api)
        exact[name].append(api)

    return {
        "by_norm": {k: sorted(set(v)) for k, v in sorted(by_norm.items())},
        "by_stem": {k: sorted(set(v)) for k, v in sorted(by_stem.items())},
        "exact": {k: sorted(set(v)) for k, v in sorted(exact.items())},
    }


def build(cache_dir: Path) -> dict[str, Any]:
    client = CDragonClient(cache_dir=cache_dir, offline=True)
    roster_ids = {c.character_id for c in client.load_roster()}
    locales = {lang: client.load_locale(code) for lang, code in LOCALE_OF.items()}

    by_norm: dict[str, dict[str, Any]] = {ns: {} for ns in NAMESPACES}
    by_stem: dict[str, dict[str, Any]] = {ns: {} for ns in NAMESPACES}
    exact: dict[str, dict[str, Any]] = {ns: {} for ns in NAMESPACES}
    display: dict[str, dict[str, dict[str, str]]] = {ns: {} for ns in NAMESPACES}
    counts: dict[str, dict[str, int]] = {}

    for lang in LANGUAGES:
        locale = locales[lang]
        extracted = {
            "augments": augment_pairs(locale),
            "traits": trait_pairs(locale),
            "champions": champion_pairs(locale, roster_ids),
        }
        for ns, pairs in extracted.items():
            built = index_pairs(pairs)
            by_norm[ns][lang] = built["by_norm"]
            by_stem[ns][lang] = built["by_stem"]
            exact[ns][lang] = built["exact"]
            for api, name in pairs:
                display[ns].setdefault(api, {})[lang] = name
            counts.setdefault(ns, {})[lang] = len(pairs)

    ambiguous = {
        ns: {
            lang: sorted(k for k, v in by_norm[ns][lang].items() if len(v) > 1)
            for lang in LANGUAGES
        }
        for ns in NAMESPACES
    }

    return {
        "meta": {
            "set": "TFTSet18",
            "source": {lang: f"cdragon:{code}" for lang, code in LOCALE_OF.items()},
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "counts": counts,
            # So nhom trung ten - gioi han du lieu, phai bao cao chu khong giau.
            "ambiguous_group_counts": {
                ns: {lang: len(ambiguous[ns][lang]) for lang in LANGUAGES}
                for ns in NAMESPACES
            },
        },
        "by_norm": by_norm,
        "by_stem": by_stem,
        "exact": exact,
        "display": display,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)

    settings = Settings.load()
    cache_dir = Path(args.cache_dir) if args.cache_dir else settings.path("cdragon_cache")

    payload = build(cache_dir)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")

    meta = payload["meta"]
    print(f"da ghi -> {out}")
    for ns in NAMESPACES:
        c = meta["counts"][ns]
        a = meta["ambiguous_group_counts"][ns]
        print(
            f"  {ns:10s} vi={c['vi']:3d} en={c['en']:3d}   "
            f"nhom trung ten: vi={a['vi']} en={a['en']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
