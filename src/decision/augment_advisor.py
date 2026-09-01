"""Augment Advisor - lo thuat toan cua do an (SPEC 3.5.4).

    Score(a | S) = w1*Base + w2*BoardFit + w3*EconFit + w4*ItemFit + w5*TempoFit

Ba rang buoc kien truc, khong duoc pha:

1. KHONG CO LLM TREN DUONG QUYET DINH. Man chon augment chi keo dai khoang
   30 giay. Toan bo diem so o day la so hoc dong tren du lieu da cache, tra
   loi tuc thi. LLM (neu bat) chi den sau, va chi duoc sua CAU CHU.

2. MOI THANH PHAN PHAI TRA VE LY DO. Xep hang khong kem ly do la hop den;
   hop den thi khong tu van duoc cho ai, va cung khong ablation duoc.

3. KHONG BAO GIO DOAN CAP MAP MO. Bon cap augment trung ca ten lan icon
   (research/vision-stack/augments.md). Gap chung thi cham diem CA HAI va
   gan nhan - vi day la gioi han cua du lieu, va giau no di thi bao cao do
   an mat trung thuc.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from ..game_state.models import GameState
from ..knowledge.augment_catalog import MatchResult
from ..knowledge.augment_features import AugmentFeature, FeatureTable
from ..knowledge.stats_provider import AugmentStatsProvider, NullProvider
from .scoring import (
    BaseScorer,
    BoardFitScorer,
    ComponentScore,
    EconFitScorer,
    ItemFitScorer,
    ScoringConfig,
    TempoFitScorer,
)


@dataclass
class AugmentChoice:
    """Mot o augment tren man hinh chon.

    `api_names` co the co NHIEU phan tu: do la mot cap map mo ma nhan dang
    khong tach duoc. Khong phai loi - la gioi han du lieu, va advisor phai
    hien thi ca hai.
    """

    api_names: list[str]
    confidence: float = 1.0
    display_name: str = ""

    @property
    def ambiguous(self) -> bool:
        return len(self.api_names) > 1

    @classmethod
    def from_match(cls, match: MatchResult, confidence: float = 1.0) -> "AugmentChoice":
        """Doi ket qua khop ten cua AugmentCatalog thanh mot o lua chon."""
        return cls(
            api_names=[a.api_name for a in match.candidates],
            confidence=confidence,
            display_name=match.candidates[0].name if match.candidates else "",
        )


@dataclass
class ScoredAugment:
    """Mot augment da cham diem, kem diem tung thanh phan va ly do."""

    api_name: str
    name: str
    total: float
    components: dict[str, ComponentScore]
    ambiguous: bool = False
    choice_index: int = 0
    confidence: float = 1.0
    # Cau giai thich do LLM viet lai (vai tro B, SPEC 3.5.3). Chi la CAU CHU:
    # no khong bao gio duoc phep dong den `total` hay thu tu xep hang.
    refined_reason: str | None = None

    @property
    def reasons(self) -> list[str]:
        """Ly do cua cac thanh phan CO TIN HIEU, xep theo dong gop giam dan.

        Bo qua thanh phan trung tinh: "khong co tin hieu" khong phai ly do de
        chon hay khong chon, hien ra chi lam loang cai dang thuc su chi phoi.
        """
        informative = [c for c in self.components.values() if not c.is_neutral and c.reason]
        informative.sort(key=lambda c: abs(c.score - 0.5), reverse=True)
        out = [c.reason for c in informative]
        return [self.refined_reason] + out if self.refined_reason else out

    def to_dict(self) -> dict[str, Any]:
        return {
            "api_name": self.api_name,
            "name": self.name,
            "total": round(self.total, 4),
            "ambiguous": self.ambiguous,
            "confidence": self.confidence,
            "components": {
                k: {"score": round(v.score, 4), "reason": v.reason, "detail": v.detail}
                for k, v in self.components.items()
            },
        }


@dataclass
class Ranking:
    """Ket qua xep hang cho mot man chon augment."""

    entries: list[ScoredAugment] = field(default_factory=list)
    weights: dict[str, float] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)

    @property
    def top(self) -> ScoredAugment | None:
        return self.entries[0] if self.entries else None

    @property
    def order(self) -> list[str]:
        """Thu tu apiName - thu ma llm_reasoner KHONG duoc phep thay doi."""
        return [e.api_name for e in self.entries]

    def component_scores(self) -> dict[str, dict[str, float]]:
        """Bang diem thanh phan cho ScenarioLogger (SPEC 12.0)."""
        return {
            e.api_name: {k: round(v.score, 4) for k, v in e.components.items()}
            for e in self.entries
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "weights": self.weights,
            "ranking": [e.to_dict() for e in self.entries],
        }


class AugmentAdvisor:
    """Tong hop 5 thanh phan thanh mot xep hang co giai thich."""

    def __init__(
        self,
        features: FeatureTable | None = None,
        stats: AugmentStatsProvider | None = None,
        config: ScoringConfig | None = None,
    ) -> None:
        self.features = features or FeatureTable.empty()
        self.stats = stats or NullProvider()
        self.config = config or ScoringConfig.default()

        self.scorers = {
            "base": BaseScorer(self.stats, self.config),
            "board_fit": BoardFitScorer(self.config),
            "econ_fit": EconFitScorer(self.config),
            "item_fit": ItemFitScorer(self.config),
            "tempo_fit": TempoFitScorer(self.config),
        }

    # -- cham diem ---------------------------------------------------------

    def score_one(self, api_name: str, state: GameState) -> tuple[float, dict[str, ComponentScore]]:
        """Cham diem MOT augment. Tra ve (tong co trong so, diem tung thanh phan)."""
        feature: AugmentFeature | None = self.features.get(api_name)
        components = {
            name: scorer(api_name, feature, state) for name, scorer in self.scorers.items()
        }
        total = sum(
            self.config.weight(name) * comp.score for name, comp in components.items()
        )
        return total, components

    def rank(
        self, choices: Sequence[AugmentChoice | MatchResult | str], state: GameState
    ) -> Ranking:
        """Xep hang cac lua chon tren man chon augment.

        Nhan ca ba dang dau vao vi ba tang goi no khac nhau: reader tra ve
        MatchResult, test viet thang apiName, orchestrator dung AugmentChoice.
        """
        normalized = [_as_choice(c) for c in choices]
        entries: list[ScoredAugment] = []

        for idx, choice in enumerate(normalized):
            for api_name in choice.api_names:
                total, components = self.score_one(api_name, state)
                feature = self.features.get(api_name)
                entries.append(
                    ScoredAugment(
                        api_name=api_name,
                        name=(feature.name if feature else choice.display_name) or api_name,
                        total=total,
                        components=components,
                        ambiguous=choice.ambiguous,
                        choice_index=idx,
                        confidence=choice.confidence,
                    )
                )

        # Sap xep on dinh: diem giam dan, hoa thi giu thu tu apiName de ket qua
        # tai lap duoc 100% - ablation study can dieu do.
        entries.sort(key=lambda e: (-e.total, e.api_name))
        return Ranking(entries, dict(self.config.weights))

    # -- trinh bay ---------------------------------------------------------

    def explain(self, ranking: Ranking) -> str:
        """Ket xuat dang van ban - dung cho CLI demo va log."""
        lines: list[str] = []
        for i, entry in enumerate(ranking, 1):
            flag = "  [KHÔNG PHÂN BIỆT ĐƯỢC]" if entry.ambiguous else ""
            lines.append(f"{i}. {entry.name}  ({entry.total:.3f}){flag}")
            for reason in entry.reasons:
                lines.append(f"     - {reason}")
        return "\n".join(lines)


def _as_choice(item: AugmentChoice | MatchResult | str) -> AugmentChoice:
    if isinstance(item, AugmentChoice):
        return item
    if isinstance(item, MatchResult):
        return AugmentChoice.from_match(item)
    return AugmentChoice([str(item)])


# --- CLI demo --------------------------------------------------------------


def _demo_state() -> GameState:
    """Mot the co that de doc: HP thap, stage 4-2, board AD, thieu trang bi."""
    from ..game_state.models import Champion

    return GameState(
        gold=32,
        level=7,
        hp=28,
        stage="4-2",
        board=[
            Champion(name="Carry", cost=4, star_level=2, items=["BFSword", "RecurveBow"],
                     position=(3, 3), traits=["Ravager"]),
            Champion(name="Tank", cost=2, star_level=2, items=["ChainVest"],
                     position=(0, 1), traits=["Vanguard"]),
        ],
        item_components=["BFSword"],
        active_traits={"Ravager": 3, "Vanguard": 2},
    )


def _force_utf8_stdout() -> None:
    """Ep stdout/stderr sang UTF-8 neu console dang dung codec hep hon."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    # Console Windows mac dinh la cp1252 -> moi reason string tieng Viet co
    # dau deu lam script chet bang UnicodeEncodeError. Reason string la san
    # pham chinh cua module nay, nen khong in duoc no la hong that.
    _force_utf8_stdout()

    ap = argparse.ArgumentParser(description="Demo Augment Advisor khong can game")
    ap.add_argument("--features", default="data/augment_features.json")
    ap.add_argument("--weights", default="config/scoring_weights.yaml")
    ap.add_argument("--stats-csv", default="data/augment_stats.csv")
    ap.add_argument("--tiers", default="data/augment_tiers.json")
    ap.add_argument("--augments", nargs="*", help="danh sach apiName can xep hang")
    ap.add_argument("--json", action="store_true", help="in JSON thay vi van ban")
    args = ap.parse_args(argv)

    from ..knowledge.stats_provider import default_provider

    features = (
        FeatureTable.load(args.features)
        if Path(args.features).exists()
        else FeatureTable.empty()
    )
    config = (
        ScoringConfig.load(args.weights)
        if Path(args.weights).exists()
        else ScoringConfig.default()
    )
    advisor = AugmentAdvisor(
        features, default_provider(args.stats_csv, args.tiers), config
    )

    state = _demo_state()
    picks = args.augments or _pick_demo_augments(features)
    ranking = advisor.rank(picks, state)

    if args.json:
        print(json.dumps(ranking.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"Tình huống: {state.stage}, HP {state.hp}, {state.gold} vàng, "
              f"tộc/hệ {state.active_traits}")
        print(advisor.explain(ranking))
    return 0


def _pick_demo_augments(features: FeatureTable, n: int = 3) -> list[str]:
    """Chon 3 augment khac loai de demo cho thay cac thanh phan tach nhau ra."""
    wanted = ["econ", "combat", "item"]
    picked: list[str] = []
    for category in wanted:
        for api, feat in sorted(features.features.items()):
            if feat.category == category and api not in picked:
                picked.append(api)
                break
    return picked[:n] or sorted(features.features)[:n]


if __name__ == "__main__":
    raise SystemExit(main())
