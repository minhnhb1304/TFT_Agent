"""Sinh data/item_recipes.json + data/champion_costs.json tu locale CDragon.

Hai bang tra cuu ma CompSelector can de doc tin hieu chot bai (SPEC 3.5.2):

    item_recipes.json   - cong thuc ghep: do da ghep -> hai manh. Tu manh suy
                          ra loai AP/AD cua do, thay vi doan theo ten.
    champion_costs.json - gia tuong: tinh tien mua tuong khi xoay bai, va suy
                          kieu doi hinh (reroll / fast 8 / fast 9) cho nguon
                          khong gan nhan.

Cung nguyen tac voi build_name_index.py: sinh tu locale day du, khong curate
tay, commit vao repo de chay offline.

    python scripts/fetch_locale.py        # mot lan, keo locale day du ve cache
    python scripts/build_game_tables.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.decision.item_advisor import ItemRecipes, build_recipes_from_locale  # noqa: E402
from src.knowledge.cdragon_client import CDragonClient, select_set_data  # noqa: E402
from src.utils.settings import Settings  # noqa: E402

# Locale day du chua do cua nhieu set. Chi giu ho `DA_` cua Set 18, neu khong
# item advisor se goi y ghep do cua set cu.
SET_PREFIX = "DA_"


def set_recipes(locale: dict[str, Any]) -> ItemRecipes:
    recipes = [
        r for r in build_recipes_from_locale(locale).recipes
        if r.item.startswith(SET_PREFIX) and all(c.startswith(SET_PREFIX) for c in r.components)
    ]
    return ItemRecipes(recipes, "cdragon:en_us/composition")


def champion_costs(locale: dict[str, Any], roster_ids: set[str]) -> dict[str, Any]:
    costs = {
        str(c["apiName"]): int(c["cost"])
        for c in select_set_data(locale).get("champions", [])
        if str(c.get("apiName", "")) in roster_ids and c.get("cost") is not None
    }
    return {
        "meta": {
            "set": "TFTSet18",
            "source": "cdragon:en_us/setData.champions (loc theo roster teamplanner)",
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "count": len(costs),
        },
        "costs": dict(sorted(costs.items())),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", default=None)
    args = parser.parse_args(argv)

    settings = Settings.load()
    cache_dir = Path(args.cache_dir) if args.cache_dir else settings.path("cdragon_cache")
    client = CDragonClient(cache_dir=cache_dir, offline=True)
    locale = client.load_locale("en_us")
    roster_ids = {c.character_id for c in client.load_roster()}

    recipes = set_recipes(locale)
    recipes_path = settings.path("item_recipes")
    recipes.save(recipes_path)

    costs = champion_costs(locale, roster_ids)
    costs_path = settings.path("champion_costs")
    costs_path.parent.mkdir(parents=True, exist_ok=True)
    costs_path.write_text(json.dumps(costs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"da ghi {len(recipes)} cong thuc -> {recipes_path}")
    print(f"da ghi {costs['meta']['count']} gia tuong -> {costs_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
