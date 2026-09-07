"""Test bang tier augment do NGUOI xep - tin hieu thu tu, khong phai so do.

BOI CANH. Riot da go truong `augments` khoi participant Set 18, va
tactics.tools cung tra ve rong tren 1,75 trieu van (do 2026-09-01). Thu duy
nhat con lai la y kien chuyen gia. Cho phep no vao he thong la MOT RUI RO:
mot y kien di qua du BA lop (provider -> AugmentStats -> reason string) rat
de tro thanh "so lieu" trong bao cao.

BON BAT BIEN CHONG LAI DUNG RUI RO DO:

    1. sample_n LUON 0 va is_evidence LUON False. Khong co duong nao de mot
       bang tier tu goi minh la bang chung.
    2. So DO DUOC luon thang y kien: CompositeProvider uu tien CSV.
    3. BaseScorer phai NOI RO trong reason rang day la xep hang chu quan -
       chuoi do hien thang len overlay cho nguoi dung doc.
    4. Tin hieu thu tu bi ha muc tin xuong `ordinal_trust`, khong duoc cham
       diem nhu mot con so do tu 200+ van.
"""

from __future__ import annotations

import json

import pytest

from scripts.import_augment_tiers import parse_tier_file, resolve_all
from src.decision.scoring.base import BaseScorer
from src.decision.scoring.types import ScoringConfig
from src.game_state.models import GameState
from src.knowledge.name_index import NameIndex
from src.knowledge.stats_provider import (
    AugmentStats,
    AugmentStatsProvider,
    CsvProvider,
    ExpertTierListProvider,
    NullProvider,
    default_provider,
)

TIERS = {"S": ["DA_18_Best"], "B": ["DA_18_Mid"], "D": ["DA_18_Worst"]}


def provider() -> ExpertTierListProvider:
    return ExpertTierListProvider(TIERS, source="expert-tierlist:tester/patch=18.1")


# --- Bat bien 1: khong bao gio tu goi la bang chung ------------------------


def test_tier_rows_carry_no_sample_and_are_never_evidence() -> None:
    stats = provider().get("DA_18_Best")
    assert stats is not None
    assert stats.sample_n == 0
    assert stats.is_ordinal is True
    assert stats.is_evidence is False


def test_a_forged_sample_size_still_cannot_make_it_evidence() -> None:
    """Chan duong vong: co ai do gan sample_n cao cho mot dong ordinal.

    `is_evidence` doc CA HAI dieu kien, nen mot dong ordinal van khong bao
    gio dat nguong - du sample_n co la bao nhieu.
    """
    forged = AugmentStats("DA_X", 4.0, sample_n=100_000, is_ordinal=True, tier="S")
    assert forged.is_evidence is False


def test_tier_order_is_monotone_in_placement() -> None:
    p = provider()
    best = p.get("DA_18_Best").avg_place
    mid = p.get("DA_18_Mid").avg_place
    worst = p.get("DA_18_Worst").avg_place
    assert best < mid < worst


def test_placements_stay_inside_the_scorer_normalisation_window() -> None:
    """Neu anchor nam ngoai [best_place, worst_place] thi moi bac bi ep ve bien
    va bang tier mat het do phan giai."""
    cfg = ScoringConfig.default().tune("base")
    for place in ExpertTierListProvider.TIER_PLACEMENT.values():
        assert cfg["best_place"] <= place <= cfg["worst_place"]


def test_an_unknown_tier_is_rejected_at_construction() -> None:
    with pytest.raises(ValueError) as exc:
        ExpertTierListProvider({"S+": ["DA_X"]})
    assert "S" in str(exc.value)


def test_missing_augment_returns_none_not_a_neutral_row() -> None:
    assert provider().get("DA_18_Unknown") is None


def test_provider_satisfies_the_protocol() -> None:
    assert isinstance(provider(), AugmentStatsProvider)


# --- Nap tu file ----------------------------------------------------------


def test_missing_file_gives_an_empty_provider_not_an_exception(tmp_path) -> None:
    p = ExpertTierListProvider.load(tmp_path / "khong-ton-tai.json")
    assert len(p) == 0
    assert p.get("DA_X") is None


