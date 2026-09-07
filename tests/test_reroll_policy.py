"""Test chinh sach reroll augment (SPEC 3.5.5).

Cach test o day theo dung tinh than test_scoring.py: dau vao TONG HOP, va moi
test giu nguyen moi thu tru MOT bien roi assert quyet dinh doi dung huong.

Khac mot diem quan trong: ba trong so test duoi day khong kiem tra "so co
dep khong" ma kiem tra DINH LY. T1/T2/T3 la ket qua chung minh duoc, nen neu
chung gay thi loi nam o code chu khong phai o nguong nao can chinh.
"""

from __future__ import annotations

import math

import pytest

from src.decision.augment_advisor import AugmentAdvisor, AugmentChoice
from src.decision.reroll_policy import (
    DEFAULT_COST_MATRIX,
    TIER_NAMES,
    PoolDistribution,
    RerollState,
    RerollTuning,
    SlotView,
    build_advice,
    decide,
    is_fabricated,
    slot_views,
    tailoring_weight,
)
from src.decision.scoring import ScoringConfig
from src.game_state.models import Champion, GameState
from src.knowledge.augment_features import AugmentFeature, FeatureTable
from src.knowledge.stats_provider import AugmentStats


class FakeProvider:
    """Nguon so lieu trong bo nho - test khong duoc cham dia lan mang."""

    name = "fake"

    def __init__(self, rows: dict[str, AugmentStats] | None = None) -> None:
        self.rows = rows or {}

    def get(self, api_name: str) -> AugmentStats | None:
        return self.rows.get(api_name)


def pool(
    scores,
    *,
    tier: int = 2,
    weights=None,
    source: str = "test",
    sample_n: int = 0,
    evidence: str = "uncalibrated",
) -> PoolDistribution:
    """Pool tong hop tu mot danh sach diem (chua can sap)."""
    ordered = sorted(float(s) for s in scores)
    w = list(weights) if weights else [1.0] * len(ordered)
    total = sum(w) or 1.0
    return PoolDistribution(
        tier=tier,
        scores=tuple(ordered),
        weights=tuple(x / total for x in w),
        api_names=tuple(f"DA_{i}" for i in range(len(ordered))),
        source=source,
        sample_n=sample_n,
        is_evidence=evidence == "measured",
        evidence=evidence,  # type: ignore[arg-type]
    )


def views(*scores, ambiguous_at: int | None = None, hi=None) -> list[SlotView]:
    """Ba o voi diem cho truoc. `ambiguous_at` bien mot o thanh khoang."""
    out = []
    for i, s in enumerate(scores):
        upper = float(hi) if (ambiguous_at == i and hi is not None) else float(s)
        out.append(
            SlotView(
                index=i,
                lo=float(s),
                hi=upper,
                ambiguous=(ambiguous_at == i),
                name=f"slot{i}",
                api_names=(f"DA_slot{i}",),
            )
        )
    return out


def feature(**kwargs) -> AugmentFeature:
    base = dict(api_name="DA_Test", name="Test", tier=2)
    base.update(kwargs)
    return AugmentFeature(**base)


# --- PoolDistribution: phep tinh phai CHINH XAC, khong xap xi --------------


def test_expected_max_matches_brute_force() -> None:
    """g(floor) phai bang trung binh co trong so tinh tho, den 1e-12.

    Day la test nen mong: ca chinh sach dung tren mot cong thuc tong hau to.
    Neu no lech thi moi nguong deu sai ma khong co trieu chung nao khac.
    """
    scores = [0.1, 0.25, 0.4, 0.55, 0.7, 0.9]
    w = [3.0, 1.0, 1.0, 2.0, 1.0, 1.0]
    p = pool(scores, weights=w)
    # `pool()` sap lai diem nhung khong sap trong so - dung bo da khop san.
    p = PoolDistribution(
        tier=2,
        scores=tuple(scores),
        weights=tuple(x / sum(w) for x in w),
        api_names=tuple(f"DA_{i}" for i in range(len(scores))),
        source="test",
        sample_n=0,
        is_evidence=False,
    )
    for floor in (0.0, 0.05, 0.25, 0.3, 0.55, 0.85, 0.9, 1.0):
        brute = sum(
            (x / sum(w)) * max(floor, s) for x, s in zip(w, scores)
        )
        assert p.expected_max(floor) == pytest.approx(brute, abs=1e-12)


