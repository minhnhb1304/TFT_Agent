"""Test cac advisor phu + dieu phoi vien (SPEC 3.5.1, 3.5.2, 3.5.3, Phase 5 + 7).

Trong tam cua file nay khong phai "ham chay dung khong" ma la ba bat bien de
vo trong luc phat trien:

    1. Thieu du lieu -> ha cap chuc nang, KHONG crash va KHONG bia.
    2. LLM khong bao gio doi duoc thu hang.
    3. Scouting tat -> contest_score bang 0 va noi ro la dang tat.
"""

from __future__ import annotations

import pytest

from src.decision.advisor import Advisor
from src.decision.augment_advisor import AugmentAdvisor, Ranking
from src.decision.comp_selector import CompSelector
from src.decision.contest_analyzer import analyze as analyze_contest
from src.decision.item_advisor import ItemAdvisor, ItemRecipes, Recipe, build_recipes_from_locale
from src.decision.llm_reasoner import LlmReasoner, RankingMutationError, assert_order_preserved
from src.decision.position_advisor import PositionAdvisor
from src.decision.rules_engine import EconomyRules, interest_income, projected_income, streak_income
from src.eval.scenario_logger import ScenarioLogger
from src.game_state.models import Champion, GameState, OpponentBoard
from src.knowledge.augment_features import AugmentFeature, FeatureTable
from src.knowledge.comp_database import CompDatabase, MetaComp
from src.knowledge.roll_odds import UnverifiedDataError, get_odds, pool_size
from src.utils.settings import Settings


def comp(name: str, **kwargs) -> MetaComp:
    base = dict(name=name, core_units=["A", "B", "C", "D"], core_items=["I1", "I2"])
    base.update(kwargs)
    return MetaComp(**base)


# --- Economy (SPEC 3.5.1) --------------------------------------------------


def test_interest_caps_at_five() -> None:
    assert interest_income(0) == 0
    assert interest_income(35) == 3
    assert interest_income(50) == 5
    assert interest_income(120) == 5, "lai phai chan tren o 5"


def test_streak_bonus_ignores_direction() -> None:
    """Chuoi thang va chuoi thua deu cho gold - dau cua streak khong quan trong."""
    assert streak_income(3) == streak_income(-3) == 2
    assert streak_income(1) == 0
    assert streak_income(9) == 3


def test_projected_income_adds_up() -> None:
    state = GameState(gold=50, streak=4)
    assert projected_income(state) == 5 + 5 + 3


def test_low_hp_overrides_econ_advice() -> None:
    """HP thap thi giu vang khong con la loi khuyen dung."""
    advice = EconomyRules().evaluate(GameState(gold=20, hp=25, stage="4-3"))
    top = advice[0]
    assert top.topic == "tempo"
    assert "vòng này" in top.message


def test_healthy_early_game_advises_saving() -> None:
    advice = EconomyRules().evaluate(GameState(gold=20, hp=90, stage="2-3"))
    assert any(a.topic == "econ" and "Giữ vàng" in a.message for a in advice)


def test_every_advice_carries_confidence_label() -> None:
    """Moc quy uoc va so do duoc phai phan biet duoc tren giao dien."""
    for a in EconomyRules().evaluate(GameState()):
        assert a.confidence in ("đo được", "quy uoc nhieu set")


# --- Roll odds bi gate -----------------------------------------------------


def test_roll_odds_refuse_to_answer_by_default() -> None:
    """Chua verify cho 18.1 -> khong duoc tra so mot cach im lang."""
    with pytest.raises(UnverifiedDataError):
        get_odds(7)


def test_roll_odds_are_labelled_unverified_when_forced() -> None:
    odds = get_odds(7, allow_unverified=True)
    assert odds.verified is False
    assert odds.chance_of(4) == pytest.approx(0.15)


def test_pool_size_returns_the_variant_it_used() -> None:
    """Hai nguon mau thuan nhau - bao cao phai noi ro dang trich cai nao."""
    size_a, name_a = pool_size(3, "community_reported")
    size_b, name_b = pool_size(3, "pbe_character_wizard_default")
    assert (size_a, size_b) == (16, 18)
    assert name_a != name_b


