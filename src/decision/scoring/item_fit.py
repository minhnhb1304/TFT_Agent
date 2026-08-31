"""Thanh phan w4 - ItemFit: component duoc tang vs item dang thieu (SPEC 3.5.4).

Hai tin hieu nhan nhau:

    1. Augment tang thu gi (component cu the / component bat ky / item hoan chinh).
    2. Board dang doi kem den dau - va DAC BIET la co component nao dang le loi
       cho du mot cai nua de ghep thanh item hay khong.

Y thu hai la thu mot bang stats tinh khong bao gio noi duoc: gia tri cua "mot
Kiem" phu thuoc vao viec ban da co san mot Kiem hay chua.
"""

from __future__ import annotations

from collections import Counter

from ...game_state.models import GameState
from ...knowledge.augment_features import AugmentFeature
from .types import ComponentScore, ScoringConfig, clamp01, neutral

NAME = "item_fit"

GENERIC_GRANTS = {"AnyComponent", "Anvil", "Emblem"}
COMPLETED_GRANTS = {"CompletedItem"}

# Bao nhieu component roi thi coi la "du do" - dung de chuan hoa muc doi kem.
RICH_THRESHOLD = 6.0


class ItemFitScorer:
    """Cham diem augment tang trang bi theo tinh trang item hien tai."""

    def __init__(self, config: ScoringConfig) -> None:
        tune = config.tune(NAME)
        self.exact = float(tune.get("exact_component", 1.0))
        self.generic = float(tune.get("generic_component", 0.6))
        self.completed = float(tune.get("completed_item", 0.8))

    def starvation(self, state: GameState) -> float:
        """Muc doi kem trang bi: 1.0 khi trang tay, 0.0 khi da du do.

        Item da ghep tinh bang 2 component vi no dung 2 component that.
        """
        owned = len(state.item_components) + 2 * len(state.completed_items)
        return clamp01((RICH_THRESHOLD - owned) / RICH_THRESHOLD)

    def __call__(
        self, api_name: str, feature: AugmentFeature | None, state: GameState
    ) -> ComponentScore:
        if feature is None:
            return neutral(NAME, "Không có dữ liệu đặc trưng cho augment này")
        if not feature.item_grants:
            return neutral(NAME, "Không tặng trang bị — không tính điểm trang bị")

        held = Counter(state.item_components)
        best_value = 0.0
        best_reason = ""

        for grant in feature.item_grants:
            if grant in COMPLETED_GRANTS:
                value, reason = self.completed, "Tặng item hoàn chỉnh"
            elif grant in GENERIC_GRANTS:
                value, reason = self.generic, f"Tặng trang bị dạng {grant}"
            elif held.get(grant, 0) % 2 == 1:
                # Dang le loi mot cai - them cai nua la ghep duoc ngay.
                value = self.exact
                reason = f"Tặng {grant} — đang lẻ đúng 1 cái, ghép được ngay"
            else:
                value = self.exact * 0.75
                reason = f"Tặng {grant} — component cụ thể, dùng được"

            if value > best_value:
                best_value, best_reason = value, reason

        starve = self.starvation(state)
        # He so 0.4 la san: tang trang bi thi khong bao gio la xau, ke ca khi
        # da du do. Phan con lai (0.6) moi phu thuoc muc doi kem.
        score = clamp01(0.5 + 0.5 * best_value * (0.4 + 0.6 * starve))

        context = (
            f"đang có {len(state.item_components)} mảnh + "
            f"{len(state.completed_items)} item hoàn chỉnh"
        )
        return ComponentScore(
            NAME,
            score,
            f"{best_reason} ({context})",
            {
                "grants": feature.item_grants,
                "starvation": round(starve, 3),
                "components_held": dict(held),
            },
        )