def test_tail_integral_is_zero_above_the_pool_max() -> None:
    p = pool([0.2, 0.4, 0.6])
    assert p.tail_integral(0.6) == pytest.approx(0.0)
    assert p.tail_integral(0.99) == pytest.approx(0.0)


def test_sigma_is_the_population_sd_of_the_pool() -> None:
    scores = [0.2, 0.4, 0.6, 0.8]
    p = pool(scores)
    mean = sum(scores) / len(scores)
    expected = math.sqrt(sum((s - mean) ** 2 for s in scores) / len(scores))
    assert p.sigma == pytest.approx(expected)


def test_certainty_equivalent_is_expected_max_when_risk_neutral() -> None:
    p = pool([0.3, 0.5, 0.7])
    assert p.certainty_equivalent(0.4, 0.0) == pytest.approx(p.expected_max(0.4))


def test_risk_aversion_lowers_the_certainty_equivalent() -> None:
    """lambda > 0 = ngai rui ro, nen tuong duong chac chan phai TUT xuong."""
    p = pool([0.1, 0.5, 0.9])
    assert p.certainty_equivalent(0.0, 2.0) < p.certainty_equivalent(0.0, 0.0)
    assert p.certainty_equivalent(0.0, -2.0) > p.certainty_equivalent(0.0, 0.0)


# --- T2: doi la mien phi thi PHAI doi ---------------------------------------


@pytest.mark.parametrize("incumbent", [0.05, 0.3, 0.5, 0.9, 0.99])
def test_free_reroll_beats_picking_whenever_the_pool_can_still_improve(
    incumbent: float,
) -> None:
    """T2: c = 0 va n >= 2 -> REROLL troi hon PICK theo nghia yeu.

    Ke ca khi the dan dau da rat cao. Doi o TE NHAT khong dung den the dan
    dau, nen gia tri dung khong the tut; mot lan rut them chi co the them.
    Dung som luc do la lo EV, du truc giac noi nguoc lai.

    Dieu kien "pool con cai gi do tot hon" la thuc chat: xem test ke ben cho
    truong hop bang nhau.
    """
    p = pool([0.2, 0.4, 0.6, 0.8, 1.0])
    v = views(0.01, 0.02, incumbent)
    action, target, _, gain, _ = decide(v, RerollState(), p, cost=0.0)
    assert action == "REROLL"
    assert target == 0  # o te nhat
    assert gain > 0.0


def test_dominance_is_weak_and_ties_break_toward_stopping() -> None:
    """Bien cua T2: the dan dau da bang dinh pool -> loi ky vong DUNG BANG 0.

    T2 la troi hon theo nghia YEU, khong phai chat. Khi tich phan duoi bang 0
    thi doi hay khong deu toi uu, va chinh sach chon DUNG: mot cu bam khong
    doi lay gi van ton dong ho ~30 giay va - duoi gia dinh burn_on_reveal -
    con dot them mot the khoi pool cua chang sau.
    """
    p = pool([0.2, 0.4, 0.6, 0.8, 1.0])
    action, _, _, gain, _ = decide(views(0.05, 0.10, 1.0), RerollState(), p, cost=0.0)
    assert gain == pytest.approx(0.0)
    assert action == "PICK"


def test_the_worst_slot_is_the_target_wherever_it_sits() -> None:
    """T1 khong quan tam o nao dang dan dau - chi quan tam o nao te nhat."""
    p = pool([0.2, 0.4, 0.6, 0.8, 1.0])
    action, target, _, _, _ = decide(views(0.05, 0.10, 0.0), RerollState(), p, cost=0.0)
    assert (action, target) == ("REROLL", 2)


def test_reroll_stops_being_free_once_a_cost_is_charged() -> None:
    """Cung mot the dan dau: c = 0 thi doi, c lon thi thoi. Khong co gi khac doi."""
    p = pool([0.2, 0.4, 0.6, 0.8])
    v = views(0.1, 0.5, 0.75)
    assert decide(v, RerollState(), p, cost=0.0)[0] == "REROLL"
    assert decide(v, RerollState(), p, cost=0.5)[0] == "PICK"


# --- T1: luon doi o te nhat -------------------------------------------------


