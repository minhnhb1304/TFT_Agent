"""Theo doi va on dinh trang thai tro choi qua nhieu khung hinh (SPEC 3.2, 3.3).

Giai quyet hai van de:
1. Loc nhieu OCR: majority vote trong cua so `window` khung hinh gan nhat.
2. Man chon augment: thanh HUD bi an -> carry-forward gia tri hop le cuoi cung.
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any

from ..vision.hud_reader import HUD_FIELDS, HudField, HudReading
from .models import GameState

# Cac truong HUD duoc theo doi va dong bo voi GameState
HUD_TRACKED_FIELDS: tuple[HudField, ...] = ("stage", "gold", "level", "xp", "hp")


@dataclass
class GameStateTracker:
    """Theo doi lich su doc HUD va duy tri GameState on dinh."""

    window: int = 5
    _history: deque[HudReading] = field(default_factory=lambda: deque(maxlen=5))
    _last_good: dict[str, Any] = field(default_factory=dict)
    _stale: set[str] = field(default_factory=set)
    _never_seen: set[str] = field(default_factory=lambda: set(HUD_TRACKED_FIELDS))

    def __post_init__(self) -> None:
        if self._history.maxlen != self.window:
            self._history = deque(self._history, maxlen=self.window)

    def update(self, reading: HudReading) -> None:
        """Them mot reading moi vao lich su va giai quyet cac truong."""
        self._history.append(reading)
        self._resolve()

    def _resolve(self) -> None:
        if not self._history:
            self._stale = set()
            self._never_seen = set(HUD_TRACKED_FIELDS)
            return

        current = self._history[-1]
        stale: set[str] = set()
        never_seen: set[str] = set()

        for f_name in HUD_TRACKED_FIELDS:
            read = current.get(f_name)
            # Truong co mat va co gia tri hop le o khung hien tai
            if read.present and read.value is not None:
                # Majority vote trong window
                valid_vals = [
                    r.get(f_name).value
                    for r in self._history
                    if r.get(f_name).present and r.get(f_name).value is not None
                ]
                # Dem so phieu
                counts = Counter(valid_vals)
                # Tie-breaking: uu tien gia tri xuat hien gan nhat trong lich su
                reversed_history_vals = [
                    r.get(f_name).value
                    for r in reversed(self._history)
                    if r.get(f_name).present and r.get(f_name).value is not None
                ]
                # Tim count cao nhat
                max_count = max(counts.values())
                candidates = {val for val, count in counts.items() if count == max_count}
                winner = None
                for val in reversed_history_vals:
                    if val in candidates:
                        winner = val
                        break
                self._last_good[f_name] = winner
            else:
                # Vang mat o khung hien tai (hoac misread)
                if f_name in self._last_good:
                    stale.add(f_name)
                else:
                    never_seen.add(f_name)

        self._stale = stale
        self._never_seen = never_seen

    def state(self, *, traits: dict[str, int] | None = None) -> GameState:
        """Xuat GameState voi cac gia tri da phan giai tu HUD va traits kem theo."""
        default_state = GameState()
        defaults = {
            "gold": default_state.gold,
            "level": default_state.level,
            "hp": default_state.hp,
            "xp": default_state.xp,
            "stage": default_state.stage,
        }

        resolved: dict[str, Any] = {}
        for f_name in HUD_TRACKED_FIELDS:
            if f_name in self._last_good:
                resolved[f_name] = self._last_good[f_name]
            else:
                resolved[f_name] = defaults[f_name]

        return GameState(
            gold=int(resolved["gold"]),
            level=int(resolved["level"]),
            hp=int(resolved["hp"]),
            xp=int(resolved["xp"]),
            stage=str(resolved["stage"]),
            active_traits=dict(traits or {}),
        )

    @property
    def stale(self) -> tuple[str, ...]:
        """Cac truong phuc vu tu khung cu vi khung hien tai bi che/vang mat."""
        return tuple(f for f in HUD_TRACKED_FIELDS if f in self._stale)

    @property
    def never_seen(self) -> tuple[str, ...]:
        """Cac truong chua tung doc duoc gia tri hop le nao, dang o default."""
        return tuple(f for f in HUD_TRACKED_FIELDS if f in self._never_seen)

    def reset(self) -> None:
        """Xoa toan bo lich su va gia tri nho."""
        self._history.clear()
        self._last_good.clear()
        self._stale.clear()
        self._never_seen = set(HUD_TRACKED_FIELDS)