def test_load_puts_the_rater_and_patch_into_every_row(tmp_path) -> None:
    """Mot bang tier khong ai ky ten thi khong hon gi bia ra."""
    path = tmp_path / "tiers.json"
    path.write_text(
        json.dumps(
            {
                "meta": {"rated_by": "Dishsoap", "patch": "18.1"},
                "tiers": {"S": ["DA_18_Best"]},
            }
        ),
        encoding="utf-8",
    )
    stats = ExpertTierListProvider.load(path).get("DA_18_Best")
    assert "Dishsoap" in stats.source
    assert "18.1" in stats.source


# --- Bat bien 2: so do duoc thang y kien ----------------------------------


def csv_at(tmp_path, rows: str):
    path = tmp_path / "stats.csv"
    path.write_text("api_name,avg_place,sample_n,source\n" + rows, encoding="utf-8")
    return path


def test_measured_csv_wins_over_the_tier_list(tmp_path) -> None:
    csv_path = csv_at(tmp_path, "DA_18_Best,4.90,900,riot\n")
    tiers_path = tmp_path / "tiers.json"
    tiers_path.write_text(
        json.dumps({"meta": {"rated_by": "x"}, "tiers": {"S": ["DA_18_Best", "DA_18_Only"]}}),
        encoding="utf-8",
    )

    p = default_provider(csv_path, tiers_path)
    # Co so do -> lay so do, du no NGUOC voi bang tier.
    measured = p.get("DA_18_Best")
    assert measured.source == "riot" and measured.is_ordinal is False
    # Khong co so do -> moi den luot bang tier.
    assert p.get("DA_18_Only").is_ordinal is True


def test_no_files_at_all_still_gives_a_working_null_provider(tmp_path) -> None:
    p = default_provider(tmp_path / "a.csv", tmp_path / "b.json")
    assert isinstance(p, NullProvider)
    assert p.get("DA_X") is None


def test_an_empty_tier_file_does_not_shadow_the_csv(tmp_path) -> None:
    csv_path = csv_at(tmp_path, "DA_18_Best,4.00,900,riot\n")
    tiers_path = tmp_path / "tiers.json"
    tiers_path.write_text(json.dumps({"meta": {}, "tiers": {}}), encoding="utf-8")
    p = default_provider(csv_path, tiers_path)
    assert isinstance(p, AugmentStatsProvider)
    assert p.get("DA_18_Best").source == "riot"


# --- Bat bien 3 + 4: BaseScorer noi ro va ha muc tin ----------------------


def score(stats_provider, api_name: str):
    return BaseScorer(stats_provider, ScoringConfig.default())(api_name, None, GameState())


def test_the_reason_string_says_it_is_not_a_measurement() -> None:
    result = score(provider(), "DA_18_Best")
    # Chuoi nay hien thang len overlay - no phai tu to cao minh.
    assert "KHÔNG phải số đo" in result.reason
    assert "Bậc S" in result.reason
    assert result.detail["tier"] == "S"
    assert result.detail["is_ordinal"] is True


def test_ordinal_trust_replaces_the_sample_size_shrinkage() -> None:
    """sample_n = 0 -> cong thuc theo co mau se cho trust 0 va tin hieu bien
    mat hoan toan. Nhanh ordinal phai thay bang tran co dinh tu config."""
    result = score(provider(), "DA_18_Best")
    assert result.detail["trust"] == pytest.approx(0.65)
    assert result.score > 0.5, "bac S phai keo diem len, khong duoc trung tinh"


def test_shipped_config_and_code_default_agree_on_ordinal_trust() -> None:
    """Hai cho ghi cung mot con so thi phai bang nhau.

    `ScoringConfig.default()` la cau hinh dung khi khong co file. Neu no lech
    voi `config/scoring_weights.yaml` thi test chay mot the gioi con nguoi
    dung chay mot the gioi khac - dung kieu lech da tung xay ra voi
    comp_selector, va cung kho thay y het.
    """
    shipped = ScoringConfig.load("config/scoring_weights.yaml").tune("base")
    coded = ScoringConfig.default().tune("base")
    assert shipped["ordinal_trust"] == coded["ordinal_trust"]