@pytest.mark.parametrize(
    "scores,expected",
    [
        ((0.1, 0.5, 0.9), 0),
        ((0.9, 0.1, 0.5), 1),
        ((0.5, 0.9, 0.1), 2),
    ],
)
def test_reroll_target_is_always_the_worst_slot_holding_a_token(scores, expected) -> None:
    p = pool([0.3, 0.6, 0.95])
    action, target, _, _, _ = decide(views(*scores), RerollState(), p, cost=0.0)
    assert action == "REROLL"
    assert target == expected


def test_a_spent_slot_is_never_the_reroll_target_even_when_it_is_worst() -> None:
    """O te nhat KHONG con luot thi phai doi o te nhi - khong doi bua o khac."""
    p = pool([0.3, 0.6, 0.95])
    v = views(0.05, 0.20, 0.80)
    action, target, _, _, _ = decide(v, RerollState((False, True, True)), p, cost=0.0)
    assert action == "REROLL"
    assert target == 1


def test_fallback_slot_is_the_best_slot_we_keep() -> None:
    p = pool([0.3, 0.6, 0.95])
    action, target, fallback, _, _ = decide(views(0.1, 0.4, 0.8), RerollState(), p, cost=0.0)
    assert (action, target, fallback) == ("REROLL", 0, 2)


# --- T3: nguong o buoc cuoi -------------------------------------------------


def test_last_token_flips_exactly_at_g_of_the_retained_floor() -> None:
    """n = 1 va o do dang la CAO NHAT: doi no la vut chinh no di.

    Luc nay san giu lai tut ve `L` = diem cao nhat trong cac o da tieu luot,
    va nguong dung chinh la g(L). Test dat the dan dau ngay tren va ngay duoi
    nguong ay roi doi chieu hai quyet dinh.
    """
    p = pool([0.0, 0.5, 1.0])
    floor = 0.30
    threshold = p.expected_max(floor)  # g(L)

    below = views(0.10, floor, threshold - 0.01)
    above = views(0.10, floor, threshold + 0.01)
    tokens = RerollState((False, False, True))

    assert decide(below, tokens, p, cost=0.0)[0] == "REROLL"
    assert decide(above, tokens, p, cost=0.0)[0] == "PICK"


def test_threshold_is_the_reservation_value_the_best_card_must_beat() -> None:
    p = pool([0.2, 0.5, 0.8])
    v = views(0.1, 0.3, 0.7)
    _, _, _, gain, threshold = decide(v, RerollState(), p, cost=0.0)
    assert threshold == pytest.approx(p.expected_max(0.7))
    assert gain == pytest.approx(threshold - 0.7)


def test_no_tokens_left_forces_a_pick_of_the_best_slot() -> None:
    p = pool([0.2, 0.5, 0.8])
    action, target, fallback, gain, _ = decide(
        views(0.1, 0.9, 0.4), RerollState((False, False, False)), p, cost=0.0
    )
    assert (action, target, fallback, gain) == ("PICK", 1, 2, 0.0)


# --- c(tier, stage): bien 4-2 va thang do sigma -----------------------------


@pytest.mark.parametrize("tier", [1, 2, 3])
def test_stage_four_costs_nothing_for_every_tier(tier: int) -> None:
    """4-2 la chang augment CUOI: khong con pool tuong lai de dot.

    Day khong phai mot lua chon hieu chinh ma la dieu kien bien cua mo hinh.
    Neu dong nay gay thi bang c da bi sua sai ban chat.
    """
    tuning = RerollTuning()
    assert tuning.cost(tier, 4) == 0.0
    assert tuning.cost_for(pool([0.1, 0.9], tier=tier), 4) == 0.0


def test_cost_is_measured_in_pool_sigma_not_raw_score_points() -> None:
    """Bang c la BOI CUA SIGMA, khong phai diem tho.

    Do 2026-09-07: sd(Score) tren mot bac chi ~0,05 va tich phan duoi voi mot
    the dan dau thuc te chi 0,002-0,009. Neu doc bang so nhu tuyet doi thi
    prismatic 0,08 lon hon MOI loi ich co the co -> khong bao gio doi the,
    trai han y do da phat bieu. Test nay khoa lai cach doc dung.
    """
    tuning = RerollTuning()
    p = pool([0.50, 0.55, 0.60, 0.65], tier=3)
    assert tuning.cost(3, 2) == 0.08
    assert tuning.cost_for(p, 2) == pytest.approx(0.08 * p.sigma)
    assert tuning.cost_for(p, 2) < 0.08  # nho hon han so tho

    absolute = RerollTuning(cost_unit="absolute")
    assert absolute.cost_for(p, 2) == pytest.approx(0.08)


