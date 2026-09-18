"""Su kien mot vong lap doc khung hinh phat ra (moc M1, docs/playtest-fixes/core-session.md).

Chi la DU LIEU THUAN: khong Qt, khong numpy view, khong tham chieu nguoc ve
session. Nho the ca hai vo (replay co cua so, live co overlay) chi viec hien,
va test chay headless.

`AdviceReady` mang theo CA `state` lan `cards` - ke ca o khong doc duoc. Vo
KHONG duoc tu dung GameState hay tu doc the: do dung la loi da lam tien/EXP
vo nghia va lam mat the sau khi reroll trong run_replay.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Union

from ..decision.advisor import AdviceBundle
from ..decision.reroll_policy import RerollState
from ..game_state.models import GameState
from ..vision.augment_reader import CardRead


@dataclass(frozen=True)
class Idle:
    """Khong co gi moi o khung nay."""

    t: float


@dataclass(frozen=True)
class Status:
    """Thong bao cho nguoi dung (dang doc, thieu key, du lieu cu...)."""

    t: float
    message: str
    degraded: tuple[str, ...] = ()


@dataclass(frozen=True)
class Cleared:
    """Da roi man chon augment - vo phai xoa panel."""

    t: float


@dataclass(frozen=True)
class AdviceReady:
    """Mot xep hang moi kem DUNG trang thai da dung de tinh ra no."""

    t: float
    stage: str
    bundle: AdviceBundle
    state: GameState
    cards: tuple[CardRead, ...]
    rerolls: RerollState
    stale_fields: tuple[str, ...] = ()
    never_seen: tuple[str, ...] = ()
    # Cau noi ro trang thai tran da doi xep hang the nao (M3). Rong = khong doi
    # gi dang ke - im lang con hon mot cau "trang thai khong anh huong".
    state_note: str = ""
    latency_ms: dict[str, float] = field(default_factory=dict)

    @property
    def unread_slots(self) -> tuple[int, ...]:
        """O chua doc duoc - phai hien ra, khong duoc im lang bo qua."""
        return tuple(c.slot for c in self.cards if not c.api_names)

    def to_dict(self) -> dict[str, Any]:
        return {
            "t": round(self.t, 3),
            "stage": self.stage,
            "cards": [c.to_dict() for c in self.cards],
            "state": self.state.to_dict() if hasattr(self.state, "to_dict") else {},
            "stale_fields": list(self.stale_fields),
            "never_seen": list(self.never_seen),
            "latency_ms": {k: round(v, 2) for k, v in self.latency_ms.items()},
        }


LiveEvent = Union[Idle, Status, Cleared, AdviceReady]