# --- Comp selector (SPEC 3.5.2) --------------------------------------------


def test_empty_comp_database_degrades_without_crashing() -> None:
    advice = CompSelector(CompDatabase()).select(GameState())
    assert advice.top == []
    assert "Chưa có dữ liệu" in advice.note


def test_comp_score_rises_with_units_owned() -> None:
    selector = CompSelector(CompDatabase([comp("X")]))
    empty = selector.select(GameState()).best.total
    partial = selector.select(
        GameState(board=[Champion(name="A", cost=1), Champion(name="B", cost=1)])
    ).best.total
    assert partial > empty


def test_missing_units_drive_the_transition_guide() -> None:
    selector = CompSelector(CompDatabase([comp("X")]))
    best = selector.select(GameState(board=[Champion(name="A", cost=1)])).best
    assert set(best.missing_units) == {"B", "C", "D"}
    assert "Cần thêm" in best.transition_guide()


def test_direction_stability_rewards_staying() -> None:
    """Tranh pivot vo co: cung mot board, comp cu duoc cong diem."""
    strong = comp("X", top4_rate=0.7, sample_n=1000)
    board = [Champion(name=n, cost=1) for n in ("A", "B", "C", "D")]
    selector = CompSelector(CompDatabase([strong]))
    fresh = selector.select(GameState(board=board)).best.total
    sticky = selector.select(GameState(board=board), previous="X").best.total
    assert sticky > fresh


def test_pivot_penalty_applies_when_selling_many_units() -> None:
    selector = CompSelector(CompDatabase([comp("X")]))
    junk = [Champion(name=f"J{i}", cost=1) for i in range(5)]
    without = selector.select(GameState(board=junk)).best.total
    with_pivot = selector.select(GameState(board=junk), previous="Y").best.total
    assert with_pivot < without


def test_meta_score_ignores_tiny_samples() -> None:
    """Comp khong co co mau khong duoc phep vuot len nho ti le dep."""
    selector = CompSelector(CompDatabase())
    trusted = selector.meta_score(comp("A", top4_rate=0.70, sample_n=1000))
    unproven = selector.meta_score(comp("B", top4_rate=0.70, sample_n=3))
    assert trusted > unproven


# --- Contest / scouting (Phase 7) ------------------------------------------


def test_contest_is_zero_and_says_so_when_scouting_disabled() -> None:
    state = GameState(opponents=[OpponentBoard(slot=1, units=["A", "B"], confidence=1.0)])
    result = analyze_contest(comp("X"), state, enabled=False)
    assert result.score == 0.0
    assert "tắt" in result.reason


def test_contest_counts_opponents_sharing_core_units() -> None:
    state = GameState(opponents=[
        OpponentBoard(slot=1, units=["A", "B", "Z"], confidence=0.9),
        OpponentBoard(slot=2, units=["A", "Q"], confidence=0.9),      # 1 unit - chua tinh
        OpponentBoard(slot=3, units=["C", "D"], confidence=0.9),
    ])
    result = analyze_contest(comp("X"), state, enabled=True)
    assert result.contesting == [1, 3]
    assert result.score == pytest.approx(-2 / 7)


def test_contest_ignores_low_confidence_boards() -> None:
    """Doc nham board doi thu roi khuyen doi huong la sai lam dat nhat."""
    state = GameState(opponents=[OpponentBoard(slot=1, units=["A", "B"], confidence=0.2)])
    result = analyze_contest(comp("X"), state, enabled=True)
    assert result.contesting == []
    assert result.confidence == 0.0


def test_contested_comp_scores_lower_than_uncontested() -> None:
    contested = GameState(
        board=[Champion(name="A", cost=1)],
        opponents=[OpponentBoard(slot=i, units=["A", "B"], confidence=0.9) for i in (1, 2)],
    )
    clean = GameState(board=[Champion(name="A", cost=1)])
    selector = CompSelector(CompDatabase([comp("X")]), enable_scouting=True)
    assert selector.select(contested).best.total < selector.select(clean).best.total