def test_ordinal_trust_is_below_one_on_purpose() -> None:
    """Bang tier van la mot Y KIEN, du no den tu nguoi choi rat gioi.

    Nang 0.35 -> 0.65 vi no da tro thanh nguon DUY NHAT cua w1, khong phai vi
    no da tro thanh so do. Phan co ngot chinh la cho trung thuc cua thiet ke:
    dat 1.0 la tuyen bo mot xep hang chu quan ngang mot phep do.
    """
    trust = ScoringConfig.load("config/scoring_weights.yaml").tune("base")["ordinal_trust"]
    assert 0.0 < trust < 1.0
    stats = provider().get("DA_18_Best")
    assert stats.is_ordinal is True
    assert stats.is_evidence is False
    assert stats.sample_n == 0


def test_a_bad_tier_pulls_the_score_down() -> None:
    assert score(provider(), "DA_18_Worst").score < 0.5


def test_an_opinion_moves_the_score_less_than_a_measurement(tmp_path) -> None:
    """Bat bien dinh luong cua ca thiet ke: cung mot avg_place, y kien phai
    dich diem it hon so do co 200+ van."""
    anchor = ExpertTierListProvider.TIER_PLACEMENT["S"]
    measured = CsvProvider(csv_at(tmp_path, f"DA_18_Best,{anchor},900,riot\n"))

    opinion_score = score(provider(), "DA_18_Best").score
    measured_score = score(measured, "DA_18_Best").score
    assert 0.5 < opinion_score < measured_score


def test_ordinal_trust_is_configurable_for_ablation() -> None:
    cfg = ScoringConfig.default()
    cfg.tuning["base"] = dict(cfg.tuning["base"], ordinal_trust=0.0)
    result = BaseScorer(provider(), cfg)("DA_18_Best", None, GameState())
    assert result.score == pytest.approx(0.5), "trust 0 -> tin hieu tat han"


# --- Script nap ------------------------------------------------------------


def test_parse_reads_tiers_comments_and_repeated_lines() -> None:
    parsed = parse_tier_file(
        "# ghi chu\n"
        "S: Mot, Hai\n"
        "\n"
        "s: Ba\n"
        "B: Bon\n"
    )
    assert parsed == {"S": ["Mot", "Hai", "Ba"], "B": ["Bon"]}


@pytest.mark.parametrize("bad", ["Mot, Hai", "X: Mot"])
def test_parse_rejects_malformed_input_at_the_line(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_tier_file(bad)


def index_with(mapping: dict[str, list[str]]) -> NameIndex:
    from src.knowledge.augment_catalog import normalize

    return NameIndex(by_norm={"augments": {"en": {normalize(k): v for k, v in mapping.items()}}})


def test_resolve_passes_api_names_through_untouched() -> None:
    resolved, problems = resolve_all({"S": ["DA_18_Best"]}, NameIndex.empty(), "en")
    assert resolved == {"S": ["DA_18_Best"]}
    assert problems == []


def test_resolve_reports_unknown_and_ambiguous_names_instead_of_guessing() -> None:
    index = index_with({"Ro Rang": ["DA_18_Clear"], "Map Mo": ["DA_A", "DA_B"]})
    resolved, problems = resolve_all({"S": ["Ro Rang", "Map Mo", "Khong Co"]}, index, "en")

    assert resolved == {"S": ["DA_18_Clear"]}
    assert len(problems) == 2
    assert any("Map Mo" in p for p in problems)
    assert any("Khong Co" in p for p in problems)


def test_the_same_augment_cannot_sit_in_two_tiers() -> None:
    resolved, problems = resolve_all(
        {"S": ["DA_18_Best"], "C": ["DA_18_Best"]}, NameIndex.empty(), "en"
    )
    assert resolved == {"S": ["DA_18_Best"]}
    assert any("da xuat hien o bac S" in p for p in problems)
