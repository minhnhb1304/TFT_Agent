"""Test chon doi hinh theo kieu doi hinh x giai doan (SPEC 3.5.2) - OFFLINE.

Moi test khoa mot quy tac lay tu cach nguoi choi hang cao chot bai:

    1. Fast 8/9 truoc luc xoay bai: board tam KHONG bi phat vi thieu tuong loi.
    2. Reroll: tuong loi la tin hieu that ngay tu dau.
    3. Xoay bai som/muon theo kinh te; tien roll khong tinh; muon nhat 4-5 / 5-1.
    4. Do chi huong bang LOAI (AP/AD); do tank khong chi huong.
    5. An khop trait la dieu kien thuan loi, manh yeu theo thong ke.
    6. Ban ca board khi xoay bai la ke hoach cua fast 8/9, khong phai chi phi.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.decision.comp_selector import (
    COMMIT_LOCK,
    COMMIT_NONE,
    DEFAULT_ADAPTIVE,
    CompSelector,
)
from src.decision.comp_signals import (
    gold_to_level,
    item_profile,
    pivot_readiness,
)
from src.decision.item_advisor import ItemRecipes, Recipe
from src.decision.scoring.types import ScoringConfig
from src.game_state.models import Champion, GameState
from src.knowledge.comp_database import CompDatabase, MetaComp, archetype_from_style

ROOT = Path(__file__).resolve().parent.parent

ROD, BF, TEAR = "DA_Component_NeedlesslyLargeRod", "DA_Component_BFSword", "DA_Component_TearOfTheGoddess"
VEST, CLOAK, GLOVES, SPAT = (
    "DA_Component_ChainVest", "DA_Component_NegatronCloak",
    "DA_Component_SparringGloves", "DA_Component_Spatula",
)
RECIPES = ItemRecipes([
    Recipe("DA_RabadonsDeathcap", (ROD, ROD)),
    Recipe("DA_ArchangelsStaff", (TEAR, ROD)),
    Recipe("DA_Deathblade", (BF, BF)),
    Recipe("DA_InfinityEdge", (BF, GLOVES)),
    Recipe("DA_GargoyleStoneplate", (VEST, CLOAK)),
    Recipe("DA_18_EmblemFae", (SPAT, BF)),
])
COSTS = {"A": 4, "B": 4, "C": 4, "D": 4, "R1": 3, "R2": 3, "R3": 3, "R4": 3}


def fast8(name: str = "F8", **kw) -> MetaComp:
    base = dict(name=name, archetype="fast8", core_units=["A", "B", "C", "D"],
                core_items=["DA_RabadonsDeathcap", "DA_ArchangelsStaff"], traits={"DA_18_Fae": 3})
    base.update(kw)
    return MetaComp(**base)


def reroll(name: str = "RR", **kw) -> MetaComp:
    base = dict(name=name, archetype="reroll", core_units=["R1", "R2", "R3", "R4"],
                core_items=["DA_Deathblade", "DA_InfinityEdge"])
    base.update(kw)
    return MetaComp(**base)


def selector(*comps: MetaComp, **kw) -> CompSelector:
    return CompSelector(CompDatabase(list(comps)), recipes=RECIPES, unit_costs=COSTS, **kw)


def units(*names: str) -> list[Champion]:
    return [Champion(name=n, cost=COSTS.get(n, 1)) for n in names]


# --- 1 + 2: tuong loi co phai tin hieu hay khong -------------------------------


def test_fast8_holding_board_is_not_penalised_for_missing_core_units() -> None:
    """Stage 3 cua fast 8: co 0 hay 2 tuong loi thi diem nhu nhau."""
    sel = selector(fast8())
    none = sel.select(GameState(stage="3-2")).best
    some = sel.select(GameState(stage="3-2", board=units("A", "B"))).best
    assert none.weights["unit"] == 0.0
    assert none.total == pytest.approx(some.total)
    assert "Khi xoay bài tìm" in none.transition_guide()


def test_reroll_core_units_are_a_real_signal_from_the_start() -> None:
    sel = selector(reroll())
    none = sel.select(GameState(stage="2-5")).best.total
    some = sel.select(GameState(stage="2-5", board=units("R1", "R2"))).best.total
    assert some > none


def test_fast8_units_matter_again_after_the_deadline() -> None:
    sel = selector(fast8())
    none = sel.select(GameState(stage="4-5", level=7)).best
    some = sel.select(GameState(stage="4-5", level=7, board=units("A", "B"))).best
    assert none.pivoted is True
    assert none.weights["unit"] == DEFAULT_ADAPTIVE["profiles"]["fast_pivoted"]["unit"]
    assert some.total > none.total


def test_gold_does_not_reorder_comps_before_the_pivot() -> None:
    """Loi da gap tren du lieu that: tung de fast 9 thieu tien vuot len fast 8.

    Hai comp giong het nhau chi khac kieu doi hinh; o 4-2, lv7, 60 vang thi
    fast 9 xa tam voi hon han. Tien chi noi THOI DIEM xoay bai, khong duoc lam
    comp xa tam voi it bi tru vi thieu tuong loi.
    """
    state = GameState(stage="4-2", level=7, gold=60, board=units("X1", "X2"))
    sel = selector(fast8("F8"), fast8("F9", archetype="fast9"))
    scores = {s.name: s for s in sel.select(state).top}
    assert scores["F8"].readiness > scores["F9"].readiness
    assert scores["F8"].total == pytest.approx(scores["F9"].total)


# --- 3: kinh te xoay bai --------------------------------------------------------


def test_gold_to_level_buys_remaining_xp_in_blocks_of_four() -> None:
    economy = DEFAULT_ADAPTIVE["economy"]
    assert gold_to_level(GameState(level=7, xp=0), 8, economy) == 56
    assert gold_to_level(GameState(level=7, xp=10), 8, economy) == 48
    assert gold_to_level(GameState(level=8), 8, economy) == 0


def test_pivot_readiness_follows_gold_but_ignores_roll_money() -> None:
    pivot, economy = DEFAULT_ADAPTIVE["pivot"], DEFAULT_ADAPTIVE["economy"]
    missing = ["A", "B"]  # 8 vang mua tuong + 56 vang len 8 = 64
    rich = pivot_readiness("fast8", GameState(stage="4-2", level=7, gold=64), missing, COSTS, pivot, economy)
    half = pivot_readiness("fast8", GameState(stage="4-2", level=7, gold=32), missing, COSTS, pivot, economy)
    early = pivot_readiness("fast8", GameState(stage="3-5", level=7, gold=90), missing, COSTS, pivot, economy)
    assert rich.value == 1.0
    assert half.value == pytest.approx(0.5)
    assert "chưa tính tiền roll" in half.reason
    assert early.value == 0.0


def test_fast9_deadline_is_5_1_not_4_5() -> None:
    pivot, economy = DEFAULT_ADAPTIVE["pivot"], DEFAULT_ADAPTIVE["economy"]
    at_4_5 = pivot_readiness("fast9", GameState(stage="4-5", level=8, gold=0), [], COSTS, pivot, economy)
    at_5_1 = pivot_readiness("fast9", GameState(stage="5-1", level=8, gold=0), [], COSTS, pivot, economy)
    assert at_4_5.value < 1.0
    assert at_5_1.value == 1.0


def test_already_at_target_level_means_pivoted() -> None:
    pivot, economy = DEFAULT_ADAPTIVE["pivot"], DEFAULT_ADAPTIVE["economy"]
    done = pivot_readiness("fast8", GameState(stage="4-1", level=8), ["A"], COSTS, pivot, economy)
    assert done.value == 1.0


# --- 4: loai do ------------------------------------------------------------------


def test_ap_items_point_to_ap_comp_without_exact_name_match() -> None:
    """Co Mu Phu Thuy + Truong Thien Than ma doi hinh AD can Kiem - van nghieng AP."""
    ap_comp = fast8("AP", core_items=["DA_RabadonsDeathcap"])
    ad_comp = fast8("AD", core_items=["DA_Deathblade", "DA_InfinityEdge"])
    state = GameState(stage="3-2", completed_items=["DA_ArchangelsStaff"], item_components=[ROD])
    advice = selector(ap_comp, ad_comp).select(state)
    assert advice.best.name == "AP"


def test_tank_items_do_not_choose_a_direction() -> None:
    ap_comp = fast8("AP", core_items=["DA_RabadonsDeathcap"])
    ad_comp = fast8("AD", core_items=["DA_Deathblade"])
    state = GameState(stage="3-2", completed_items=["DA_GargoyleStoneplate"], item_components=[VEST])
    sel = selector(ap_comp, ad_comp)
    assert sel.item_type_score(ap_comp, state)[0] == pytest.approx(sel.item_type_score(ad_comp, state)[0])
    assert item_profile(state.completed_items, state.item_components, RECIPES, 0.3).mass == 0.0


# --- 5: an -------------------------------------------------------------------------


def test_emblem_matching_comp_trait_is_a_favourable_signal() -> None:
    comp = fast8()
    stats = {"DA_18_EmblemFae": {"count": 40000, "top4_rate": 0.62}}
    sel = selector(comp, item_stats=stats)
    with_emblem = sel.select(GameState(stage="3-2", completed_items=["DA_18_EmblemFae"])).best
    without = sel.select(GameState(stage="3-2")).best
    assert with_emblem.parts["emblem"] > 0.5
    assert with_emblem.total > without.total


def test_stronger_emblem_by_stats_scores_higher() -> None:
    comp = fast8()
    state = GameState(stage="3-2", completed_items=["DA_18_EmblemFae"])
    weak = selector(comp, item_stats={"DA_18_EmblemFae": {"count": 40000, "top4_rate": 0.45}})
    strong = selector(comp, item_stats={"DA_18_EmblemFae": {"count": 40000, "top4_rate": 0.65}})
    assert strong.emblem_score(comp, state)[0] > weak.emblem_score(comp, state)[0]


def test_emblem_of_unrelated_trait_gives_nothing() -> None:
    comp = fast8(traits={"DA_18_Hunter": 3})
    score, reason = selector(comp).emblem_score(comp, GameState(completed_items=["DA_18_EmblemFae"]))
    assert (score, reason) == (0.0, "")


# --- 6: ban ca board ---------------------------------------------------------------


def test_fast_comp_is_not_penalised_for_selling_the_board() -> None:
    board = units("X1", "X2", "X3", "X4", "X5")
    sel = selector(fast8())
    fresh = sel.select(GameState(stage="4-2", board=board)).best.total
    after_other = sel.select(GameState(stage="4-2", board=board), previous="OTHER").best.total
    assert fresh == pytest.approx(after_other)


def test_reroll_comp_still_pays_for_selling_the_board() -> None:
    board = units("X1", "X2", "X3", "X4", "X5")
    sel = selector(reroll())
    fresh = sel.select(GameState(stage="3-2", board=board)).best.total
    after_other = sel.select(GameState(stage="3-2", board=board), previous="OTHER").best.total
    assert after_other < fresh


# --- che do co dinh + muc chot bai ----------------------------------------------


def test_static_mode_ignores_archetype() -> None:
    cfg = ScoringConfig(tuning={"comp_selector": {"adaptive": False}})
    labelled = CompSelector(CompDatabase([fast8()]), cfg, recipes=RECIPES)
    unlabelled = CompSelector(CompDatabase([fast8(archetype="")]), recipes=RECIPES)
    state = GameState(stage="3-2", board=units("A", "B"))
    assert labelled.select(state).best.total == pytest.approx(unlabelled.select(state).best.total)
    assert labelled.select(state).best.archetype == ""


def test_meta_numbers_alone_never_lock_a_comp() -> None:
    strong = fast8("S", top4_rate=0.7, sample_n=5000)
    weak = fast8("W", top4_rate=0.4, sample_n=5000)
    advice = selector(strong, weak).select(GameState(stage="3-2"))
    assert advice.best.name == "S"
    assert advice.commitment == COMMIT_NONE


def test_no_emblem_and_no_augment_are_not_evidence_against() -> None:
    """Loi da gap tren du lieu that: do AP ro rang ma van bao "chi dua vao meta"."""
    comp = fast8(core_items=["DA_RabadonsDeathcap"])
    state = GameState(stage="3-2", completed_items=["DA_RabadonsDeathcap", "DA_ArchangelsStaff"])
    best = selector(comp).select(state).best
    assert best.evidence >= DEFAULT_ADAPTIVE["commitment"]["min_evidence"]


def test_same_fast_archetype_at_the_top_says_wait_for_the_pivot() -> None:
    state = GameState(stage="3-2", completed_items=["DA_RabadonsDeathcap"])
    advice = selector(fast8("F1"), fast8("F2")).select(state)
    assert advice.commitment == COMMIT_NONE
    assert "khi xoay bài" in advice.commitment_reason


def test_clear_board_signal_locks_the_comp() -> None:
    state = GameState(stage="2-5", board=units("R1", "R2", "R3", "R4"),
                      completed_items=["DA_Deathblade", "DA_InfinityEdge"])
    advice = selector(reroll(), reroll("OTHER", core_units=["Z1", "Z2", "Z3", "Z4"],
                                       core_items=["DA_RabadonsDeathcap"])).select(state)
    assert advice.best.name == "RR"
    assert advice.commitment == COMMIT_LOCK


# --- du lieu that --------------------------------------------------------------------


def test_style_labels_map_to_archetypes() -> None:
    assert archetype_from_style("4-Cost Fast 8") == "fast8"
    assert archetype_from_style("Fast 9") == "fast9"
    assert archetype_from_style("3-Cost Reroll") == "reroll"
    assert archetype_from_style("Lose Streak") == ""


def test_tftacademy_data_carries_expert_archetype_labels() -> None:
    comps = json.loads((ROOT / "data" / "meta_comps.tftacademy.json").read_text(encoding="utf-8"))["comps"]
    labelled = [c for c in comps if c.get("archetype")]
    assert len(labelled) >= 50
    assert {c["archetype"] for c in labelled} == {"reroll", "fast8", "fast9"}


def test_board_cost_share_cannot_tell_reroll_from_fast8() -> None:
    """Khoa ly do KHONG suy kieu doi hinh tu gia tuong: reroll that van nhieu tuong dat tien."""
    costs = json.loads((ROOT / "data" / "champion_costs.json").read_text(encoding="utf-8"))["costs"]
    comps = json.loads((ROOT / "data" / "meta_comps.tftacademy.json").read_text(encoding="utf-8"))["comps"]
    heavy_rerolls = [
        c["name"] for c in comps
        if c.get("archetype") == "reroll"
        and sum(1 for u in c["core_units"] if costs.get(u, 0) >= 4) >= 3
    ]
    assert heavy_rerolls, "neu mat di thi co the xem lai viec suy kieu doi hinh tu gia tuong"