def test_scouting_off_makes_opponents_irrelevant() -> None:
    """Moi code doc state.opponents phai chiu duoc list rong VA co bi tat."""
    state = GameState(
        board=[Champion(name="A", cost=1)],
        opponents=[OpponentBoard(slot=1, units=["A", "B"], confidence=1.0)],
    )
    off = CompSelector(CompDatabase([comp("X")]), enable_scouting=False)
    assert off.select(state).best.total == CompSelector(
        CompDatabase([comp("X")])
    ).select(GameState(board=[Champion(name="A", cost=1)])).best.total


# --- Item advisor ----------------------------------------------------------


def test_item_advisor_without_recipes_still_reports_odd_components() -> None:
    advice = ItemAdvisor().recommend(GameState(item_components=["BFSword", "ChainVest", "BFSword", "Rod"]))
    assert advice.buildable == []
    # BFSword co 2 cai (chan) nen khong le; ChainVest va Rod moi thu 1 cai.
    assert advice.surplus == ["ChainVest", "Rod"]
    assert "Chưa có bảng công thức" in advice.note


def test_item_advisor_lists_buildable_and_one_away() -> None:
    recipes = ItemRecipes(
        [Recipe("Deathblade", ("BFSword", "BFSword")), Recipe("Bloodthirster", ("BFSword", "Cloak"))],
        source="test",
    )
    advice = ItemAdvisor(recipes).recommend(GameState(item_components=["BFSword", "BFSword"]))
    assert advice.buildable == ["Deathblade"]
    assert ("Bloodthirster", "Cloak") in advice.one_away


def test_recipes_are_generated_from_locale_not_hardcoded() -> None:
    """SPEC 5: bang tra cuu la san pham SINH RA, khong phai hang so trong code."""
    locale = {"items": [
        {"apiName": "TFT_Item_X", "composition": ["BFSword", "ChainVest"]},
        {"apiName": "DA_Aug", "composition": ["BFSword", "BFSword"], "isAugment": True},
        {"apiName": "TFT_Component", "composition": []},
    ]}
    recipes = build_recipes_from_locale(locale)
    assert len(recipes) == 1
    assert recipes.recipes[0].item == "TFT_Item_X"


# --- Position advisor ------------------------------------------------------


def test_carry_on_front_row_is_the_top_issue() -> None:
    state = GameState(board=[
        Champion(name="Carry", cost=4, items=["BFSword", "RecurveBow"], position=(0, 3)),
    ])
    issues = PositionAdvisor().evaluate(state).issues
    assert issues[0].severity == 1
    assert "hàng đầu" in issues[0].issue


def test_tank_on_back_row_is_flagged() -> None:
    state = GameState(board=[Champion(name="Tank", cost=2, items=["ChainVest"], position=(3, 3))])
    assert any("đỡ đòn" in i.issue for i in PositionAdvisor().evaluate(state).issues)


def test_position_advisor_admits_it_ignores_opponents() -> None:
    """Pham vi hep phai duoc noi ra, khong de nguoi doc tu suy dien."""
    state = GameState(board=[Champion(name="X", cost=1, position=(1, 1))])
    assert "Phase 7" in PositionAdvisor().evaluate(state).note


def test_empty_board_is_not_an_error() -> None:
    assert PositionAdvisor().evaluate(GameState()).issues == []


# --- LLM reasoner (SPEC 3.5.3) ---------------------------------------------


def _ranking() -> Ranking:
    table = FeatureTable({
        "A": AugmentFeature(api_name="A", name="A", econ_value=3),
        "B": AugmentFeature(api_name="B", name="B"),
    })
    return AugmentAdvisor(table).rank(["A", "B"], GameState(stage="2-1"))


def test_llm_disabled_returns_ranking_untouched() -> None:
    ranking = _ranking()
    before = list(ranking.order)
    after = LlmReasoner(enabled=False).refine(ranking, GameState())
    assert after.order == before
    assert all(e.refined_reason is None for e in after.entries)


