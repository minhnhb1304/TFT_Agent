"""SPEC 12.4 - ablation study: tat tung trong so, do delta.

DONG QUAN TRONG NHAT CUA BANG LA DONG "chi w1".

"Chi w1" = chi dung so lieu tinh = dung bang stats tinh. Delta giua no va mo
hinh day du chinh la cau tra loi DINH LUONG cho cau hoi vi sao phai lam mot
advisor doc board thay vi mot bang tra cuu. Neu delta xap xi 0 thi do VAN LA
mot ket qua nghien cuu hop le va phai bao cao trung thuc, khong duoc giau.

Cham diem lai chay hoan toan offline tren dataset da log: khong can game, khong
can key. Do la ly do ScenarioLogger phai ghi DU GameState chu khong phai chi
ket qua.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from ..decision.augment_advisor import AugmentAdvisor
from ..decision.scoring.types import ScoringConfig
from ..knowledge.augment_features import FeatureTable
from ..knowledge.stats_provider import AugmentStatsProvider, NullProvider
from .correlation import spearman
from .scenario_logger import Scenario


@dataclass
class AblationRow:
    """Mot cau hinh trong bang ablation."""

    label: str
    disabled: str | None
    top1_change_rate: float = 0.0
    mean_rank_shift: float = 0.0
    kendall_tau: float = 1.0
    rho_vs_placement: float | None = None
    n: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "disabled": self.disabled,
            "top1_change_rate": round(self.top1_change_rate, 4),
            "mean_rank_shift": round(self.mean_rank_shift, 4),
            "kendall_tau": round(self.kendall_tau, 4),
            "rho_vs_placement": (
                None if self.rho_vs_placement is None else round(self.rho_vs_placement, 4)
            ),
            "n": self.n,
        }


@dataclass
class AblationReport:
    rows: list[AblationRow] = field(default_factory=list)
    n_scenarios: int = 0

    def table(self) -> str:
        """Bang van ban - dan thang duoc vao chuong ket qua."""
        head = (
            f"{'Cau hinh':<22}{'doi top-1':>11}{'dich hang TB':>14}"
            f"{'tau':>8}{'rho vs placement':>19}"
        )
        lines = [head, "-" * len(head)]
        for row in self.rows:
            rho = "-" if row.rho_vs_placement is None else f"{row.rho_vs_placement:.3f}"
            lines.append(
                f"{row.label:<22}{row.top1_change_rate:>10.1%}"
                f"{row.mean_rank_shift:>14.2f}{row.kendall_tau:>8.3f}{rho:>19}"
            )
        lines.append(f"\nn = {self.n_scenarios} scenario")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {"n_scenarios": self.n_scenarios, "rows": [r.to_dict() for r in self.rows]}


def kendall_tau(a: Sequence[str], b: Sequence[str]) -> float:
    """Tuong quan hang Kendall giua hai thu tu tren cung tap phan tu.

    Dung tau chu khong phai "co doi top-1 khong" vi tau bat duoc ca nhung thay
    doi nho hon: mot thanh phan co the khong doi quan quan nhung van dao lon
    toan bo phan con lai, va do van la dong gop that.
    """
    common = [x for x in a if x in set(b)]
    if len(common) < 2:
        return 1.0
    pos_b = {x: i for i, x in enumerate(b)}
    concordant = discordant = 0
    for i in range(len(common)):
        for j in range(i + 1, len(common)):
            x, y = common[i], common[j]
            if pos_b[x] < pos_b[y]:
                concordant += 1
            else:
                discordant += 1
    total = concordant + discordant
    return (concordant - discordant) / total if total else 1.0


class AblationRunner:
    """Cham diem lai toan bo dataset voi cac cau hinh trong so khac nhau."""

    def __init__(
        self,
        features: FeatureTable | None = None,
        stats: AugmentStatsProvider | None = None,
        config: ScoringConfig | None = None,
    ) -> None:
        self.features = features or FeatureTable.empty()
        self.stats = stats or NullProvider()
        self.config = config or ScoringConfig.default()

    def rescore(self, scenario: Scenario, config: ScoringConfig) -> list[str]:
        """Cham diem lai MOT scenario voi mot bo trong so, tra ve thu tu moi."""
        advisor = AugmentAdvisor(self.features, self.stats, config)
        candidates = scenario.ranking or list(scenario.component_scores)
        return advisor.rank(candidates, scenario.game_state).order

    def run(self, scenarios: Iterable[Scenario]) -> AblationReport:
        data = [s for s in scenarios if s.ranking]
        report = AblationReport(n_scenarios=len(data))
        if not data:
            return report

        baseline = {id(s): self.rescore(s, self.config) for s in data}

        configs: list[tuple[str, str | None, ScoringConfig]] = [
            ("Full model", None, self.config)
        ]
        for component in ScoringConfig.COMPONENTS:
            configs.append(
                (f"bo {component}", component, self.config.with_ablation(component))
            )
        # Dong quan trong nhat, de cuoi de no nam ngay tren phan ket luan.
        configs.append(("chi w1 (stats tinh)", "all_but_base", self.config.only("base")))

        for label, disabled, config in configs:
            report.rows.append(self._evaluate(label, disabled, config, data, baseline))
        return report

    def _evaluate(
        self,
        label: str,
        disabled: str | None,
        config: ScoringConfig,
        data: list[Scenario],
        baseline: dict[int, list[str]],
    ) -> AblationRow:
        changed = 0
        shifts: list[float] = []
        taus: list[float] = []
        pick_ranks: list[float] = []
        placements: list[float] = []

        for scenario in data:
            before = baseline[id(scenario)]
            after = self.rescore(scenario, config)
            if before and after and before[0] != after[0]:
                changed += 1
            taus.append(kendall_tau(before, after))

            for api in before:
                if api in after:
                    shifts.append(abs(before.index(api) - after.index(api)))

            if scenario.player_pick in after and scenario.final_placement:
                pick_ranks.append(after.index(scenario.player_pick) + 1)
                placements.append(float(scenario.final_placement))

        return AblationRow(
            label=label,
            disabled=disabled,
            top1_change_rate=changed / len(data),
            mean_rank_shift=sum(shifts) / len(shifts) if shifts else 0.0,
            kendall_tau=sum(taus) / len(taus) if taus else 1.0,
            rho_vs_placement=(
                spearman(pick_ranks, placements) if len(pick_ranks) >= 2 else None
            ),
            n=len(data),
        )
