"""Data model cho trang thai mot van dau - SPEC 3.3.

Nguyen tac thiet ke duy nhat dang nho o day: MOI reader deu co the that bai.
Vi the tat ca field deu co gia tri mac dinh hop le, va `opponents` mac dinh
RONG. Moi doan code doc `state.opponents` phai chay duoc khi scouting tat
(Phase 7, feature-flag) - do la ly do no la list rong chu khong phai None.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any

# Stage dang "4-2": (so man, so vong trong man).
RE_STAGE = re.compile(r"^\s*(\d+)\s*-\s*(\d+)\s*$")


class GameEvent(Enum):
    """Su kien do state_tracker phat ra khi so sanh hai frame lien tiep."""

    ROUND_START = "round_start"
    ROUND_END = "round_end"
    SHOP_REFRESH = "shop_refresh"
    CHAMPION_BOUGHT = "champion_bought"
    CHAMPION_SOLD = "champion_sold"
    ITEM_EQUIPPED = "item_equipped"
    LEVEL_UP = "level_up"
    AUGMENT_SELECTION = "augment_selection"
    COMBAT_RESULT = "combat_result"
    CAROUSEL_ROUND = "carousel_round"
    GAME_START = "game_start"
    GAME_END = "game_end"


@dataclass
class Champion:
    """Mot tuong tren board hoac bench."""

    name: str
    cost: int = 1
    star_level: int = 1
    items: list[str] = field(default_factory=list)
    position: tuple[int, int] | None = None  # (row, col) hex; None = tren bench
    traits: list[str] = field(default_factory=list)
    role: str | None = None  # Vai tro tu Riot/CDragon (ADCarry, APCaster,...), None neu chua cap nhat

    @property
    def on_bench(self) -> bool:
        return self.position is None

    @property
    def value(self) -> int:
        """Gia tri quy doi ra gold: cost * 3^(star-1). Dung de uoc luong carry."""
        return self.cost * (3 ** (self.star_level - 1))


@dataclass
class OpponentBoard:
    """Board doi thu doc qua scoreboard - Phase 7, mac dinh khong co.

    LUON kem confidence: doc board nguoi khac nhieu hon han doc board minh,
    va moi thu tinh tu day (contest_score) phai biet du lieu dau vao yeu den dau.
    """

    slot: int
    units: list[str] = field(default_factory=list)
    level: int | None = None
    hp: int | None = None
    confidence: float = 0.0


@dataclass
class GameState:
    """Anh chup trang thai tai mot thoi diem.

    Tat ca field co default de mot reader hong mot phan van tra ve state dung
    duoc - advisor se tu ha diem tin cay thay vi crash.
    """

    gold: int = 0
    level: int = 1
    hp: int = 100
    xp: int = 0
    stage: str = "1-1"
    streak: int = 0

    board: list[Champion] = field(default_factory=list)
    bench: list[Champion] = field(default_factory=list)
    shop: list[Champion | None] = field(default_factory=list)

    item_components: list[str] = field(default_factory=list)
    completed_items: list[str] = field(default_factory=list)
    active_traits: dict[str, int] = field(default_factory=dict)
    augments: list[str] = field(default_factory=list)

    timestamp: float = 0.0
    round_phase: str = "planning"
    session_state: str = "in_game"

    # Phase 7 - feature-flag `enable_scouting`, MAC DINH TAT.
    opponents: list[OpponentBoard] = field(default_factory=list)

    # -- tien ich doc stage ------------------------------------------------

    @property
    def stage_number(self) -> int:
        """So man (phan truoc dau gach). Tra 1 neu stage khong doc duoc."""
        m = RE_STAGE.match(self.stage)
        return int(m.group(1)) if m else 1

    @property
    def round_number(self) -> int:
        """So vong trong man. Tra 1 neu stage khong doc duoc."""
        m = RE_STAGE.match(self.stage)
        return int(m.group(2)) if m else 1

    @property
    def stage_progress(self) -> float:
        """Vi tri trong van dau, 0.0 (dau 1-1) -> 1.0 (tu 6-1 tro di).

        Dung lam he so cho EconFit/TempoFit: econ som co thoi gian sinh loi,
        econ muon thi khong. Chan tren o stage 6 vi qua do moi quyet dinh
        deu la "danh ngay", khong con khac biet.
        """
        return min(max((self.stage_number - 1) / 5.0, 0.0), 1.0)

    @property
    def carries(self) -> list[Champion]:
        """Cac tuong dang duoc dau tu nhat - suy ra tu gia tri va so item.

        Khong co field "carry" trong game; carry la thu SUY RA. Xep theo
        (so item, gia tri quy doi) roi lay nhung con dang mang item.
        """
        ranked = sorted(
            self.board,
            key=lambda c: (len(c.items), c.value),
            reverse=True,
        )
        with_items = [c for c in ranked if c.items]
        return with_items[:2] if with_items else ranked[:1]

    def to_dict(self) -> dict[str, Any]:
        """Serialize phang de ScenarioLogger ghi ra JSON (SPEC 12.0)."""
        return asdict(self)


def _champion_from_dict(data: dict[str, Any]) -> Champion:
    """JSON khong co tuple - position quay ve dang list, phai doi lai."""
    payload = dict(data)
    pos = payload.get("position")
    payload["position"] = tuple(pos) if pos is not None else None
    return Champion(**payload)


def state_from_dict(data: dict[str, Any]) -> GameState:
    """Dung lai GameState tu JSON da log. Dung o eval khi cham diem lai."""
    champs = {
        "board": [_champion_from_dict(c) for c in data.get("board", [])],
        "bench": [_champion_from_dict(c) for c in data.get("bench", [])],
        "shop": [_champion_from_dict(c) if c else None for c in data.get("shop", [])],
    }
    opponents = [OpponentBoard(**o) for o in data.get("opponents", [])]
    scalar = {
        k: v
        for k, v in data.items()
        if k not in ("board", "bench", "shop", "opponents")
    }
    return GameState(**scalar, **champs, opponents=opponents)
