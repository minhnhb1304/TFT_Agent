"""Advisor - dieu phoi vien: gop moi tu van roi day sang Overlay VA Logger.

Day la cho duy nhat cac module quyet dinh gap nhau, va la cho duy nhat doc
config/settings.yaml. Moi advisor con nhan phu thuoc qua constructor - nho the
chung test duoc doc lap va khong cai nao co the tu bat mot co ma cai khac
khong biet.

THU TU LA CO Y: augment truoc, phan con lai sau. Man chon augment co dong ho
dem nguoc ~30 giay; cac tu van khac thi khong. Neu mot advisor phu bi cham hay
loi, no khong duoc phep keo augment advisor theo - vi the moi advisor phu deu
duoc goi trong khoi try rieng va that bai thi bi bo qua co ghi nhan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from ..eval.scenario_logger import ScenarioLogger
from ..game_state.models import GameState
from ..knowledge.augment_features import FeatureTable
from ..knowledge.comp_database import CompDatabase
from ..knowledge.stats_provider import AugmentStatsProvider, default_provider
from ..utils.settings import Settings
from .augment_advisor import AugmentAdvisor, AugmentChoice, Ranking
from .comp_selector import CompAdvice, CompSelector
from .item_advisor import ItemAdvice, ItemAdvisor, ItemRecipes
from .llm_reasoner import LlmReasoner
from .position_advisor import PositionAdvice, PositionAdvisor
from .rules_engine import Advice, EconomyRules
from .scoring.types import ScoringConfig


@dataclass
class AdviceBundle:
    """Toan bo dau ra cua mot chu ky tu van."""

    ranking: Ranking | None = None
    comp: CompAdvice | None = None
    economy: list[Advice] = field(default_factory=list)
    items: ItemAdvice | None = None
    position: PositionAdvice | None = None
    degraded: list[str] = field(default_factory=list)
    scenario_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        from .comp_selector import as_dict as comp_as_dict

        return {
            "augment": self.ranking.to_dict() if self.ranking else None,
            "comp": comp_as_dict(self.comp) if self.comp else None,
            "economy": [a.to_dict() for a in self.economy],
            "items": self.items.to_dict() if self.items else None,
            "position": self.position.to_dict() if self.position else None,
            "degraded": self.degraded,
            "scenario_path": self.scenario_path,
        }


class Advisor:
    """Dieu phoi cac advisor con theo mot cau hinh."""

    def __init__(
        self,
        settings: Settings | None = None,
        features: FeatureTable | None = None,
        stats: AugmentStatsProvider | None = None,
        comps: CompDatabase | None = None,
        recipes: ItemRecipes | None = None,
        logger: ScenarioLogger | None = None,
    ) -> None:
        self.settings = settings or Settings.load()
        s = self.settings

        weights_path = s.path("scoring_weights")
        config = (
            ScoringConfig.load(weights_path)
            if weights_path.exists()
            else ScoringConfig.default()
        )

        feature_path = s.path("augment_features")
        self.features = features or (
            FeatureTable.load(feature_path) if feature_path.exists() else FeatureTable.empty()
        )
        self.stats = stats or default_provider(
            s.path("augment_stats_csv"), s.path("augment_tiers")
        )
        self.augment_advisor = AugmentAdvisor(self.features, self.stats, config)

        self.comp_selector = CompSelector(
            comps or CompDatabase.load(s.path("meta_comps")),
            config,
            enable_scouting=s.enable_scouting,
        )
        self.item_advisor = ItemAdvisor(recipes or ItemRecipes.load(s.path("item_recipes")))
        self.position_advisor = PositionAdvisor()
        self.economy = EconomyRules()
        self.reasoner = LlmReasoner(
            enabled=s.enable_llm_refinement,
            model=str(s.get("features", "llm_model", "gemini-3.5-flash-lite")),
            timeout_s=float(s.get("features", "llm_hard_timeout_s", 2.0)),
        )
        self.logger = logger or ScenarioLogger(s.path("scenarios"), enabled=s.log_scenarios)

        self._previous_comp: str | None = None

    def advise(
        self,
        state: GameState,
        choices: Sequence[AugmentChoice | str] | None = None,
        frame_ref: str | None = None,
    ) -> AdviceBundle:
        """Chay mot chu ky tu van day du.

        Args:
            choices: cac augment dang duoc chao. None nghia la khong phai man
                chon augment - bo qua augment advisor, van tu van phan con lai.
        """
        bundle = AdviceBundle()

        # 1. Augment - duong co han gio, chay truoc va khong bao boc try/except:
        #    that bai o day la that bai cua chinh do an, phai no ra chu khong nuot.
        if choices:
            bundle.ranking = self.augment_advisor.rank(choices, state)
            bundle.ranking = self.reasoner.refine(bundle.ranking, state)

        # 2. Cac advisor phu - moi cai duoc phep hong rieng.
        bundle.comp = self._safe(bundle, "comp", lambda: self.comp_selector.select(state, self._previous_comp))
        if bundle.comp and bundle.comp.best:
            self._previous_comp = bundle.comp.best.name

        bundle.economy = self._safe(bundle, "economy", lambda: self.economy.evaluate(state)) or []
        bundle.items = self._safe(bundle, "items", lambda: self.item_advisor.recommend(state))
        bundle.position = self._safe(bundle, "position", lambda: self.position_advisor.evaluate(state))

        # 3. Log - chi khi that su co mot quyet dinh augment de ghi.
        if bundle.ranking is not None:
            path = self.logger.log(bundle.ranking, state, frame_ref=frame_ref)
            bundle.scenario_path = str(path) if path else None

        return bundle

    @staticmethod
    def _safe(bundle: AdviceBundle, name: str, fn):
        """Chay mot advisor phu, ghi nhan neu no hong thay vi keo ca he thong."""
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - co y bat rong o ranh gioi module
            bundle.degraded.append(f"{name}: {type(exc).__name__}: {exc}")
            return None
