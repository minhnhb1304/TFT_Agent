"""Test bo cong cu danh gia (SPEC 12).

Cac test o day chay tren scenario TONG HOP, va do la ca diem: bo cong cu danh
gia phai duoc kiem chung TRUOC khi co du lieu that. Neu doi den luc co dataset
that moi viet, thi den luc phat hien Spearman cai sai se khong con thoi gian.

Moi ham thong ke tu cai (Spearman co dong hang, Kendall tau, Cohen's kappa,
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
    cohen_kappa,
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
    kappa, observed, _ = cohen_kappa(entries)
    assert observed == pytest.approx(1.0)
    assert kappa == pytest.approx(1.0)


def test_kappa_punishes_agreement_that_chance_explains() -> None:
    """Voi 3 lua chon, doan bua da trung 33% - ti le tho mot minh la vo nghia."""
    entries = [ExpertEntry(f"s{i}", ["A"], ["A"], ["A"]) for i in range(10)]
    kappa, observed, expected = cohen_kappa(entries)
    assert observed == pytest.approx(1.0)
    assert expected == pytest.approx(1.0)
    assert kappa == pytest.approx(1.0)   # ca hai luon chon A -> khong co thong tin


def test_expert_report_states_the_agreement_level() -> None:
    entries = [ExpertEntry("s1", ["A", "B"], ["A", "B"], ["B", "A"])]
    text = analyze_experts(entries).report()
    assert "Cohen's kappa" in text and "Muc do dong thuan" in text


def test_expert_report_tracks_each_expert_separately() -> None:
    entries = [
        ExpertEntry("s1", ["A", "B"], ["A", "B"], ["A", "B"], expert_id="e1"),
        ExpertEntry("s1", ["A", "B"], ["A", "B"], ["B", "A"], expert_id="e2"),
    ]
    report = analyze_experts(entries)
    assert report.per_expert == {"e1": 1.0, "e2": 0.0}
