"""Thanh phan w3 - EconFit: gia tri kinh te x do hop thoi diem (SPEC 3.5.4).

Mot augment kinh te khong co gia tri co dinh: no la mot khoan DAU TU, va gia
tri phu thuoc vao con bao nhieu vong de thu hoi. Cung mot augment cho 10 gold
o 2-1 va o 5-1 la hai thu khac han nhau. Do la toan bo noi dung cua thanh phan
nay, va cung la ly do no khong the la mot cot trong bang stats tinh.

Tu M3, thanh phan nay con doc TIEN va CHUOI - truoc do hai truong nay duoc doc
tu man hinh roi vut di (do duoc: doc HUD dung hay sai thi xep hang khong doi).
Hai dieu chinh, deu la LUA CHON chua fit tren du lieu, va deu tat duoc bang
config de ablation:

  - Da kich tran lai (>= `interest_cap_gold`): mot augment sinh vang bot gia
    tri, vi phan lon gia tri cua no la day ban toi moc lai tiep theo.
  - Dang thua lien tiep ma HP con chiu duoc: gia tri kinh te tang, vi day dung
    la luc mot the "lose streak" doi lay von.
"""

from __future__ import annotations

from ...game_state.models import GameState
from ...knowledge.augment_features import AugmentFeature
from .types import ComponentScore, ScoringConfig, clamp01, neutral

NAME = "econ_fit"

DEFAULT_CURVE = [1.0, 1.0, 0.8, 0.5, 0.25, 0.1]
DEFAULT_INTEREST_CAP = 50      # vang: tu day tro len la lai da kich tran
DEFAULT_POOR_GOLD = 20
DEFAULT_GOLD_SWING = 0.10      # bien do dieu chinh theo tien
DEFAULT_LOSS_STREAK = 3        # thua lien tiep tu day tro len
DEFAULT_STREAK_BONUS = 0.08
DEFAULT_STREAK_MIN_HP = 40     # HP duoi muc nay thi khong con "doi mau lay von"


class EconFitScorer:
    """Cham diem augment kinh te theo stage hien tai."""

    def __init__(self, config: ScoringConfig) -> None:
        tune = config.tune(NAME)
        curve = tune.get("stage_curve") or DEFAULT_CURVE
        self.curve = [float(x) for x in curve]
        self.interest_cap = float(tune.get("interest_cap_gold", DEFAULT_INTEREST_CAP))
        self.poor_gold = float(tune.get("poor_gold", DEFAULT_POOR_GOLD))
        self.gold_swing = float(tune.get("gold_swing", DEFAULT_GOLD_SWING))
        self.loss_streak = int(tune.get("loss_streak", DEFAULT_LOSS_STREAK))
        self.streak_bonus = float(tune.get("loss_streak_bonus", DEFAULT_STREAK_BONUS))
        self.streak_min_hp = float(tune.get("loss_streak_min_hp", DEFAULT_STREAK_MIN_HP))

    def gold_adjustment(self, state: GameState) -> tuple[float, str]:
        """Dieu chinh theo tien dang giu. Tra ve (do lech diem, ly do)."""
        if self.gold_swing <= 0:
            return 0.0, ""
        if state.gold >= self.interest_cap:
            return -self.gold_swing, f"{state.gold} vàng — lãi đã kịch trần, lõi tiền bớt giá trị"
        if state.gold <= self.poor_gold:
            return self.gold_swing, f"{state.gold} vàng — đang thiếu vốn, lõi tiền đáng hơn"
        return 0.0, ""

    def streak_adjustment(self, state: GameState) -> tuple[float, str]:
        """Thua lien tiep ma con chiu duoc mau -> dang la luc doi von."""
        if self.streak_bonus <= 0 or state.streak > -self.loss_streak:
            return 0.0, ""
        if state.hp < self.streak_min_hp:
            return 0.0, ""
        return self.streak_bonus, f"đang thua {abs(state.streak)} — đúng lúc đổi máu lấy vốn"

    def stage_coefficient(self, state: GameState) -> float:
        """He so thoi diem: 1.0 o dau van, tien ve 0 khi van dau sap ket thuc."""
        idx = min(max(state.stage_number - 1, 0), len(self.curve) - 1)
        return self.curve[idx]

    def __call__(
        self, api_name: str, feature: AugmentFeature | None, state: GameState
    ) -> ComponentScore:
        if feature is None:
            return neutral(NAME, "Không có dữ liệu đặc trưng cho augment này")

        if feature.econ_value <= 0:
            return neutral(
                NAME,
                "Không phải augment kinh tế — không tính điểm kinh tế",
                econ_value=0,
            )

        coeff = self.stage_coefficient(state)
        strength = feature.econ_value / 3.0

        # Diem lech khoi trung tinh theo CA hai chieu: econ manh o stage som
        # keo len, chinh no o stage muon keo xuong. Neu chi cong duong thi
        # advisor se khuyen an econ o 5-2, va do la loi khuyen sai that.
        score = 0.5 + strength * (coeff - 0.5)
        gold_delta, gold_reason = self.gold_adjustment(state)
        streak_delta, streak_reason = self.streak_adjustment(state)
        score = clamp01(score + gold_delta + streak_delta)

        if coeff >= 0.8:
            verdict = f"còn {6 - state.stage_number} màn để sinh lời — kịp hoàn vốn"
        elif coeff >= 0.5:
            verdict = "đã qua nửa ván — hoàn vốn vừa đủ"
        else:
            verdict = "quá muộn để đầu tư kinh tế"

        extra = " · ".join(x for x in (gold_reason, streak_reason) if x)
        reason = f"Giá trị kinh tế {feature.econ_value}/3 ở {state.stage} — {verdict}"
        return ComponentScore(
            NAME,
            score,
            f"{reason} · {extra}" if extra else reason,
            {
                "econ_value": feature.econ_value,
                "stage": state.stage,
                "stage_coefficient": coeff,
                "gold": state.gold,
                "streak": state.streak,
                "gold_delta": round(gold_delta, 3),
                "streak_delta": round(streak_delta, 3),
            },
        )
