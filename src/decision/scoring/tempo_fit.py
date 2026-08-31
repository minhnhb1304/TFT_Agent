"""Thanh phan w5 - TempoFit: do tham lam theo mau (SPEC 3.5.4).

Mot augment "scaling" o 20 HP co the la mot lua chon CHET: khong con du vong
de no lon. Cung augment do o 90 HP lai la lua chon tot nhat ban co. HP la bien
duy nhat trong game noi cho ta biet con bao nhieu thoi gian.

Phat khong doi xung, co chu y: scaling luc sap chet bi phat NANG hon la
immediate luc con day mau duoc thuong. Ly do la hai sai lam khong cung gia:
chon scaling khi sap chet thi thua luon, con chon immediate khi con day mau
chi la kem toi uu.
"""

from __future__ import annotations

from ...game_state.models import GameState
from ...knowledge.augment_features import AugmentFeature
from .types import ComponentScore, ScoringConfig, clamp01, neutral

NAME = "tempo_fit"


class TempoFitScorer:
    """Cham diem tempo cua augment theo HP hien tai."""

    def __init__(self, config: ScoringConfig) -> None:
        tune = config.tune(NAME)
        self.low_hp = float(tune.get("low_hp", 35))
        self.high_hp = float(tune.get("high_hp", 70))

    def urgency(self, state: GameState) -> float:
        """Do cap bach: 1.0 khi HP <= low_hp, 0.0 khi HP >= high_hp."""
        span = self.high_hp - self.low_hp
        if span <= 0:
            return 0.0 if state.hp >= self.high_hp else 1.0
        return clamp01((self.high_hp - state.hp) / span)

    def __call__(
        self, api_name: str, feature: AugmentFeature | None, state: GameState
    ) -> ComponentScore:
        if feature is None:
            return neutral(NAME, "Không có dữ liệu đặc trưng cho augment này")

        urgency = self.urgency(state)

        if feature.tempo == "immediate":
            score = 0.5 + 0.5 * urgency
            if urgency >= 0.6:
                reason = f"HP {state.hp} — cần sức mạnh ngay, augment này cho ngay"
            else:
                reason = f"HP {state.hp} còn thoải mái — sức mạnh tức thì là an toàn"
        else:
            score = 1.0 - 0.7 * urgency
            if urgency >= 0.6:
                reason = f"HP {state.hp} — augment cộng dồn khó kịp phát huy"
            else:
                reason = f"HP {state.hp} còn thoải mái — đủ thời gian để cộng dồn"

        return ComponentScore(
            NAME,
            clamp01(score),
            reason,
            {"tempo": feature.tempo, "hp": state.hp, "urgency": round(urgency, 3)},
        )
