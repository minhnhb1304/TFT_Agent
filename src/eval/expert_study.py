"""SPEC 12.3 - dong thuan chuyen gia.

Quy trinh:
    1. `export_scenarios()` xuat ~50 tinh huong ra JSON de nguoi choi rank cao
       xep hang DOC LAP. Ban xuat co CHU Y KHONG kem xep hang cua advisor -
       neu thay truoc, chuyen gia se bi neo (anchoring) va so lieu thanh vo nghia.
    2. Chuyen gia dien `expert_ranking` vao tung muc.
    3. `analyze()` tinh top-1 agreement va Cohen's kappa.
    4. So them voi baseline "chi dung stats tinh" de tach phan dong gop cua
       nhan thuc board (SPEC 12.3 - doi chung).

Cohen's kappa duoc tinh tren su kien "advisor va chuyen gia co chon cung mot
augment lam so 1 khong", tren khong gian nhan la cac augment duoc chao trong
tung tinh huong. Kappa quan trong hon ti le dong thuan tho vi voi 3 lua chon,
doan bua da trung 33% roi.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from .scenario_logger import Scenario


@dataclass
class ExpertEntry:
    """Mot tinh huong da co ca xep hang cua advisor lan cua chuyen gia."""

    scenario_id: str
    candidates: list[str]
    advisor_ranking: list[str]
    expert_ranking: list[str]
    expert_id: str = "expert-1"

    @property
    def advisor_top(self) -> str | None:
        return self.advisor_ranking[0] if self.advisor_ranking else None

    @property
    def expert_top(self) -> str | None:
        return self.expert_ranking[0] if self.expert_ranking else None

    @property
    def agrees(self) -> bool:
        return self.advisor_top is not None and self.advisor_top == self.expert_top


@dataclass
class ExpertReport:
    n: int = 0
    top1_agreement: float = 0.0
    kappa: float = 0.0
    expected_agreement: float = 0.0
    per_expert: dict[str, float] = field(default_factory=dict)

    def report(self) -> str:
        return (
            f"Dong thuan top-1: {self.top1_agreement:.1%} tren {self.n} tinh huong\n"
            f"Cohen's kappa: {self.kappa:.3f} "
            f"(dong thuan ky vong do ngau nhien: {self.expected_agreement:.1%})\n"
            f"{_kappa_verdict(self.kappa)}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "n": self.n,
            "top1_agreement": round(self.top1_agreement, 4),
            "kappa": round(self.kappa, 4),
            "expected_agreement": round(self.expected_agreement, 4),
            "per_expert": {k: round(v, 4) for k, v in self.per_expert.items()},
        }


def _kappa_verdict(kappa: float) -> str:
    """Doc kappa theo thang Landis & Koch - de bao cao khong tu khen."""
    if kappa < 0.0:
        return "Muc do dong thuan: te hon ngau nhien."
    if kappa < 0.20:
        return "Muc do dong thuan: khong dang ke."
    if kappa < 0.40:
        return "Muc do dong thuan: yeu."
    if kappa < 0.60:
        return "Muc do dong thuan: trung binh."
    if kappa < 0.80:
        return "Muc do dong thuan: kha."
    return "Muc do dong thuan: rat cao."


def export_scenarios(
    scenarios: Iterable[Scenario], out_path: str | Path, limit: int = 50
) -> Path:
    """Xuat ban de chuyen gia xep hang - KHONG kem ket qua cua advisor.

    Giau xep hang cua advisor la yeu cau phuong phap, khong phai tuy chon: cho
    chuyen gia thay truoc thi so lieu dong thuan do niem tin vao advisor chu
    khong do chat luong cua no.
    """
    payload: list[dict[str, Any]] = []
    for i, scenario in enumerate(list(scenarios)[:limit], start=1):
        state = scenario.game_state
        payload.append({
            "scenario_id": scenario.path.stem if scenario.path else f"s{i:03d}",
            "frame_ref": scenario.frame_ref,
            "tinh_huong": {
                "stage": state.stage,
                "hp": state.hp,
                "gold": state.gold,
                "level": state.level,
                "traits": state.active_traits,
                "board": [
                    {"ten": c.name, "sao": c.star_level, "items": c.items}
                    for c in state.board
                ],
                "manh_trang_bi": state.item_components,
                "augment_dang_co": state.augments,
            },
            "candidates": list(scenario.ranking),
            "expert_ranking": [],   # <- chuyen gia dien vao day
        })

    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def load_expert_entries(
    export_path: str | Path, scenarios: Iterable[Scenario], expert_id: str = "expert-1"
) -> list[ExpertEntry]:
    """Ghep ban chuyen gia da dien voi xep hang cua advisor."""
    filled = json.loads(Path(export_path).read_text(encoding="utf-8"))
    by_id = {
        (s.path.stem if s.path else ""): s for s in scenarios
    }

    entries: list[ExpertEntry] = []
    for row in filled:
        expert_ranking = row.get("expert_ranking") or []
        if not expert_ranking:
            continue    # chua dien thi bo qua, khong doan ho
        scenario = by_id.get(row.get("scenario_id", ""))
        advisor_ranking = list(scenario.ranking) if scenario else list(row.get("candidates", []))
        entries.append(
            ExpertEntry(
                scenario_id=row.get("scenario_id", ""),
                candidates=list(row.get("candidates", [])),
                advisor_ranking=advisor_ranking,
                expert_ranking=list(expert_ranking),
                expert_id=row.get("expert_id", expert_id),
            )
        )
    return entries


def cohen_kappa(entries: Sequence[ExpertEntry]) -> tuple[float, float, float]:
    """Kappa tren lua chon top-1.

    Returns:
        (kappa, dong thuan quan sat, dong thuan ky vong)
    """
    valid = [e for e in entries if e.advisor_top and e.expert_top]
    if not valid:
        return 0.0, 0.0, 0.0

    observed = sum(1 for e in valid if e.agrees) / len(valid)

    # Dong thuan ky vong: tinh tu phan phoi bien cua tung ben tren toan bo nhan.
    labels = {e.advisor_top for e in valid} | {e.expert_top for e in valid}
    n = len(valid)
    expected = 0.0
    for label in labels:
        p_advisor = sum(1 for e in valid if e.advisor_top == label) / n
        p_expert = sum(1 for e in valid if e.expert_top == label) / n
        expected += p_advisor * p_expert

    kappa = (observed - expected) / (1 - expected) if expected < 1 else 1.0
    return kappa, observed, expected


def analyze(entries: Sequence[ExpertEntry]) -> ExpertReport:
    """Tinh dong thuan top-1 va kappa, tach theo tung chuyen gia."""
    if not entries:
        return ExpertReport()

    kappa, observed, expected = cohen_kappa(entries)

    per_expert: dict[str, float] = {}
    for expert in {e.expert_id for e in entries}:
        subset = [e for e in entries if e.expert_id == expert]
        per_expert[expert] = sum(1 for e in subset if e.agrees) / len(subset)

    return ExpertReport(
        n=len(entries),
        top1_agreement=observed,
        kappa=kappa,
        expected_agreement=expected,
        per_expert=per_expert,
    )
