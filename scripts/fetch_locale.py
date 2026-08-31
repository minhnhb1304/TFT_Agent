"""Keo du lieu CommunityDragon FULL ve cache - SPEC 3.4, feedback Tier 1 #3.

Vi sao script nay ton tai:
    data/augment_features.json hien duoc sinh tu tests/fixtures/cdragon/
    en_us.trimmed.json - mot ban da bi cat got de lam fixture. Ban trimmed
    KHONG co champion nao va KHONG co item thuong nao, nen khong the sinh
    duoc bang anh xa ten -> apiName (feedback #6/#7) hay item recipes tu no.

    Feedback Tier 1 #3: "Network is fine" - cho phep goi thang /latest/.

Script nay CHI la CLI mong boc quanh CDragonClient. Moi logic tai, cache va
kiem chung nam o src/knowledge/cdragon_client.py - khong viet lai o day.

    python scripts/fetch_locale.py                 # en_us + vi_vn + roster
    python scripts/fetch_locale.py --branch pbe    # khi standalone client len PBE
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.knowledge.cdragon_client import (  # noqa: E402
    CDragonClient,
    CDragonError,
    select_set_data,
)
from src.utils.settings import Settings  # noqa: E402

# Locale can co. en_us la nguon trich dac trung (vocabulary regex deu la tieng
# Anh); vi_vn la nguon doi chieu ket qua OCR. Ca hai deu can cho name index.
LOCALES = ("en_us", "vi_vn")


def _count_augments(locale: dict[str, Any]) -> int:
    return sum(
        1
        for item in locale.get("items", [])
        if item.get("isAugment") and str(item.get("apiName", "")).startswith("DA_")
    )


def _count_traits(locale: dict[str, Any]) -> int:
    return len(select_set_data(locale).get("traits", []))


def _report(cache_dir: Path, name: str) -> str:
    f = cache_dir / name
    meta = cache_dir / f"{name}.meta"
    size_mb = f.stat().st_size / 1_048_576 if f.exists() else 0.0
    last_mod = meta.read_text(encoding="utf-8").strip() if meta.exists() else "(khong co header)"
    return f"{name:34s} {size_mb:6.1f} MB   Last-Modified: {last_mod}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--branch",
        default=None,
        help="latest (mac dinh) hoac pbe. Khong truyen -> doc locale.branch trong settings.yaml.",
    )
    parser.add_argument("--cache-dir", default=None, help="Mac dinh: paths.cdragon_cache.")
    parser.add_argument(
        "--locales",
        nargs="*",
        default=list(LOCALES),
        help=f"Mac dinh: {' '.join(LOCALES)}. vn_vn bi tu choi o tang client.",
    )
    parser.add_argument(
        "--skip-roster",
        action="store_true",
        help="Bo qua tftchampions-teamplanner.json (roster 65 tuong).",
    )
    args = parser.parse_args(argv)

    settings = Settings.load()
    branch = args.branch or str(settings.get("locale", "branch", "latest"))
    cache_dir = Path(args.cache_dir) if args.cache_dir else settings.path("cdragon_cache")

    client = CDragonClient(branch=branch, cache_dir=cache_dir)
    print(f"Branch : {branch}")
    print(f"Cache  : {cache_dir}")
    print()

    try:
        # Doc set info truoc: neu Riot da doi set thi dung ngay, khong tai
        # 24 MB x 2 roi moi phat hien.
        default_set = client.load_set_info()
        print(f"mDefaultSet.SetName        = {default_set.get('SetName')}")
        print(f"mDefaultSet.SetDisplayName = {default_set.get('SetDisplayName')}")
        print(f"mDefaultSet.SetAugmentName = {default_set.get('SetAugmentName')}")
        print()

        if not args.skip_roster:
            roster = client.load_roster()
            print(f"Roster: {len(roster)} tuong (da qua assert phan bo tier + prefix DA)")

        for lang in args.locales:
            data = client.load_locale(lang)
            print(
                f"Locale {lang}: {_count_augments(data)} augment, "
                f"{_count_traits(data)} trait, {len(data.get('items', []))} item"
            )
    except CDragonError as exc:
        print(f"\nFAIL: {exc}", file=sys.stderr)
        return 1

    print("\nFile trong cache:")
    for name in sorted(p.name for p in cache_dir.glob("*.json")):
        print("  " + _report(cache_dir, name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
