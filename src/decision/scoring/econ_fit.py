"""Thanh phan w3 - EconFit: gia tri kinh te x do hop thoi diem (SPEC 3.5.4).

Mot augment kinh te khong co gia tri co dinh: no la mot khoan DAU TU, va gia
tri phu thuoc vao con bao nhieu vong de thu hoi. Cung mot augment cho 10 gold
o 2-1 va o 5-1 la hai thu khac han nhau. Do la toan bo noi dung cua thanh phan
nay, va cung la ly do no khong the la mot cot trong bang stats tinh.
"""

from __future__ import annotations

from ...game_state.models import GameState
from ...knowledge.augment_features import AugmentFeature
from .types import ComponentScore, ScoringConfig, clamp01, neutral

NAME = "econ_fit"

DEFAULT_CURVE = [1.0, 1.0, 0.8, 0.5, 0.25, 0.1]


class EconFitScorer:
    """Cham diem augment kinh te theo stage hien tai."""

    def __init__(self, config: ScoringConfig) -> None:
        tune = config.tune(NAME)
        curve = tune.get("stage_curve") or DEFAULT_CURVE
        self.curve = [float(x) for x in curve]

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
        score = clamp01(0.5 + strength * (coeff - 0.5))

        if coeff >= 0.8:
            verdict = f"còn {6 - state.stage_number} màn để sinh lời — kịp hoàn vốn"
        elif coeff >= 0.5:
            verdict = "đã qua nửa ván — hoàn vốn vừa đủ"
        else:
            verdict = "quá muộn để đầu tư kinh tế"

        return ComponentScore(
            NAME,
            score,
            f"Giá trị kinh tế {feature.econ_value}/3 ở {state.stage} — {verdict}",
            {
                "econ_value": feature.econ_value,
                "stage": state.stage,
                "stage_coefficient": coeff,
                "gold": state.gold,
            },
        )
