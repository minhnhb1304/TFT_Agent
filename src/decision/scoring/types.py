"""Kieu du lieu dung chung cho 5 thanh phan cham diem (SPEC 3.5.4).

QUY UOC NGON NGU trong package nay: docstring va comment viet khong dau (dong
bo voi phan con lai cua source), nhung `reason` la CHUOI HIEN LEN OVERLAY cho
nguoi dung doc, nen viet tieng Viet co dau day du.

QUY UOC DIEM: moi thanh phan tra ve so trong [0, 1] voi 0.5 la TRUNG TINH.
Trung tinh khong phai "trung binh" ma la "khong co tin hieu" - va no phai
phan biet duoc voi "co tin hieu va tin hieu do la xau" (diem thap). Nham hai
cai nay se lam augment thieu du lieu bi phat oan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

NEUTRAL = 0.5


def clamp01(x: float) -> float:
    """Ep ve [0, 1]. Moi cong thuc cham diem deu di qua day."""
    return max(0.0, min(1.0, float(x)))


@dataclass(frozen=True)
class ComponentScore:
    """Ket qua cua MOT thanh phan cham diem.

    `reason` la bat buoc, khong phai trang tri:
      - overlay hien xep hang KEM ly do -> la advisor chu khong phai hop den;
      - khi hai augment diem sat nhau, ly do moi la thu giup nguoi choi quyet;
      - ablation study (SPEC 12.4) can doc duoc tung thanh phan dong gop gi.
    """

    name: str
    score: float
    reason: str
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def is_neutral(self) -> bool:
        return abs(self.score - NEUTRAL) < 1e-9


def neutral(name: str, reason: str, **detail: Any) -> ComponentScore:
    """Tao diem trung tinh - dung khi THIEU DU LIEU, khong phai khi du lieu xau."""
    return ComponentScore(name, NEUTRAL, reason, detail)


@dataclass
class ScoringConfig:
    """Trong so + tham so, nap tu config/scoring_weights.yaml.

    Ablation (SPEC 12.4) chi duoc phep cham vao `weights`. `tuning` la hanh vi
    noi tai cua tung component va phai giu nguyen giua cac lan ablation, neu
    khong thi khong con biet delta den tu dau.
    """

    weights: dict[str, float] = field(default_factory=dict)
    tuning: dict[str, dict[str, Any]] = field(default_factory=dict)

    COMPONENTS = ("base", "board_fit", "econ_fit", "item_fit", "tempo_fit")

    # Cac khoi cau hinh nam o cap CAO NHAT trong YAML nhung duoc doc qua
    # `tuning`. `comp_selector` la truong hop duy nhat hien nay: no khong phai
    # tham so cua mot scorer nen khong thuoc `tuning` ve mat ngu nghia, nhung
    # CompSelector lai tra no bang cfg.tune("comp_selector").
    #
    # Truoc khi co dong nay, ca khoi comp_selector: trong scoring_weights.yaml
    # la CONFIG CHET - sua so trong file khong co tac dung gi, CompSelector im
    # lang dung DEFAULT_WEIGHTS trong code. Khong test nao bat duoc vi hai bo
    # gia tri tinh co trung nhau.
    TOP_LEVEL_TUNING = ("comp_selector",)

    @classmethod
    def load(cls, path: str | Path) -> "ScoringConfig":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        tuning = dict(data.get("tuning") or {})
        for key in cls.TOP_LEVEL_TUNING:
            if key in data and key not in tuning:
                tuning[key] = data[key]
        return cls(
            weights={k: float(v) for k, v in (data.get("weights") or {}).items()},
            tuning=tuning,
        )

    @classmethod
    def default(cls) -> "ScoringConfig":
        """Cau hinh mac dinh khi khong co file - dung cho test va demo."""
        return cls(
            weights={
                "base": 0.30, "board_fit": 0.30, "econ_fit": 0.15,
                "item_fit": 0.15, "tempo_fit": 0.10,
            },
            tuning={
                "base": {"best_place": 3.5, "worst_place": 5.0, "min_sample_n": 200},
                "board_fit": {
                    "trait_weight": 0.6, "carry_weight": 0.4,
                    "active_trait_min_units": 2,
                },
                "econ_fit": {"stage_curve": [1.0, 1.0, 0.8, 0.5, 0.25, 0.1]},
                "item_fit": {
                    "exact_component": 1.0, "generic_component": 0.6,
                    "completed_item": 0.8,
                },
                "tempo_fit": {"low_hp": 35, "high_hp": 70},
            },
        )

    def tune(self, component: str) -> dict[str, Any]:
        """Tham so cua mot component, rong neu khong khai bao."""
        return self.tuning.get(component, {})

    def weight(self, component: str) -> float:
        return float(self.weights.get(component, 0.0))

    def with_ablation(self, disabled: str | None) -> "ScoringConfig":
        """Ban sao voi MOT trong so bi tat - dau vao cua SPEC 12.4.

        Cac trong so con lai duoc chuan hoa lai de tong van bang 1. Chuan hoa
        la phep bien doi don dieu nen KHONG doi thu hang trong cung mot cau
        hinh; no chi giu diem tuyet doi so sanh duoc giua cac cau hinh.
        """
        if disabled is None:
            return ScoringConfig(dict(self.weights), self.tuning)
        remaining = {k: (0.0 if k == disabled else v) for k, v in self.weights.items()}
        total = sum(remaining.values())
        if total > 0:
            remaining = {k: v / total for k, v in remaining.items()}
        return ScoringConfig(remaining, self.tuning)

    def only(self, component: str) -> "ScoringConfig":
        """Ban sao chi giu MOT trong so - dong quan trong nhat cua bang ablation.

        `only("base")` chinh la baseline "chi dung stats tinh": no tra loi
        dinh luong cho cau hoi vi sao phai lam advisor dong thay vi bang stats.
        """
        weights = {k: (1.0 if k == component else 0.0) for k in self.weights}
        return ScoringConfig(weights, self.tuning)