def test_llm_refinement_only_rewrites_text() -> None:
    ranking = _ranking()
    before = list(ranking.order)
    reasoner = LlmReasoner(
        enabled=True,
        call=lambda prompt: '{"A": "Câu văn mượt hơn", "B": "Câu khác"}',
    )
    after = reasoner.refine(ranking, GameState())
    assert after.order == before, "LLM khong duoc phep doi thu hang"
    assert after.entries[0].refined_reason == "Câu văn mượt hơn"


def test_llm_timeout_falls_back_to_original() -> None:
    """Het hard timeout -> tra nguyen ket qua da tinh, khong doi."""
    import time

    def slow(prompt: str) -> str:
        time.sleep(0.5)
        return "{}"

    ranking = _ranking()
    before = list(ranking.order)
    after = LlmReasoner(enabled=True, timeout_s=0.05, call=slow).refine(ranking, GameState())
    assert after.order == before
    assert all(e.refined_reason is None for e in after.entries)


def test_llm_error_is_swallowed_not_propagated() -> None:
    def boom(prompt: str) -> str:
        raise RuntimeError("mang hong")

    ranking = _ranking()
    assert LlmReasoner(enabled=True, call=boom).refine(ranking, GameState()).order == ranking.order


def test_malformed_llm_output_is_ignored() -> None:
    ranking = _ranking()
    after = LlmReasoner(enabled=True, call=lambda p: "khong phai JSON").refine(ranking, GameState())
    assert all(e.refined_reason is None for e in after.entries)


def test_order_invariant_is_enforced_not_just_documented() -> None:
    """Bat bien kien truc phai la mot phep kiem tra chay duoc."""
    ranking = _ranking()
    with pytest.raises(RankingMutationError):
        assert_order_preserved(["Z", "Y"], ranking)


# --- Advisor (dieu phoi) ---------------------------------------------------


@pytest.fixture
def advisor(tmp_path) -> Advisor:
    settings = Settings.load("config/settings.yaml")
    features = FeatureTable({
        "A": AugmentFeature(api_name="A", name="A", econ_value=3, category="econ"),
        "B": AugmentFeature(api_name="B", name="B", tempo="scaling"),
    })
    return Advisor(
        settings=settings,
        features=features,
        comps=CompDatabase([comp("X")]),
        recipes=ItemRecipes(),
        logger=ScenarioLogger(tmp_path / "scenarios"),
    )


def test_advisor_runs_every_sub_advisor(advisor) -> None:
    bundle = advisor.advise(GameState(stage="3-2", hp=60, gold=40), choices=["A", "B"])
    assert bundle.ranking is not None
    assert bundle.comp is not None
    assert bundle.economy and bundle.items and bundle.position is not None
    assert bundle.degraded == []


def test_advisor_logs_only_augment_decisions(advisor) -> None:
    """Khong phai man chon augment thi khong sinh ban ghi - dataset phai sach."""
    assert advisor.advise(GameState()).scenario_path is None
    assert advisor.advise(GameState(), choices=["A"]).scenario_path is not None


def test_a_broken_sub_advisor_does_not_break_augment_advice(advisor) -> None:
    """Duong co han gio phai song sot khi mot advisor phu hong."""
    class Broken:
        def select(self, *args, **kwargs):
            raise RuntimeError("hong that")

    advisor.comp_selector = Broken()
    bundle = advisor.advise(GameState(stage="2-1"), choices=["A", "B"])
    assert bundle.ranking is not None
    assert any("comp" in d for d in bundle.degraded)


def test_advisor_output_is_json_serializable(advisor) -> None:
    """Overlay va ScenarioLogger deu an dau ra nay - no phai serialize duoc."""
    import json

    bundle = advisor.advise(GameState(stage="4-1", hp=40), choices=["A", "B"])
    assert json.loads(json.dumps(bundle.to_dict(), ensure_ascii=False))["augment"]
