"""In do dong thuan giua data/augment_features.json va nhan tag MetaTFT (audit, khong phai ground truth).

    python scripts/compare_metatft_tags.py
    python scripts/compare_metatft_tags.py --list-fp

Tag lay tu data/augment_tags.metatft.json (tao boi scripts/crawl_metatft_tags.py).
Logic o src/eval/metatft_tags.py; xem docs/directional-augment/metatft-tag-audit.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.eval.metatft_tags import compare, format_report, load_snapshot  # noqa: E402

DEFAULT_TAGS = ROOT / "data" / "augment_tags.metatft.json"
DEFAULT_FEATURES = ROOT / "data" / "augment_features.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="So bang feature augment voi tag MetaTFT")
    parser.add_argument("--tags", default=str(DEFAULT_TAGS))
    parser.add_argument("--features", default=str(DEFAULT_FEATURES))
    parser.add_argument("--list-fp", action="store_true", help="In apiName FP/FN cua tung check")
    args = parser.parse_args(argv)

    tags = load_snapshot(args.tags)
    features = json.loads(Path(args.features).read_text(encoding="utf-8"))["augments"]
    print(format_report(compare(features, tags), list_fp=args.list_fp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
