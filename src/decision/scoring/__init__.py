"""Nam thanh phan cham diem augment (SPEC 3.5.4).

Moi thanh phan la mot callable `(api_name, feature, state) -> ComponentScore`.
Chu ky giong het nhau la co y: augment_advisor duyet chung trong mot vong lap,
va ablation study tat bat tung cai ma khong can biet cai nao lam gi.
"""

from .base import BaseScorer
from .board_fit import BoardFitScorer, infer_carry_type, trait_key
from .econ_fit import EconFitScorer
from .item_fit import ItemFitScorer
from .tempo_fit import TempoFitScorer
from .types import NEUTRAL, ComponentScore, ScoringConfig, clamp01, neutral

__all__ = [
    "BaseScorer",
    "BoardFitScorer",
    "EconFitScorer",
    "ItemFitScorer",
    "TempoFitScorer",
    "ComponentScore",
    "ScoringConfig",
    "NEUTRAL",
    "clamp01",
    "neutral",
    "infer_carry_type",
    "trait_key",
]
