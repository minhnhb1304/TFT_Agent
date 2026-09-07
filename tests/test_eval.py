"""Test bo cong cu danh gia (SPEC 12).

Cac test o day chay tren scenario TONG HOP, va do la ca diem: bo cong cu danh
gia phai duoc kiem chung TRUOC khi co du lieu that. Neu doi den luc co dataset
that moi viet, thi den luc phat hien Spearman cai sai se khong con thoi gian.

Moi ham thong ke tu cai (Spearman co dong hang, Kendall tau, Brennan-Prediger S,
phan vi) deu duoc doi chieu voi mot vi du tinh tay.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from src.decision.augment_advisor import AugmentAdvisor
from src.decision.scoring.types import ScoringConfig
from src.eval.ablation import AblationRunner, kendall_tau
from src.eval.correlation import analyze as analyze_correlation
from src.eval.correlation import rank_with_ties, spearman
from src.eval.expert_study import (
    ExpertEntry,
    analyze as analyze_experts,
    bootstrap_ci,
    chance_corrected_agreement,
    export_scenarios,
    load_expert_entries,
)
from src.eval.recognition import Prediction, evaluate as evaluate_recognition, percentile
from src.eval.scenario_logger import Scenario, ScenarioLogger, load_scenarios
from src.game_state.models import Champion, GameState
from src.knowledge.augment_features import AugmentFeature, FeatureTable
from src.knowledge.stats_provider import AugmentStats

FIXED_TIME = datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc)


def features() -> FeatureTable:
    return FeatureTable({
        "ECON": AugmentFeature(api_name="ECON", name="Econ", category="econ", econ_value=3),
        "TRAIT": AugmentFeature(
            api_name="TRAIT", name="Trait", trait_affinity=["DA_18_Ravager"], carry_type="AD"
        ),
        "SCALE": AugmentFeature(api_name="SCALE", name="Scale", tempo="scaling"),
    })


def make_logger(tmp_path, offset: int = 0) -> ScenarioLogger:
    stamps = iter(
        datetime(2026, 8, 29, 12, 0, i, tzinfo=timezone.utc) for i in range(offset, offset + 100)
    )
    return ScenarioLogger(tmp_path, clock=lambda: next(stamps))


# --- ScenarioLogger (SPEC 12.0) -------------------------------------------


def test_logged_scenario_round_trips(tmp_path) -> None:
    """Ban ghi phai du de cham diem lai - ablation phu thuoc hoan toan vao dieu nay."""
    advisor = AugmentAdvisor(features())
    state = GameState(stage="4-2", hp=30, gold=42, board=[
        Champion(name="C", cost=4, star_level=2, items=["BFSword"], position=(2, 3)),
    ])
    ranking = advisor.rank(["ECON", "TRAIT"], state)

    path = make_logger(tmp_path).log(ranking, state, frame_ref="frames/0001.png")
    loaded = load_scenarios(tmp_path)

    assert len(loaded) == 1
    scenario = loaded[0]
    assert scenario.game_state == state
    assert scenario.ranking == ranking.order
    assert scenario.frame_ref == "frames/0001.png"
    assert scenario.weights == ranking.weights
    assert path.exists()


def test_logger_can_be_disabled(tmp_path) -> None:
    advisor = AugmentAdvisor(features())
    ranking = advisor.rank(["ECON"], GameState())
    assert ScenarioLogger(tmp_path, enabled=False).log(ranking, GameState()) is None
    assert list(tmp_path.glob("*.json")) == []


def test_back_fill_placement_overwrites_in_place(tmp_path) -> None:
    logger = make_logger(tmp_path)
    ranking = AugmentAdvisor(features()).rank(["ECON"], GameState())
    path = logger.log(ranking, GameState(), player_pick="ECON")

    logger.back_fill_placement(path, 2)

    assert len(list(tmp_path.glob("*.json"))) == 1, "khong duoc de lai ban sao"
    assert json.loads(path.read_text(encoding="utf-8"))["final_placement"] == 2


def test_pick_rank_is_one_based() -> None:
    scenario = Scenario(ts="", game_state=GameState(), ranking=["A", "B", "C"], player_pick="B")
    assert scenario.pick_rank == 2


def test_pick_rank_is_none_when_pick_unknown() -> None:
    scenario = Scenario(ts="", game_state=GameState(), ranking=["A"], player_pick=None)
    assert scenario.pick_rank is None


def test_corrupt_file_is_skipped_not_fatal(tmp_path) -> None:
    (tmp_path / "bad.json").write_text("{khong phai json", encoding="utf-8")
    make_logger(tmp_path).log(AugmentAdvisor(features()).rank(["ECON"], GameState()), GameState())
    assert len(load_scenarios(tmp_path)) == 1


# --- Correlation (SPEC 12.2) ----------------------------------------------


def test_rank_with_ties_uses_average_ranks() -> None:
    """Dataset chac chan co dong hang - xep hang tho se lam lech he so."""
    assert rank_with_ties([10, 20, 20, 30]) == [1.0, 2.5, 2.5, 4.0]


def test_spearman_matches_hand_computed_values() -> None:
    assert spearman([1, 2, 3, 4], [1, 2, 3, 4]) == pytest.approx(1.0)
    assert spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert spearman([1, 2, 3], [2, 2, 2]) == pytest.approx(0.0)


def test_correlation_detects_the_hypothesised_direction() -> None:
    """Chon augment advisor xep cao -> placement tot hon."""
    scenarios = [
        Scenario(ts="", game_state=GameState(), ranking=["A", "B", "C"],
                 player_pick=pick, final_placement=place)
        for pick, place in [("A", 1), ("A", 2), ("B", 4), ("B", 4), ("C", 7), ("C", 8)]
    ]
    result = analyze_correlation(scenarios)
    assert result.n == 6
    assert result.rho > 0.9
    assert result.supports_hypothesis


def test_correlation_reports_limits_of_observational_data() -> None:
    """Bao cao khong duoc phep im ve gioi han phuong phap."""
    scenarios = [
        Scenario(ts="", game_state=GameState(), ranking=["A", "B"],
                 player_pick="A", final_placement=p)
        for p in (1, 2, 3)
    ]
    text = analyze_correlation(scenarios).report()
    assert "khong phai thi nghiem co doi chung" in text
    assert "nhan qua" in text


def test_correlation_counts_skipped_unlabelled_scenarios() -> None:
    labelled = Scenario(ts="", game_state=GameState(), ranking=["A"], player_pick="A",
                        final_placement=1)
    unlabelled = Scenario(ts="", game_state=GameState(), ranking=["A"])
    result = analyze_correlation([labelled, labelled, unlabelled])
    assert result.n == 2 and result.skipped == 1


def test_correlation_is_safe_on_tiny_datasets() -> None:
    assert analyze_correlation([]).n == 0


# --- Ablation (SPEC 12.4) --------------------------------------------------


def _ablation_scenarios() -> list[Scenario]:
    advisor = AugmentAdvisor(features())
    states = [
        GameState(stage="2-1", hp=95),
        GameState(stage="5-2", hp=18, active_traits={"Ravager": 3},
                  board=[Champion(name="C", cost=4, items=["BFSword"], position=(2, 2))]),
        GameState(stage="3-4", hp=55, active_traits={"Ravager": 2}),
    ]
    out = []
    for i, state in enumerate(states):
        ranking = advisor.rank(["ECON", "TRAIT", "SCALE"], state)
        out.append(Scenario(
            ts=f"t{i}", game_state=state, ranking=ranking.order,
            component_scores=ranking.component_scores(), weights=ranking.weights,
            player_pick=ranking.order[0], final_placement=i + 1,
        ))
    return out


def test_kendall_tau_is_one_for_identical_orders() -> None:
    assert kendall_tau(["A", "B", "C"], ["A", "B", "C"]) == pytest.approx(1.0)
    assert kendall_tau(["A", "B", "C"], ["C", "B", "A"]) == pytest.approx(-1.0)


def test_ablation_produces_a_row_per_component_plus_baselines() -> None:
    report = AblationRunner(features()).run(_ablation_scenarios())
    labels = [r.label for r in report.rows]
    assert labels[0] == "Full model"
    assert labels[-1] == "chi w1 (stats tinh)"
    assert len(labels) == 2 + len(ScoringConfig.COMPONENTS)


def test_full_model_row_is_identical_to_itself() -> None:
    """Cham diem lai voi cung trong so phai ra y het - neu khong, co gi do ngau nhien."""
    report = AblationRunner(features()).run(_ablation_scenarios())
    full = report.rows[0]
    assert full.top1_change_rate == 0.0
    assert full.kendall_tau == pytest.approx(1.0)


def test_static_stats_baseline_changes_the_ranking() -> None:
    """Dong quan trong nhat cua bang: bo het tru w1 thi ket qua phai KHAC.

    Neu no khong khac, advisor dong khong hon bang stats tinh - va do van la
    mot ket qua nghien cuu hop le, chi la phai bao cao trung thuc.
    """
    report = AblationRunner(features()).run(_ablation_scenarios())
    only_base = report.rows[-1]
    assert only_base.top1_change_rate > 0.0


def test_ablation_rescoring_is_offline_and_deterministic() -> None:
    scenarios = _ablation_scenarios()
    runner = AblationRunner(features())
    assert runner.run(scenarios).to_dict() == runner.run(scenarios).to_dict()


def test_ablation_table_is_readable() -> None:
    table = AblationRunner(features()).run(_ablation_scenarios()).table()
    assert "chi w1 (stats tinh)" in table and "n = 3 scenario" in table


def test_ablation_uses_stats_provider_when_present() -> None:
    """Bo w1 phai co tac dung THAT khi co so lieu - neu khong, dong do vo nghia."""
    class Stats:
        name = "test"

        def get(self, api_name):
            table = {"SCALE": AugmentStats("SCALE", 3.5, sample_n=1000, source="t")}
            return table.get(api_name)

    report = AblationRunner(features(), Stats()).run(_ablation_scenarios())
    base_row = next(r for r in report.rows if r.disabled == "base")
    assert base_row.top1_change_rate > 0.0


# --- Recognition (SPEC 12.1) ----------------------------------------------


def test_percentiles_interpolate() -> None:
    assert percentile([10, 20, 30, 40], 0.5) == pytest.approx(25.0)
    assert percentile([], 0.5) == 0.0


def test_recognition_splits_metrics_per_entity() -> None:
    """Gop chung se giau viec augment dang te hon cac truong so de doc."""
    report = evaluate_recognition([
        Prediction("augment", "A", "A", latency_ms=120),
        Prediction("augment", "B", "C", latency_ms=140),
        Prediction("gold", "50", "50", latency_ms=8),
    ])
    assert report.per_entity["gold"].f1 == pytest.approx(1.0)
    assert report.per_entity["augment"].f1 == pytest.approx(0.5)


def test_wrong_prediction_counts_as_both_fp_and_fn() -> None:
    report = evaluate_recognition([Prediction("augment", "A", "B")])
    metrics = report.per_entity["augment"]
    assert (metrics.fp, metrics.fn, metrics.tp) == (1, 1, 0)


def test_ambiguous_pairs_are_reported_separately() -> None:
    """Cap khong phan biet duoc la GIOI HAN DU LIEU, khong phai loi model."""
    report = evaluate_recognition([
        Prediction("augment", "A", "A"),
        Prediction("augment", "X", "Y", ambiguous_pair=True),
    ])
    assert report.ambiguous.support == 1
    assert report.ambiguous.f1 == 0.0
    assert "GIOI HAN DU LIEU" in report.table()


def test_latency_percentiles_are_per_entity() -> None:
    report = evaluate_recognition(
        [Prediction("augment", "A", "A", latency_ms=v) for v in (100, 200, 300, 400)]
    )
    stats = report.latency_stats("augment")
    assert stats["p50"] == pytest.approx(250.0)
    assert stats["n"] == 4


# --- Expert study (SPEC 12.3) ---------------------------------------------


def test_export_hides_advisor_ranking_to_avoid_anchoring(tmp_path) -> None:
    """Cho chuyen gia thay xep hang truoc la lam hong chinh phep do."""
    scenarios = _ablation_scenarios()
    for i, s in enumerate(scenarios):
        s.path = tmp_path / f"s{i}.json"

    out = export_scenarios(scenarios, tmp_path / "export.json")
    payload = json.loads(out.read_text(encoding="utf-8"))

    assert all(row["expert_ranking"] == [] for row in payload)
    assert all("ranking" not in row for row in payload)
    assert all("tinh_huong" in row and "candidates" in row for row in payload)
    # Bo khoa thoi thi chua du - xem test ben duoi ve THU TU.


def test_unfilled_rows_are_skipped_not_guessed(tmp_path) -> None:
    scenarios = _ablation_scenarios()
    for i, s in enumerate(scenarios):
        s.path = tmp_path / f"s{i}.json"
    out = export_scenarios(scenarios, tmp_path / "export.json")

    payload = json.loads(out.read_text(encoding="utf-8"))
    payload[0]["expert_ranking"] = ["TRAIT", "ECON", "SCALE"]
    out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    entries = load_expert_entries(out, scenarios)
    assert len(entries) == 1


def test_kappa_is_one_on_perfect_agreement() -> None:
    entries = [
        ExpertEntry(f"s{i}", ["A", "B"], ["A", "B"], ["A", "B"]) for i in range(3)
    ] + [ExpertEntry("s4", ["A", "B"], ["B", "A"], ["B", "A"])]
    kappa, observed, _ = chance_corrected_agreement(entries)
    assert observed == pytest.approx(1.0)
    assert kappa == pytest.approx(1.0)


def test_agreement_is_zero_when_there_was_only_one_choice() -> None:
    """Chi chao mot augment thi dong thuan 100% khong noi len dieu gi.

    Ban cu tra 1.0 o day trong khi chinh comment cua no viet "khong co thong
    tin" - tuc la test khang dinh dung dieu ma no vua phu nhan.
    """
    entries = [ExpertEntry(f"s{i}", ["A"], ["A"], ["A"]) for i in range(10)]
    s, observed, expected = chance_corrected_agreement(entries)
    assert observed == pytest.approx(1.0)
    assert expected == pytest.approx(1.0)
    assert s == pytest.approx(0.0)


def test_expert_report_states_the_agreement_level() -> None:
    entries = [ExpertEntry("s1", ["A", "B"], ["A", "B"], ["B", "A"])]
    text = analyze_experts(entries).report()
    assert "Brennan-Prediger S" in text and "Muc do dong thuan" in text


def test_expert_report_tracks_each_expert_separately() -> None:
    entries = [
        ExpertEntry("s1", ["A", "B"], ["A", "B"], ["A", "B"], expert_id="e1"),
        ExpertEntry("s1", ["A", "B"], ["A", "B"], ["B", "A"], expert_id="e2"),
    ]
    report = analyze_experts(entries)
    assert report.per_expert == {"e1": 1.0, "e2": 0.0}


def _disjoint_entries(n: int, n_agree: int) -> list[ExpertEntry]:
    """n tinh huong, moi cai chao BA augment KHAC NHAU - giong du lieu that.

    Day chinh la hinh dang da lam hong cong thuc cu: khong tinh huong nao dung
    chung nhan voi tinh huong nao.
    """
    out = []
    for i in range(n):
        cands = [f"A{i}", f"B{i}", f"C{i}"]
        expert_top = f"A{i}" if i < n_agree else f"B{i}"
        out.append(ExpertEntry(
            f"s{i}", cands, [f"A{i}", f"B{i}", f"C{i}"],
            [expert_top] + [c for c in cands if c != expert_top],
        ))
    return out


def test_export_shuffles_candidates_so_order_does_not_leak_ranking(tmp_path) -> None:
    """Giau khoa "ranking" nhung giu thu tu thi chuyen gia van bi neo y het.

    Ban cu ghi candidates = list(scenario.ranking), nen lua chon so 1 cua
    advisor LUON nam dau danh sach. Test cu chi kiem tra khoa vang mat nen no
    xanh trong khi loi con nguyen.
    """
    scenarios = [
        Scenario(ts=f"t{i}", game_state=GameState(), ranking=["TOP", "MID", "LOW"],
                 path=tmp_path / f"s{i:02d}.json")
        for i in range(24)
    ]
    out = export_scenarios(scenarios, tmp_path / "export.json")
    payload = json.loads(out.read_text(encoding="utf-8"))

    assert all(sorted(r["candidates"]) == ["LOW", "MID", "TOP"] for r in payload)
    first_is_advisor_top = sum(1 for r in payload if r["candidates"][0] == "TOP")
    assert first_is_advisor_top < len(payload)


def test_export_shuffle_is_reproducible(tmp_path) -> None:
    """Ban xuat phai tai lap duoc, neu khong thi khong kiem chung lai duoc."""
    def build(name: str) -> list[dict]:
        scenarios = [
            Scenario(ts=f"t{i}", game_state=GameState(), ranking=["A", "B", "C"],
                     path=tmp_path / f"s{i:02d}.json")
            for i in range(8)
        ]
        out = export_scenarios(scenarios, tmp_path / name)
        return json.loads(out.read_text(encoding="utf-8"))

    a, b = build("one.json"), build("two.json")
    assert [r["candidates"] for r in a] == [r["candidates"] for r in b]
    assert all("candidate_seed" in r for r in a)


def test_expected_agreement_is_one_third_when_three_are_offered() -> None:
    """Voi 3 lua chon, doan bua trung 33% - dung con so docstring da hua."""
    _, _, expected = chance_corrected_agreement(_disjoint_entries(18, 12))
    assert expected == pytest.approx(1 / 3)


def test_agreement_is_not_inflated_by_disjoint_label_sets() -> None:
    """Hoi quy cho loi thoi phong kappa (sua 2026-09-06).

    18 tinh huong, moi cai chao 3 augment rieng, dong thuan tho 12/18 = 0.667.
    Cong thuc cu gop moi apiName vao MOT khong gian nhan chung -> p_e = 0.037
    -> kappa = 0.654 ("rat cao"). Gia tri dung: p_e = 1/3 -> S = 0.5.
    """
    s, observed, expected = chance_corrected_agreement(_disjoint_entries(18, 12))
    assert observed == pytest.approx(2 / 3)
    assert expected == pytest.approx(1 / 3)
    assert s == pytest.approx(0.5)
    assert s < 0.654


def test_verdict_is_withheld_when_the_interval_spans_bands() -> None:
    """Co mau nho: in mot bac Landis-Koch duy nhat la tu lua."""
    text = analyze_experts(_disjoint_entries(18, 12)).report()
    assert "KTC 95%" in text
    assert "CHUA KET LUAN DUOC" in text


def test_verdict_is_given_when_the_interval_is_tight() -> None:
    """Dong thuan tuyet doi tren co mau lon thi duoc phep ket luan."""
    text = analyze_experts(_disjoint_entries(200, 200)).report()
    assert "CHUA KET LUAN DUOC" not in text
    assert "rat cao" in text


def test_bootstrap_interval_brackets_the_point_estimate() -> None:
    entries = _disjoint_entries(30, 20)
    s, _, _ = chance_corrected_agreement(entries)
    lo, hi = bootstrap_ci(entries)
    assert lo <= s <= hi


# --- Gom cum theo van (SPEC 12.2, sua 2026-09-06) --------------------------


def _clustered_scenarios(with_game_id: bool) -> list[Scenario]:
    """6 van, moi van 3 quyet dinh dung CHUNG mot placement.

    Day la hinh dang that cua du lieu: `final_placement` la dai luong cua mot
    VAN, khong phai cua mot quyet dinh.
    """
    plan = [
        (1, "AAA"), (2, "AAB"), (3, "ABB"),
        (5, "BBC"), (6, "BCC"), (8, "CCC"),
    ]
    out = []
    for game, (place, picks) in enumerate(plan, start=1):
        for j, pick in enumerate(picks):
            out.append(Scenario(
                ts=f"g{game}d{j}", game_state=GameState(), ranking=["A", "B", "C"],
                player_pick=pick, final_placement=place,
                game_id=f"game-{game}" if with_game_id else None,
            ))
    return out


def test_game_id_survives_the_json_round_trip(tmp_path) -> None:
    logger = make_logger(tmp_path)
    advisor = AugmentAdvisor(features())
    ranking = advisor.rank(["ECON", "TRAIT"], GameState(stage="2-1"))
    path = logger.log(ranking, GameState(stage="2-1"), game_id="vod-abc-g3")

    assert path is not None
    reloaded = load_scenarios(tmp_path)
    assert reloaded[0].game_id == "vod-abc-g3"
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 3


def test_schema_3_records_the_reroll_advice(tmp_path) -> None:
    """Advisor tinh ra khuyen nghi doi the roi vut di thi khong danh gia duoc.

    Truong nay se rong cho den khi Track B doc duoc `player_pick` - nhung so
    do cua advisor phai duoc ghi lai TU BAY GIO, khong the ghi hoi to.
    """
    from src.decision.reroll_policy import RerollState

    logger = make_logger(tmp_path)
    advisor = AugmentAdvisor(features())
    state = GameState(stage="2-1")
    ranking = advisor.rank(["ECON", "TRAIT"], state)
    advice = advisor.advise_reroll(ranking, state, RerollState())

    path = logger.log(ranking, state, reroll=advice)
    assert path is not None
    written = json.loads(path.read_text(encoding="utf-8"))["reroll"]
    assert written["action"] in ("PICK", "REROLL")
    assert written["pool_source"]
    assert load_scenarios(tmp_path)[0].reroll == written


def test_scenario_without_reroll_advice_is_still_valid(tmp_path) -> None:
    """Chinh sach reroll khong chay (khong phai man chon, hoac no hong) thi
    ban ghi van phai hop le - `reroll` chi la None."""
    logger = make_logger(tmp_path)
    advisor = AugmentAdvisor(features())
    logger.log(advisor.rank(["ECON"], GameState(stage="2-1")), GameState(stage="2-1"))
    assert load_scenarios(tmp_path)[0].reroll is None


def test_schema_1_file_still_loads_with_no_game_id(tmp_path) -> None:
    """File cu khong co `game_id` van doc duoc - khong duoc vo khi nang schema."""
    old = {
        "schema_version": 1, "ts": "t", "frame_ref": None, "recognized": [],
        "game_state": GameState().to_dict(), "component_scores": {},
        "ranking": ["A"], "weights": {}, "player_pick": "A", "final_placement": 1,
    }
    (tmp_path / "old.json").write_text(json.dumps(old), encoding="utf-8")
    loaded = load_scenarios(tmp_path)
    assert len(loaded) == 1 and loaded[0].game_id is None


def test_analyze_counts_independent_games_not_decisions() -> None:
    """18 quyet dinh nhung chi 6 quan sat doc lap."""
    result = analyze_correlation(_clustered_scenarios(with_game_id=True))
    assert result.n == 18
    assert result.n_games == 6
    assert "6 van" in result.report()


def test_missing_game_id_is_reported_not_silently_assumed_independent() -> None:
    """Thieu nhan cum thi phai NOI, khong duoc lang le coi la doc lap."""
    result = analyze_correlation(_clustered_scenarios(with_game_id=False))
    assert result.n_games is None
    assert "CANH BAO" in result.report()


def test_block_permutation_is_not_anti_conservative() -> None:
    """Hoan vi tu do tren du lieu co cum tao ra p nho hon that.

    Cung mot dataset: hoan vi theo khoi chi co 6! cach gan placement cho van,
    con hoan vi tu do co 18! cach - phan phoi null hep gia tao.
    """
    clustered = analyze_correlation(_clustered_scenarios(with_game_id=True))
    free = analyze_correlation(_clustered_scenarios(with_game_id=False))
    assert clustered.rho == pytest.approx(free.rho)   # rho khong doi
    assert clustered.p_value > free.p_value           # chi p-value trung thuc hon