def test_prismatic_charges_more_than_gold_at_the_same_stage() -> None:
    """Pool prismatic nho nhat -> lo them mot the tot dat hon. Thu tu nay la
    toan bo noi dung cua bang c; con so cu the thi chua duoc do."""
    tuning = RerollTuning()
    assert tuning.cost(3, 2) > tuning.cost(2, 2)
    assert tuning.cost(3, 2) > tuning.cost(3, 3) > tuning.cost(3, 4)


def test_cost_matrix_covers_every_tier_name() -> None:
    for tier, name in TIER_NAMES.items():
        assert name in DEFAULT_COST_MATRIX
        assert set(DEFAULT_COST_MATRIX[name]) == {"stage_2", "stage_3", "stage_4"}


# --- Tailoring --------------------------------------------------------------


def test_tailoring_lifts_augments_matching_an_active_trait() -> None:
    f = feature(trait_affinity=["DA_18_Ravager"])
    assert tailoring_weight(f, {"Ravager": 3}, beta=1.0) == 2.0
    assert tailoring_weight(f, {"Bastion": 3}, beta=1.0) == 1.0


def test_tailoring_beta_zero_recovers_the_uniform_pool() -> None:
    """beta = 0 la nhanh doi chung cua ablation - phai deu tuyet doi."""
    f = feature(trait_affinity=["DA_18_Ravager"])
    assert tailoring_weight(f, {"Ravager": 3}, beta=0.0) == 1.0


def test_tailoring_raises_expected_max_when_good_augments_match() -> None:
    """Neu the trung trait lai la the diem cao thi g(R) phai TANG.

    Day chinh la thien lech ma mot pool deu gay ra: no danh gia thap gia tri
    cua mot lan doi va lam may so reroll mot cach nhan tao.
    """
    scores = [0.3, 0.4, 0.5, 0.9]
    flat = pool(scores)
    tailored = pool(scores, weights=[1.0, 1.0, 1.0, 2.0])
    assert tailored.expected_max(0.5) > flat.expected_max(0.5)


def test_tailoring_changes_nothing_when_no_augment_matches() -> None:
    scores = [0.3, 0.5, 0.7]
    flat = pool(scores)
    same = pool(scores, weights=[1.0, 1.0, 1.0])
    assert same.expected_max(0.4) == pytest.approx(flat.expected_max(0.4))


# --- Muc do bang chung KHONG duoc chan quyet dinh ---------------------------


def test_uncalibrated_pool_still_returns_a_concrete_action() -> None:
    """Hoi quy cho loi "te liet o che do suy giam".

    `B` va `F_S` cung sinh ra tu MOT ham diem, nen phep so sanh giua chung bat
    bien qua moi phep hieu chinh don dieu - no van dung khi Base trung tinh o
    ca 254 augment. Tu choi tra loi la vut di mot so sanh HOP LE chi vi thieu
    mot phep hieu chuan tuyet doi. Duoc phep ha giong cau chu, khong duoc phep
    ha hanh dong.
    """
    p = pool([0.2, 0.5, 0.9], source="MOCK-NOT-REAL", evidence="uncalibrated")
    advice = build_advice(views(0.1, 0.4, 0.6), RerollState(), p, RerollTuning(), 2)
    assert advice.action in ("PICK", "REROLL")
    assert advice.evidence == "uncalibrated"
    assert "chưa quy ra placement" in advice.reason


def test_uncalibrated_and_measured_pools_agree_on_the_action() -> None:
    """Cung mot phan bo, chi khac nhan bang chung -> cung mot quyet dinh."""
    scores = [0.2, 0.5, 0.9]
    v = views(0.1, 0.4, 0.6)
    a = build_advice(v, RerollState(), pool(scores, evidence="uncalibrated"), RerollTuning(), 2)
    b = build_advice(v, RerollState(), pool(scores, evidence="measured"), RerollTuning(), 2)
    assert (a.action, a.target_slot) == (b.action, b.target_slot)


