"""Item Advisor - ghep gi tu nhung manh dang co (SPEC 3.5, uu tien 4).

BANG CONG THUC LA DU LIEU SINH RA, KHONG PHAI HANG SO TRONG CODE.

Day la quy tac da ghi o SPEC 5: asset va bang tra cuu curate tay chinh la thu
da giet moi overlay TFT nguon mo truoc day - moi set doi ten item mot lan la
mot lan phai sua tay. Vi the:

    build_recipes_from_locale()  <- sinh tu field `composition` cua CDragon
    ItemRecipes.load()           <- doc file da sinh
    khong co file                -> advisor van chay, chi khong goi ten item

Fixture trong repo da bi trim con rieng augment nen `composition` rong; bang
that duoc sinh khi chay voi locale day du.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

from ..game_state.models import GameState


@dataclass(frozen=True)
class Recipe:
    """Mot cong thuc ghep: hai component -> mot item."""

    item: str
    components: tuple[str, str]

    def needs(self, held: Counter) -> list[str]:
        """Component con thieu de ghep duoc, co tinh trung lap (2 manh giong nhau)."""
        need = Counter(self.components)
        return list((need - held).elements())


@dataclass
class ItemRecipes:
    """Tap cong thuc ghep, kem nguon goc."""

    recipes: list[Recipe] = field(default_factory=list)
    source: str = "empty"

    def __len__(self) -> int:
        return len(self.recipes)

    @property
    def is_empty(self) -> bool:
        return not self.recipes

    @classmethod
    def load(cls, path: str | Path) -> "ItemRecipes":
        """Nap tu file da sinh. Khong co file -> rong, KHONG raise."""
        p = Path(path)
        if not p.exists():
            return cls([], f"khong tim thay {p}")
        payload = json.loads(p.read_text(encoding="utf-8"))
        recipes = [
            Recipe(r["item"], tuple(r["components"])) for r in payload.get("recipes", [])
        ]
        return cls(recipes, payload.get("source", str(p)))

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "source": self.source,
            "recipes": [{"item": r.item, "components": list(r.components)} for r in self.recipes],
        }
        p.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def buildable(self, components: Iterable[str]) -> list[tuple[Recipe, tuple[str, str]]]:
        """Cac item ghep duoc NGAY tu manh dang co."""
        held = Counter(components)
        out: list[tuple[Recipe, tuple[str, str]]] = []
        for recipe in self.recipes:
            if not (Counter(recipe.components) - held):
                out.append((recipe, recipe.components))
        return out

    def one_away(self, components: Iterable[str]) -> list[tuple[Recipe, str]]:
        """Cac item chi con thieu DUNG MOT component."""
        held = Counter(components)
        out: list[tuple[Recipe, str]] = []
        for recipe in self.recipes:
            missing = recipe.needs(held)
            if len(missing) == 1:
                out.append((recipe, missing[0]))
        return out


def build_recipes_from_locale(locale: dict[str, Any]) -> ItemRecipes:
    """Sinh bang cong thuc tu `composition` cua locale CDragon.

    Chi lay item co dung 2 component - do la dinh nghia cua item ghep chuan.
    Item dac biet (radiant, artifact, emblem) co composition khac va duoc bo
    qua co y: chung khong ghep duoc tu tui component thong thuong.
    """
    recipes: list[Recipe] = []
    for item in locale.get("items", []):
        comp = item.get("composition") or []
        if len(comp) != 2 or item.get("isAugment"):
            continue
        recipes.append(Recipe(str(item.get("apiName") or item.get("name")), (comp[0], comp[1])))
    return ItemRecipes(recipes, "cdragon:composition")


@dataclass
class ItemAdvice:
    """Loi khuyen trang bi cho mot thoi diem."""

    buildable: list[str] = field(default_factory=list)
    one_away: list[tuple[str, str]] = field(default_factory=list)
    surplus: list[str] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "buildable": self.buildable,
            "one_away": [{"item": i, "needs": c} for i, c in self.one_away],
            "surplus": self.surplus,
            "note": self.note,
        }


class ItemAdvisor:
    """Doc tui component va noi ghep duoc gi, con thieu gi."""

    def __init__(self, recipes: ItemRecipes | None = None) -> None:
        self.recipes = recipes or ItemRecipes()

    def recommend(self, state: GameState) -> ItemAdvice:
        held = Counter(state.item_components)

        if self.recipes.is_empty:
            # Khong co bang cong thuc thi van con mot dieu chac chan noi duoc:
            # component nao dang le va component nao dang du.
            odd = sorted(c for c, n in held.items() if n % 2 == 1)
            return ItemAdvice(
                surplus=odd,
                note=(
                    "Chưa có bảng công thức (sinh bằng build_recipes_from_locale) — "
                    "chỉ báo được mảnh lẻ"
                ),
            )

        buildable = [r.item for r, _ in self.recipes.buildable(state.item_components)]
        one_away = [(r.item, need) for r, need in self.recipes.one_away(state.item_components)]
        surplus = sorted(c for c, n in held.items() if n >= 3)

        note = f"Nguồn công thức: {self.recipes.source}"
        return ItemAdvice(buildable, one_away[:6], surplus, note)
