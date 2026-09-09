"""Test 5 thanh phan cham diem + AugmentAdvisor (SPEC 3.5.4).

Cach test o day khac test_augment_catalog.py: o kia moi con so den tu du lieu
that, con o day dau vao la GameState TONG HOP. Ly do la thu can chung minh
cung khac nhau - khong phai "du lieu co dung khong" ma la "thuat toan co phan
ung dung huong khi tinh huong thay doi khong".

Vi the moi test o day deu co dang: giu nguyen augment, DOI MOT bien cua tinh
huong, va assert diem di dung chieu.
"""

from __future__ import annotations

import pytest

from src.decision.augment_advisor import AugmentAdvisor, AugmentChoice
from src.decision.scoring import (
    BaseScorer,
    BoardFitScorer,
    EconFitScorer,
    ItemFitScorer,
    ScoringConfig,
    TempoFitScorer,
    infer_carry_type,
    trait_key,
)
from src.game_state.models import Champion, GameState
from src.knowledge.augment_features import AugmentFeature, FeatureTable
from src.knowledge.stats_provider import (
    AugmentStats,
    CompositeProvider,
    NullProvider,
)


class FakeProvider:
    """Nguon so lieu trong bo nho - test khong duoc cham dia lan mang."""

    name = "fake"

    def __init__(self, rows: dict[str, AugmentStats] | None = None) -> None:
        self.rows = rows or {}

    def get(self, api_name: str) -> AugmentStats | None:
        return self.rows.get(api_name)


@pytest.fixture
def config() -> ScoringConfig:
    return ScoringConfig.default()


def feature(**kwargs) -> AugmentFeature:
    """Dac trung toi thieu, ghi de bang kwargs."""
    base = dict(api_name="DA_Test", name="Test", tier=2)
    base.update(kwargs)
    return AugmentFeature(**base)


# --- Base (w1) -------------------------------------------------------------


def test_base_is_penalized_without_stats(config) -> None:
    """Lõi chưa có data/tier list chính xác bị hạ điểm xuống 0.35 kèm chú thích."""
    scorer = BaseScorer(NullProvider(), config)
    result = scorer("DA_Test", feature(), GameState())
    assert result.score == 0.35
    assert not result.is_neutral
    assert "Chưa có data/tier list chính xác" in result.reason
    assert result.detail["is_unknown"] is True


def test_base_rewards_lower_placement(config) -> None:
    provider = FakeProvider({
        "GOOD": AugmentStats("GOOD", avg_place=3.6, sample_n=1000, source="t"),
        "BAD": AugmentStats("BAD", avg_place=4.9, sample_n=1000, source="t"),
    })
    scorer = BaseScorer(provider, config)
    good = scorer("GOOD", feature(), GameState()).score
    bad = scorer("BAD", feature(), GameState()).score
    assert good > 0.8 > bad


def test_base_shrinks_toward_neutral_on_small_sample(config) -> None:
    """Co mau nho thi khong duoc phep dieu khien xep hang.

    Cung mot avg_place, n=10 phai gan trung tinh hon han n=1000.
    """
    scorer = BaseScorer(
        FakeProvider({
            "BIG": AugmentStats("BIG", avg_place=3.5, sample_n=1000, source="t"),
            "SMALL": AugmentStats("SMALL", avg_place=3.5, sample_n=10, source="t"),
        }),
        config,
    )
    big = scorer("BIG", feature(), GameState()).score
    small = scorer("SMALL", feature(), GameState()).score
    assert big > small > 0.5


def test_base_reason_always_carries_provenance(config) -> None:
    """SPEC 3.4.2: khong co co mau va nguon thi khong phai bang chung."""
    scorer = BaseScorer(
        FakeProvider({"X": AugmentStats("X", avg_place=4.0, sample_n=321, source="opgg")}),
        config,
    )
    reason = scorer("X", feature(), GameState()).reason
    assert "321" in reason and "opgg" in reason


# --- BoardFit (w2) ---------------------------------------------------------


def test_trait_key_normalizes_every_spelling() -> None:
    """Feature table giu apiName, con reader tra ve ten hien thi."""
    keys = {trait_key(x) for x in ["DA_18_Ravager", "DA_Ravager18", "Ravager", "ravager"]}
    assert keys == {"ravager"}