def test_mock_data_is_never_reported_as_measured() -> None:
    """Bo so gia lap bia san sample_n > 200 nen `is_evidence` tra True.

    Voi BaseScorer dieu do vo hai - no in thang `source` ra overlay. Nhung muc
    `evidence` o day dieu khien cau canh bao, nen no phai nhin ca ten nguon.
    """
    assert is_fabricated("MOCK-NOT-REAL")
    assert is_fabricated("mock-anything")
    assert not is_fabricated("tactics.tools")


def test_advice_always_carries_provenance() -> None:
    p = pool([0.2, 0.5], source="nguon-x", sample_n=1234, evidence="measured")
    advice = build_advice(views(0.1, 0.3, 0.4), RerollState(), p, RerollTuning(), 3)
    assert advice.pool_source == "nguon-x"
    assert advice.pool_n == 2
    assert "nguon-x" in advice.reason


# --- Cap map mo -------------------------------------------------------------


def test_ambiguous_slot_straddling_the_threshold_falls_back_to_pick() -> None:
    """Khoang [lo, hi] vat qua nguong -> quyet dinh lat theo cach doc.

    Quy tac cua du an la khong bao gio doan mot cap map mo. O day dieu do
    nghia la: khong doi the khi chua chac, va phai noi ro vi sao.
    """
    p = pool([0.0, 0.5, 1.0])
    # O 2 mo ho: doc thap thi duoi nguong (nen doi), doc cao thi tren nguong.
    v = views(0.10, 0.20, 0.30, ambiguous_at=2, hi=0.99)
    advice = build_advice(v, RerollState((False, False, True)), p, RerollTuning(), 4)
    assert advice.action == "PICK"
    assert advice.ambiguous
    assert "KHÔNG PHÂN BIỆT ĐƯỢC" in advice.reason


def test_ambiguous_slot_that_does_not_change_the_decision_is_acted_on() -> None:
    """Mo ho ma quyet dinh KHONG doi thi van hanh dong binh thuong."""
    p = pool([0.2, 0.4, 0.6, 0.8, 1.0])
    v = views(0.02, 0.05, 0.08, ambiguous_at=2, hi=0.09)
    advice = build_advice(v, RerollState(), p, RerollTuning(), 4)
    assert advice.action == "REROLL"
    assert advice.target_slot == 0
    assert advice.ambiguous  # van gan nhan, nhung khong chan


def test_slot_views_collapses_both_halves_of_a_pair_into_one_interval() -> None:
    table = FeatureTable(
        {
            "DA_A": feature(api_name="DA_A", name="A"),
            "DA_B": feature(api_name="DA_B", name="B"),
            "DA_C": feature(api_name="DA_C", name="C"),
        }
    )
    stats = FakeProvider(
        {
            "DA_A": AugmentStats("DA_A", avg_place=3.6, sample_n=500, source="s"),
            "DA_B": AugmentStats("DA_B", avg_place=4.9, sample_n=500, source="s"),
        }
    )
    advisor = AugmentAdvisor(table, stats, ScoringConfig.default())
    state = GameState(stage="3-2")
    ranking = advisor.rank(
        [AugmentChoice(["DA_A", "DA_B"]), AugmentChoice(["DA_C"])], state
    )

    v = slot_views(ranking)
    assert len(v) == 2
    assert v[0].ambiguous and v[0].lo < v[0].hi
    assert not v[1].ambiguous and v[1].lo == v[1].hi


# --- Tich hop voi AugmentAdvisor -------------------------------------------


@pytest.fixture
def advisor() -> AugmentAdvisor:
    table = FeatureTable(
        {
            f"DA_G{i}": feature(api_name=f"DA_G{i}", name=f"G{i}", tier=2, econ_value=i % 4)
            for i in range(12)
        }
        | {
            f"DA_P{i}": feature(api_name=f"DA_P{i}", name=f"P{i}", tier=3, econ_value=i % 4)
            for i in range(8)
        }
    )
    return AugmentAdvisor(table, FakeProvider(), ScoringConfig.default())


def test_pool_distribution_only_scores_the_offered_tier(advisor) -> None:
    """Cham ca 254 augment la 12,2 ms p95 - VO ngan sach 5 ms. Loc theo bac."""
    state = GameState(stage="3-2")
    assert len(advisor.pool_distribution(2, state)) == 12
    assert len(advisor.pool_distribution(3, state)) == 8


