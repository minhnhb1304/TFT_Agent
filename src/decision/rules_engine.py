"""Rules Engine - kinh te, len cap, roll (SPEC 3.5.1).

Cac moc trong file nay la CHUAN NHIEU SET, chua verify lai voi 18.1. Chung
duoc giu o dang hang so co ten va co nhan `confidence` de phan biet ro voi
nhung thu da do duoc (tier ladder, dac trung augment).

Interest va streak thi khac: day la co che nen cua TFT, on dinh qua nhieu nam,
va co the kiem chung ngay trong mot van dau bang cach doc gold. Chung duoc
danh dau confidence cao hon, va co test khoa lai.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..game_state.models import GameState

# Nguong interest: moi 10 gold duoc +1, toi da +5.
INTEREST_STEP = 10
INTEREST_CAP = 5

# Streak (thang hoac thua lien tiep) -> gold thuong.
STREAK_BONUS = {2: 1, 3: 2, 4: 3}
STREAK_MAX_BONUS = 3

# Nguong gold nen giu de an du interest.
ECON_TARGET = 50

# HP duoi muc nay thi phai uu tien suc manh ngay thay vi tich luy.
DANGER_HP = 50
CRITICAL_HP = 30


@dataclass
class Advice:
    """Mot loi khuyen kem ly do va do tin cay cua chinh loi khuyen do."""

    topic: str
    message: str
    reason: str
    confidence: str = "quy uoc nhieu set"   # hoac "do duoc"
    priority: int = 5                        # 1 = gap nhat

    def to_dict(self) -> dict[str, str | int]:
        return {
            "topic": self.topic,
            "message": self.message,
            "reason": self.reason,
            "confidence": self.confidence,
            "priority": self.priority,
        }


def interest_income(gold: int) -> int:
    """Lai theo gold dang giu. Do duoc ngay trong game bang cach doc gold."""
    return min(max(gold, 0) // INTEREST_STEP, INTEREST_CAP)


def streak_income(streak: int) -> int:
    """Thuong chuoi thang/thua. `streak` la do dai chuoi, khong phan biet dau."""
    length = abs(int(streak))
    if length < 2:
        return 0
    return STREAK_BONUS.get(length, STREAK_MAX_BONUS)


def projected_income(state: GameState, base: int = 5) -> int:
    """Thu nhap du kien vong toi: co ban + lai + chuoi."""
    return base + interest_income(state.gold) + streak_income(state.streak)


@dataclass
class EconomyRules:
    """Sinh loi khuyen kinh te theo stage va tinh trang mau."""

    econ_target: int = ECON_TARGET

    def evaluate(self, state: GameState) -> list[Advice]:
        advice: list[Advice] = []
        stage = state.stage_number

        advice.append(
            Advice(
                "income",
                f"Vòng tới dự kiến +{projected_income(state)} vàng",
                f"lãi {interest_income(state.gold)} + chuỗi {streak_income(state.streak)}",
                confidence="đo được",
                priority=6,
            )
        )

        if state.hp <= CRITICAL_HP:
            advice.append(
                Advice(
                    "tempo",
                    "Dồn toàn bộ vàng để mạnh ngay vòng này",
                    f"HP {state.hp} — giữ vàng lúc này là giữ cho ván sau không tồn tại",
                    priority=1,
                )
            )
        elif state.hp <= DANGER_HP and stage >= 4:
            advice.append(
                Advice(
                    "tempo",
                    "Cân nhắc roll xuống để ổn định đội hình",
                    f"HP {state.hp} ở màn {stage} — mất máu nhanh hơn tốc độ tích lũy",
                    priority=2,
                )
            )
        elif state.gold < self.econ_target:
            advice.append(
                Advice(
                    "econ",
                    f"Giữ vàng tới mốc {self.econ_target} để ăn đủ lãi",
                    f"đang có {state.gold} — còn thiếu {self.econ_target - state.gold}",
                    priority=4,
                )
            )
        else:
            advice.append(
                Advice(
                    "econ",
                    "Đã đủ mốc lãi tối đa — vàng dư nên dùng để lên cấp hoặc roll",
                    f"đang có {state.gold} vàng, lãi đã kịch trần",
                    priority=4,
                )
            )

        advice.append(self._level_advice(state))
        return sorted(advice, key=lambda a: a.priority)

    @staticmethod
    def _level_advice(state: GameState) -> Advice:
        """Moc len cap theo stage - quy uoc nhieu set, chua verify 18.1."""
        stage, rnd = state.stage_number, state.round_number
        targets = {2: (5, "2-5"), 3: (6, "3-2"), 4: (7, "4-1"), 5: (8, "5-1")}
        target = targets.get(stage)
        if not target:
            return Advice(
                "level",
                "Chưa tới mốc lên cấp cố định",
                f"đang ở {state.stage}",
                priority=7,
            )
        level, moment = target
        if state.level < level:
            return Advice(
                "level",
                f"Nên lên cấp {level} quanh {moment}",
                f"đang cấp {state.level} ở {state.stage}",
                priority=3,
            )
        return Advice(
            "level",
            f"Cấp {state.level} đang đúng hoặc vượt mốc {moment}",
            f"mốc quy ước cho màn {stage} là cấp {level}",
            priority=6,
        )