def test_board_fit_rewards_active_trait(config) -> None:
    scorer = BoardFitScorer(config)
    feat = feature(trait_affinity=["DA_18_Ravager"])
    aligned = scorer("A", feat, GameState(active_traits={"Ravager": 3}))
    absent = scorer("A", feat, GameState(active_traits={"Vanguard": 2}))
    assert aligned.score > absent.score
    assert "Ravager" in aligned.reason


def test_board_fit_is_neutral_when_augment_has_no_signal(config) -> None:
    scorer = BoardFitScorer(config)
    result = scorer("A", feature(), GameState())
    assert result.is_neutral


def test_infer_carry_type_reads_items_not_champion_names() -> None:
    """Du lieu CDragon khong noi tuong nao AD hay AP - item thi noi."""
    state = GameState(board=[
        Champion(name="X", cost=4, items=["BFSword", "RecurveBow"], position=(1, 1)),
    ])
    carry_type, evidence = infer_carry_type(state)
    assert carry_type == "AD"
    assert "BFSword" in evidence


def test_infer_carry_type_unknown_without_items() -> None:
    """Board trang tay va khong co role -> unknown, coi la THIEU tin hieu."""
    state = GameState(board=[Champion(name="X", cost=1, position=(1, 1))])
    assert infer_carry_type(state)[0] == "unknown"


def test_infer_carry_type_falls_back_to_champion_role() -> None:
    """Khi board chua co item nhung tuong co role (CDragon role): dung role lam fallback."""
    state = GameState(board=[Champion(name="Ahri", cost=4, role="APCaster", position=(1, 1))])
    carry_type, evidence = infer_carry_type(state)
    assert carry_type == "AP"
    assert "Ahri" in evidence and "APCaster" in evidence


def test_board_fit_penalizes_carry_type_mismatch(config) -> None:
    scorer = BoardFitScorer(config)
    ad_board = GameState(board=[
        Champion(name="X", cost=4, items=["BFSword"], position=(1, 1))
    ])
    match = scorer("A", feature(carry_type="AD"), ad_board)
    mismatch = scorer("A", feature(carry_type="AP"), ad_board)
    assert match.score > mismatch.score


# --- EconFit (w3) ----------------------------------------------------------


def test_econ_fit_falls_with_stage(config) -> None:
    """Cung mot augment econ: som thi tot, muon thi te. Day la ca ly do w3 ton tai."""
    scorer = EconFitScorer(config)
    feat = feature(econ_value=3, category="econ")
    early = scorer("A", feat, GameState(stage="2-1")).score
    mid = scorer("A", feat, GameState(stage="4-1")).score
    late = scorer("A", feat, GameState(stage="6-1")).score
    assert early > mid > late
    assert late < 0.5, "econ o cuoi van phai bi tru diem, khong chi la trung tinh"


def test_econ_fit_neutral_for_non_econ_augment(config) -> None:
    scorer = EconFitScorer(config)
    assert scorer("A", feature(econ_value=0), GameState(stage="5-1")).is_neutral


def test_econ_fit_scales_with_econ_value(config) -> None:
    scorer = EconFitScorer(config)
    state = GameState(stage="2-1")
    weak = scorer("A", feature(econ_value=1), state).score
    strong = scorer("A", feature(econ_value=3), state).score
    assert strong > weak


# --- ItemFit (w4) ----------------------------------------------------------


def test_item_fit_prefers_completing_an_odd_component(config) -> None:
    """Gia tri cua "mot Kiem" phu thuoc vao viec da co san mot Kiem hay chua."""
    scorer = ItemFitScorer(config)
    feat = feature(item_grants=["BFSword"])
    has_one = scorer("A", feat, GameState(item_components=["BFSword"]))
    has_none = scorer("A", feat, GameState(item_components=["ChainVest"]))
    assert has_one.score > has_none.score
    assert "ghép được ngay" in has_one.reason


def test_item_fit_falls_when_board_is_item_rich(config) -> None:
    scorer = ItemFitScorer(config)
    feat = feature(item_grants=["AnyComponent"])
    starved = scorer("A", feat, GameState()).score
    rich = scorer("A", feat, GameState(completed_items=["a", "b", "c"])).score
    assert starved > rich