def test_pool_distribution_excludes_what_is_already_on_screen(advisor) -> None:
    state = GameState(stage="3-2")
    p = advisor.pool_distribution(2, state, exclude=["DA_G0", "DA_G1"])
    assert len(p) == 10
    assert "DA_G0" not in p.api_names


def test_pool_scores_come_back_sorted_ascending(advisor) -> None:
    p = advisor.pool_distribution(2, GameState(stage="3-2"))
    assert list(p.scores) == sorted(p.scores)


def test_advise_reroll_is_deterministic(advisor) -> None:
    state = GameState(stage="3-2")
    ranking = advisor.rank(["DA_G1", "DA_G2", "DA_G3"], state)
    first = advisor.advise_reroll(ranking, state, RerollState())
    second = advisor.advise_reroll(ranking, state, RerollState())
    assert first.to_dict() == second.to_dict()


def test_advise_reroll_reads_the_tier_from_the_offered_cards(advisor) -> None:
    state = GameState(stage="4-2")
    ranking = advisor.rank(["DA_P1", "DA_P2", "DA_P3"], state)
    advice = advisor.advise_reroll(ranking, state, RerollState())
    assert advice.pool_n == 5  # 8 prismatic tru 3 the dang hien
    assert advice.depletion_cost == 0.0  # 4-2


def test_advise_reroll_never_touches_the_ranking(advisor) -> None:
    """`rank()` la duong da co test phu kin - reroll khong duoc lam no doi."""
    state = GameState(stage="3-2")
    ranking = advisor.rank(["DA_G1", "DA_G2", "DA_G3"], state)
    before = ranking.order
    advisor.advise_reroll(ranking, state, RerollState())
    assert ranking.order == before


def test_reroll_policy_block_is_not_dead_config() -> None:
    """Khoi `reroll_policy:` nam o CAP CAO NHAT trong YAML.

    Neu no khong duoc liet vao TOP_LEVEL_TUNING thi sua file se khong co tac
    dung gi ma khong test nao bat duoc - dung cai bay da xay ra voi
    comp_selector (xem chu thich o scoring/types.py).
    """
    config = ScoringConfig.load("config/scoring_weights.yaml")
    tuning = config.tune("reroll_policy")
    assert tuning, "khoi reroll_policy khong den duoc tuning"
    assert "cost_matrix" in tuning

    parsed = RerollTuning.from_config(config)
    assert parsed.cost(3, 2) == pytest.approx(tuning["cost_matrix"]["prismatic"]["stage_2"])


def test_shipped_config_still_rerolls_gold_but_stops_early_on_prismatic(advisor) -> None:
    """Hai che do phai TACH NHAU duoi bang c da ship.

    Gold pool lon -> dot ~1% -> gan nhu luon doi. Prismatic pool nho -> lo mot
    the tot ma khong lay duoc la dot that -> dung som khi da co the manh.
    Neu hai dong nay bang nhau thi bang c khong con noi len dieu gi.
    """
    config = ScoringConfig.load("config/scoring_weights.yaml")
    tuning = RerollTuning.from_config(config)
    state = GameState(stage="2-1")

    p_gold = advisor.pool_distribution(2, state)
    p_pris = advisor.pool_distribution(3, state)
    assert tuning.cost_for(p_pris, 2) > tuning.cost_for(p_gold, 2)


# --- Ngan sach do tre -------------------------------------------------------


def test_a_decision_is_cheap_once_the_pool_is_cached(advisor) -> None:
    """Dung pool da cache thi moi quyet dinh chi la O(log N).

    Nguong 0,5 ms rat rong so voi thuc te (~vai microsecond) - no o day de bat
    mot hoi quy kieu "lo tinh lai ca pool moi buoc", chu khong phai de do hieu
    nang chinh xac. Do that phai lam khi game dang chay (SPEC 12.1).
    """
    import time

    state = GameState(stage="3-2")
    ranking = advisor.rank(["DA_G1", "DA_G2", "DA_G3"], state)
    cached = advisor.pool_distribution(2, state)

    samples = []
    for _ in range(200):
        t0 = time.perf_counter()
        advisor.advise_reroll(ranking, state, RerollState(), pool=cached)
        samples.append((time.perf_counter() - t0) * 1000)
    samples.sort()
    assert samples[int(0.95 * len(samples))] < 0.5
