"""Test phần đo ảnh hưởng của trạng thái trận lên xếp hạng (mốc M3).

Buổi test 2026-09-16 cho thấy hệ thống đọc HUD rất chăm nhưng `gold`, `level`,
`streak` **không hề vào điểm** — đọc đúng hay sai thì xếp hạng vẫn y nguyên.
Các test ở đây khoá lại điều ngược lại: trạng thái phải đổi được điểm, và phải
nói ra được là nó đổi vì cái gì.
"""

from __future__ import annotations

import pytest

from src.decision.augment_advisor import AugmentAdvisor
from src.decision.scoring.types import ScoringConfig
from src.decision.state_effect import explain, measure, neutral_state
from src.game_state.models import GameState
from src.knowledge.augment_features import AugmentFeature, FeatureTable

ECON = "DA_Econ"
COMBAT = "DA_Combat"


def features() -> FeatureTable:
    return FeatureTable({
        ECON: AugmentFeature(api_name=ECON, name="Lõi Tiền", tier=2, category="econ",
                             econ_value=3, tempo="scaling"),
        COMBAT: AugmentFeature(api_name=COMBAT, name="Lõi Đánh", tier=2, category="combat",
                               econ_value=0, tempo="immediate"),
    })


def advisor() -> AugmentAdvisor:
    return AugmentAdvisor(features(), config=ScoringConfig.default())


def state(**kwargs) -> GameState:
    base = {"stage": "3-2", "gold": 30, "level": 6, "hp": 70, "streak": 0}
    base.update(kwargs)
    return GameState(**base)


def score(api: str, st: GameState) -> float:
    total, _ = advisor().score_one(api, st)
    return total


# --- tiền và chuỗi vào điểm -------------------------------------------------


def test_gold_at_interest_cap_lowers_an_econ_augment():
    """Đã kịch lãi thì một lõi sinh vàng bớt giá trị — phần lớn giá trị của nó là đẩy tới mốc lãi."""
    assert score(ECON, state(gold=60)) < score(ECON, state(gold=30))


def test_being_poor_raises_an_econ_augment():
    assert score(ECON, state(gold=5)) > score(ECON, state(gold=30))


def test_losing_streak_with_healthy_hp_raises_an_econ_augment():
    assert score(ECON, state(streak=-4, hp=80)) > score(ECON, state(streak=0, hp=80))


def test_losing_streak_at_low_hp_gives_no_econ_bonus():
    """Thua liên tiếp mà sắp chết thì không còn là 'đổi máu lấy vốn' nữa."""
    assert score(ECON, state(streak=-4, hp=20)) == score(ECON, state(streak=0, hp=20))


def test_gold_does_not_move_a_non_econ_augment():
    assert score(COMBAT, state(gold=5)) == score(COMBAT, state(gold=60))


# --- nhịp lên cấp -----------------------------------------------------------


def test_being_behind_on_level_favours_immediate_power():
    assert score(COMBAT, state(level=4)) > score(COMBAT, state(level=6))


def test_being_behind_on_level_penalises_scaling():
    assert score(ECON, state(level=4)) < score(ECON, state(level=6))


def test_being_ahead_on_level_changes_nothing():
    """Nhanh nhịp không phải lý do để tham hơn — chỉ chậm nhịp mới là tín hiệu."""
    assert score(COMBAT, state(level=8)) == score(COMBAT, state(level=6))


# --- đo và giải thích -------------------------------------------------------


def test_neutral_state_keeps_stage_and_traits():
    st = state(gold=60, streak=-4, active_traits={"Vanguard": 2})
    neutral = neutral_state(st)
    assert (neutral.stage, neutral.active_traits) == (st.stage, st.active_traits)
    assert (neutral.gold, neutral.streak, neutral.hp) == (30, 0, 70)


def test_measure_reports_no_change_for_a_neutral_state():
    effect = measure(advisor(), [ECON, COMBAT], state())
    assert not effect.order_changed
    assert all(abs(d) < 1e-9 for d in effect.deltas.values())


def test_measure_detects_a_flipped_ranking():
    """Nghèo + thua dài phải kéo lõi tiền lên trên lõi đánh."""
    effect = measure(advisor(), [ECON, COMBAT], state(gold=5, streak=-4, hp=80))
    assert effect.deltas[ECON] > 0
    assert effect.biggest[0] == ECON


def test_explain_is_silent_when_nothing_moved():
    adv = advisor()
    st = state()
    assert explain(measure(adv, [ECON, COMBAT], st), st, adv.rank([ECON, COMBAT], st)) == ""


def test_explain_names_the_reason_and_the_augment():
    adv = advisor()
    st = state(gold=5, streak=-4, hp=80)
    text = explain(measure(adv, [ECON, COMBAT], st), st, adv.rank([ECON, COMBAT], st))
    assert "Lõi Tiền" in text
    assert "5 vàng" in text and "thua 4" in text


@pytest.mark.parametrize("field,value", [("gold", 60), ("streak", -4), ("level", 4)])
def test_each_state_field_moves_at_least_one_score(field: str, value: int):
    """Từng trường một phải có tác dụng — nếu không, đọc nó từ màn hình là vô nghĩa."""
    st = state(**{field: value})
    moved = any(abs(score(api, st) - score(api, state())) > 1e-9 for api in (ECON, COMBAT))
    assert moved, f"trường {field} không ảnh hưởng gì tới điểm"
