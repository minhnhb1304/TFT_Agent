"""Trang thai tran co that su doi duoc loi khuyen khong? (moc M3)

Cau hoi nay phai TRA LOI DUOC BANG SO, khong phai bang niem tin. Buoi test
2026-09-16 cho thay mot he thong doc HUD rat cham chi ma `gold`, `level`,
`streak` khong he vao diem: doc dung hay sai thi xep hang van y nguyen.

Cach do: cham lai chinh ba the do voi mot trang thai TRUNG TINH - cung stage,
cung toc/he, nhung tien/cap/mau/chuoi dat ve muc "trung binh". Lech giua hai
lan cham chinh la phan dong gop cua trang thai.

Dung cho ca hai muc dich:
    - chi so `state_effect` trong bao cao (bao nhieu % man doi thu hang);
    - mot cau giai thich tren giao dien: "Vi 55 vang + thua 1: X +0,06".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from ..game_state.models import GameState

# Trang thai doi chieu. KHONG phai "trang thai dung" - chi la mot moc co dinh
# de do lech. Doi cac so nay thi moi so do cu deu phai do lai.
NEUTRAL_GOLD = 30
NEUTRAL_HP = 70
NEUTRAL_STREAK = 0
NEUTRAL_LEVEL_PACE = [3, 5, 6, 7, 8, 9]


def neutral_state(state: GameState) -> GameState:
    """Ban sao cua `state` voi tien/cap/mau/chuoi dat ve muc trung binh."""
    index = min(max(state.stage_number - 1, 0), len(NEUTRAL_LEVEL_PACE) - 1)
    return GameState(
        gold=NEUTRAL_GOLD,
        level=NEUTRAL_LEVEL_PACE[index],
        hp=NEUTRAL_HP,
        xp=0,
        xp_needed=None,
        stage=state.stage,
        streak=NEUTRAL_STREAK,
        board=list(state.board),
        bench=list(state.bench),
        item_components=list(state.item_components),
        completed_items=list(state.completed_items),
        active_traits=dict(state.active_traits),
    )


@dataclass
class StateEffect:
    """Phan dong gop cua trang thai tran vao mot xep hang."""

    deltas: dict[str, float] = field(default_factory=dict)      # apiName -> lech diem
    order_changed: bool = False
    top_changed: bool = False
    real_order: list[str] = field(default_factory=list)
    neutral_order: list[str] = field(default_factory=list)

    @property
    def biggest(self) -> tuple[str, float] | None:
        if not self.deltas:
            return None
        api = max(self.deltas, key=lambda k: abs(self.deltas[k]))
        return api, self.deltas[api]


def measure(advisor: Any, choices: Sequence[Any], state: GameState) -> StateEffect:
    """Cham hai lan - trang thai that va trang thai trung tinh - roi so."""
    real = advisor.rank(choices, state)
    neutral = advisor.rank(choices, neutral_state(state))
    neutral_totals = {e.api_name: e.total for e in neutral.entries}

    deltas = {
        e.api_name: round(e.total - neutral_totals.get(e.api_name, e.total), 4)
        for e in real.entries
    }
    return StateEffect(
        deltas=deltas,
        order_changed=real.order != neutral.order,
        top_changed=bool(real.order) and bool(neutral.order) and real.order[0] != neutral.order[0],
        real_order=list(real.order),
        neutral_order=list(neutral.order),
    )


def explain(effect: StateEffect, state: GameState, ranking: Any, min_delta: float = 0.02) -> str:
    """Mot cau cho nguoi choi, hoac chuoi rong neu trang thai khong doi gi dang ke.

    Chi noi khi CO chuyen: lech nho hon `min_delta` va thu hang khong doi thi
    im lang - mot cau "trang thai khong anh huong" chi lam loang man hinh.
    """
    biggest = effect.biggest
    if biggest is None:
        return ""
    api, delta = biggest
    if abs(delta) < min_delta and not effect.order_changed:
        return ""

    names = {e.api_name: e.name for e in getattr(ranking, "entries", [])}
    name = names.get(api, api)
    context = ", ".join(_context(state))
    moved = ""
    if api in effect.real_order and api in effect.neutral_order:
        before = effect.neutral_order.index(api) + 1
        after = effect.real_order.index(api) + 1
        if before != after:
            moved = f" (từ #{before} lên #{after})" if after < before else f" (từ #{before} xuống #{after})"
    sign = "+" if delta >= 0 else "−"
    return f"Vì {context}: {name} {sign}{abs(delta):.2f}{moved}"


def _context(state: GameState) -> list[str]:
    """Nhung truong that su lech khoi moc trung tinh - chi ke nhung cai do."""
    out: list[str] = []
    if state.gold >= NEUTRAL_GOLD + 15 or state.gold <= NEUTRAL_GOLD - 15:
        out.append(f"{state.gold} vàng")
    if state.streak <= -2:
        out.append(f"thua {abs(state.streak)}")
    elif state.streak >= 2:
        out.append(f"thắng {state.streak}")
    if state.hp <= NEUTRAL_HP - 20:
        out.append(f"HP {state.hp}")
    index = min(max(state.stage_number - 1, 0), len(NEUTRAL_LEVEL_PACE) - 1)
    gap = NEUTRAL_LEVEL_PACE[index] - state.level
    if gap > 0:
        out.append(f"chậm nhịp {gap} cấp")
    return out or ["trạng thái hiện tại"]