def test_item_fit_never_below_neutral(config) -> None:
    """Duoc tang trang bi khong bao gio la mot dieu xau - chi la it gia tri hon."""
    scorer = ItemFitScorer(config)
    rich = GameState(completed_items=["a", "b", "c", "d", "e"])
    assert scorer("A", feature(item_grants=["AnyComponent"]), rich).score >= 0.5


def test_item_fit_neutral_when_no_grants(config) -> None:
    scorer = ItemFitScorer(config)
    assert scorer("A", feature(), GameState()).is_neutral


# --- TempoFit (w5) ---------------------------------------------------------


def test_tempo_fit_punishes_scaling_at_low_hp(config) -> None:
    scorer = TempoFitScorer(config)
    feat = feature(tempo="scaling")
    healthy = scorer("A", feat, GameState(hp=90)).score
    dying = scorer("A", feat, GameState(hp=15)).score
    assert healthy > dying
    assert dying < 0.5


def test_tempo_fit_rewards_immediate_at_low_hp(config) -> None:
    scorer = TempoFitScorer(config)
    feat = feature(tempo="immediate")
    assert scorer("A", feat, GameState(hp=15)).score > scorer("A", feat, GameState(hp=90)).score


def test_tempo_penalty_is_asymmetric(config) -> None:
    """Chon scaling luc sap chet la sai lam dat hon chon immediate luc day mau.

    Vi the do lech khoi trung tinh cua scaling-o-HP-thap phai LON hon do lech
    cua immediate-o-HP-cao. Day la mot quyet dinh thiet ke, khong phai tinh co.
    """
    scorer = TempoFitScorer(config)
    scaling_dying = abs(scorer("A", feature(tempo="scaling"), GameState(hp=10)).score - 0.5)
    immediate_healthy = abs(
        scorer("A", feature(tempo="immediate"), GameState(hp=100)).score - 0.5
    )
    assert scaling_dying > immediate_healthy


# --- ScoringConfig / ablation ---------------------------------------------


def test_ablation_zeroes_one_weight_and_renormalizes(config) -> None:
    ablated = config.with_ablation("board_fit")
    assert ablated.weight("board_fit") == 0.0
    assert sum(ablated.weights.values()) == pytest.approx(1.0)


def test_only_keeps_a_single_weight(config) -> None:
    """Cau hinh "chi w1" la baseline stats tinh cua SPEC 12.4."""
    only_base = config.only("base")
    assert only_base.weight("base") == 1.0
    assert sum(only_base.weights.values()) == 1.0


def test_config_loads_from_yaml() -> None:
    """Trong so phai doc duoc tu file - ablation study khong duoc sua code."""
    cfg = ScoringConfig.load("config/scoring_weights.yaml")
    assert set(cfg.weights) == set(ScoringConfig.COMPONENTS)
    assert sum(cfg.weights.values()) == pytest.approx(1.0)


def test_top_level_comp_selector_block_reaches_tuning(tmp_path) -> None:
    """Khoi `comp_selector:` o cap cao nhat phai den duoc CompSelector.

    Truoc khi co ScoringConfig.TOP_LEVEL_TUNING, khoi nay la CONFIG CHET:
    CompSelector doc no bang cfg.tune("comp_selector") nhung load() chi lay
    `weights` va `tuning`, nen sua so trong YAML khong co tac dung gi va
    CompSelector im lang dung DEFAULT_WEIGHTS trong code. Khong test nao bat
    duoc vi hai bo gia tri tinh co trung nhau - test nay dung gia tri KHAC
    han mac dinh de bay ra chenh lech.
    """
    path = tmp_path / "w.yaml"
    path.write_text(
        "weights: {base: 1.0}\n"
        "tuning: {}\n"
        "comp_selector:\n"
        "  unit: 0.77\n"
        "  stability: {pivot_penalty: 0.99}\n",
        encoding="utf-8",
    )
    tune = ScoringConfig.load(path).tune("comp_selector")
    assert tune["unit"] == 0.77
    assert tune["stability"]["pivot_penalty"] == 0.99


