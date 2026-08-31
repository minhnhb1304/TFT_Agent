"""Position Advisor - dat quan (SPEC 3.5, uu tien 5).

Pham vi co y HEP. Dat quan toi uu la bai toan doi khang: no phu thuoc doi hinh
doi thu vong nay, ma doi hinh do thuoc Phase 7 (scouting) va mac dinh tat.

Vi the module nay chi kiem tra cac nguyen tac KHONG PHU THUOC DOI THU:

    - carry (con dang cam item) khong duoc dung hang truoc;
    - tank khong duoc dung hang cuoi;
    - carry khong nen dung o cot giua, vi do la noi assassin nhay vao;
    - hai carry khong nen dung sat nhau (mot AoE an ca hai).

Cac nguyen tac nay dung ke ca khi khong biet doi thu danh gi, va do la ly do
chung duoc chon. Loi khuyen phu thuoc doi thu se den o Phase 7 neu bat scouting.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..game_state.models import Champion, GameState
from .scoring.board_fit import COMPONENT_CARRY_TYPE

# Luoi hex cua TFT: 4 hang x 7 cot. Hang 0 la hang sat doi thu nhat.
FRONT_ROW = 0
BACK_ROW = 3
CENTER_COLUMNS = (2, 3, 4)


@dataclass
class PositionIssue:
    """Mot van de vi tri, kem de xuat cu the."""

    champion: str
    issue: str
    suggestion: str
    severity: int = 3   # 1 = nghiem trong nhat

    def to_dict(self) -> dict[str, str | int]:
        return {
            "champion": self.champion,
            "issue": self.issue,
            "suggestion": self.suggestion,
            "severity": self.severity,
        }


@dataclass
class PositionAdvice:
    issues: list[PositionIssue] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict:
        return {"issues": [i.to_dict() for i in self.issues], "note": self.note}


def is_tanky(champ: Champion) -> bool:
    """Suy ra vai tro do don tu item dang cam - khong tu ten tuong."""
    return any(COMPONENT_CARRY_TYPE.get(i) == "tank" for i in champ.items)


def is_carry(champ: Champion) -> bool:
    """Carry = dang cam it nhat 2 item, hoac cam item sat thuong."""
    if len(champ.items) >= 2:
        return True
    return any(COMPONENT_CARRY_TYPE.get(i) in ("AD", "AP") for i in champ.items)


class PositionAdvisor:
    """Kiem tra cac nguyen tac dat quan khong phu thuoc doi thu."""

    def evaluate(self, state: GameState) -> PositionAdvice:
        placed = [c for c in state.board if c.position is not None]
        if not placed:
            return PositionAdvice([], "Board trống — chưa có gì để kiểm tra")

        issues: list[PositionIssue] = []
        carries = [c for c in placed if is_carry(c)]

        for champ in placed:
            row, col = champ.position  # type: ignore[misc]
            if is_carry(champ) and row == FRONT_ROW:
                issues.append(
                    PositionIssue(
                        champ.name,
                        "Carry đang đứng hàng đầu",
                        f"Chuyển {champ.name} về hàng {BACK_ROW}",
                        severity=1,
                    )
                )
            elif is_carry(champ) and col in CENTER_COLUMNS and row >= BACK_ROW - 1:
                issues.append(
                    PositionIssue(
                        champ.name,
                        "Carry đứng giữa hàng sau — dễ ăn trọn kỹ năng diện rộng",
                        f"Dời {champ.name} ra cột biên (0 hoặc 6)",
                        severity=3,
                    )
                )

            if is_tanky(champ) and row >= BACK_ROW:
                issues.append(
                    PositionIssue(
                        champ.name,
                        "Đơn vị đỡ đòn đang đứng hàng cuối",
                        f"Đẩy {champ.name} lên hàng {FRONT_ROW}",
                        severity=2,
                    )
                )

        # Hai carry sat nhau: mot ky nang dien rong an ca hai.
        for a, b in _pairs(carries):
            if _adjacent(a, b):
                issues.append(
                    PositionIssue(
                        f"{a.name} + {b.name}",
                        "Hai carry đứng sát nhau",
                        "Tách ra hai cột biên đối diện",
                        severity=2,
                    )
                )

        issues.sort(key=lambda i: i.severity)
        note = "Chưa xét đội hình đối thủ (scouting là Phase 7, mặc định tắt)"
        return PositionAdvice(issues, note)


def _pairs(items: list[Champion]):
    for i, a in enumerate(items):
        for b in items[i + 1 :]:
            yield a, b


def _adjacent(a: Champion, b: Champion) -> bool:
    if a.position is None or b.position is None:
        return False
    return abs(a.position[0] - b.position[0]) <= 1 and abs(a.position[1] - b.position[1]) <= 1