def test_shipped_comp_selector_weights_are_actually_read() -> None:
    """File that trong repo cung phai di qua duong do, khong chi file tam."""
    tune = ScoringConfig.load("config/scoring_weights.yaml").tune("comp_selector")
    assert tune, "khoi comp_selector: khong den duoc tuning - config chet"
    assert set(tune) >= {"unit", "item", "meta", "augment", "stability"}


# --- AugmentAdvisor (tong hop) --------------------------------------------


@pytest.fixture
def advisor(config) -> AugmentAdvisor:
    table = FeatureTable({
        "ECON": feature(api_name="ECON", name="Econ", category="econ", econ_value=3),
        "TRAIT": feature(
            api_name="TRAIT", name="Trait", category="trait",
            trait_affinity=["DA_18_Ravager"], carry_type="AD",
        ),
        "SCALE": feature(api_name="SCALE", name="Scale", tempo="scaling"),
    })
    return AugmentAdvisor(table, NullProvider(), config)


def test_advisor_ranks_by_situation_not_by_augment(advisor) -> None:
    """Cung ba augment, hai tinh huong khac nhau -> thu hang phai khac nhau.

    Day la mot cau khang dinh cua ca do an: neu test nay do len thi advisor
    khong hon mot bang stats tinh.
    """
    early = GameState(stage="2-1", hp=95, active_traits={})
    late = GameState(
        stage="5-2", hp=18, active_traits={"Ravager": 3},
        board=[Champion(name="C", cost=4, items=["BFSword"], position=(1, 1))],
    )
    assert advisor.rank(["ECON", "TRAIT", "SCALE"], early).order[0] == "ECON"
    assert advisor.rank(["ECON", "TRAIT", "SCALE"], late).order[0] == "TRAIT"


def test_advisor_is_deterministic(advisor) -> None:
    """Cung dau vao -> cung dau ra, ke ca khi diem bang nhau."""
    state = GameState(stage="3-2", hp=60)
    first = advisor.rank(["ECON", "TRAIT", "SCALE"], state).order
    second = advisor.rank(["SCALE", "ECON", "TRAIT"], state).order
    assert first == second


def test_advisor_scores_both_halves_of_an_ambiguous_pair(advisor) -> None:
    """SPEC 3.5.4: gap cap map mo thi hien CA HAI, khong duoc doan."""
    choice = AugmentChoice(["ECON", "TRAIT"], confidence=0.8, display_name="Trung ten")
    ranking = advisor.rank([choice], GameState(stage="2-1"))
    assert len(ranking) == 2
    assert all(e.ambiguous for e in ranking)


def test_advisor_handles_augment_missing_from_feature_table(advisor) -> None:
    """Augment moi ra ma bang chua sinh lai -> khong crash, phan con lai van hoat dong."""
    ranking = advisor.rank(["KHONG_CO_TRONG_BANG"], GameState())
    assert len(ranking) == 1
    # Base component bi phat xuong 0.35 do khong co stats trong NullProvider
    assert ranking.entries[0].components["base"].score == 0.35
    assert "Chưa có data/tier list chính xác" in ranking.entries[0].components["base"].reason
    # Cac thanh phan khac deu trung tinh vi khong co feature
    for name, c in ranking.entries[0].components.items():
        if name != "base":
            assert c.is_neutral


def test_every_component_returns_a_reason(advisor) -> None:
    """Ly do la bat buoc o MOI thanh phan - khong co ngoai le."""
    _, components = advisor.score_one("ECON", GameState(stage="2-1"))
    assert set(components) == set(ScoringConfig.COMPONENTS)
    for name, comp in components.items():
        assert comp.reason.strip(), f"{name} tra ve ly do rong"


def test_explain_marks_ambiguous_pairs(advisor) -> None:
    choice = AugmentChoice(["ECON", "TRAIT"])
    text = advisor.explain(advisor.rank([choice], GameState()))
    assert "KHÔNG PHÂN BIỆT ĐƯỢC" in text


def test_composite_provider_keeps_first_source() -> None:
    """Gop nguon KHONG duoc trung binh cong - provenance phai giu nguyen."""
    primary = FakeProvider({"X": AugmentStats("X", 3.9, sample_n=500, source="riot")})
    secondary = FakeProvider({"X": AugmentStats("X", 4.4, sample_n=10, source="csv")})
    merged = CompositeProvider([primary, secondary])
    assert merged.get("X").source == "riot"
