"""Test phan trinh bay cua panel augment - chay khong can man hinh.

Chinh vi cac test nay ma `build_rows()` duoc tach khoi widget Qt: logic trinh
bay (rut gon ly do, gan nhan map mo, canh bao do tin cay) la thu de sai va de
im lang, nen no phai kiem tra duoc tren may khong co desktop.
"""

from __future__ import annotations

from src.decision.augment_advisor import AugmentAdvisor, AugmentChoice
from src.game_state.models import GameState
from src.knowledge.augment_features import AugmentFeature, FeatureTable
from src.overlay.widgets.augment_panel import (
    AMBIGUOUS_LABEL,
    MAX_REASONS,
    build_reroll_line,
    build_rows,
    render_text,
)


def _advisor() -> AugmentAdvisor:
    table = FeatureTable({
        "A": AugmentFeature(api_name="A", name="Augment A", econ_value=3, category="econ"),
        "B": AugmentFeature(api_name="B", name="Augment B", tempo="scaling"),
    })
    return AugmentAdvisor(table)


def test_rows_follow_ranking_order() -> None:
    ranking = _advisor().rank(["A", "B"], GameState(stage="2-1", hp=90))
    rows = build_rows(ranking)
    assert [r.rank for r in rows] == [1, 2]
    assert [r.name for r in rows] == [e.name for e in ranking.entries]


def test_reasons_are_capped() -> None:
    """Man chon augment chi co ~30 giay - khong duoc do het ly do ra man hinh."""
    ranking = _advisor().rank(["A"], GameState(stage="2-1", hp=20))
    assert len(build_rows(ranking)[0].reasons) <= MAX_REASONS


def test_ambiguous_pair_is_labelled() -> None:
    ranking = _advisor().rank([AugmentChoice(["A", "B"])], GameState())
    assert all(AMBIGUOUS_LABEL in r.badges for r in build_rows(ranking))


def test_low_recognition_confidence_is_surfaced() -> None:
    """Xep hang tu tin tren mot ket qua nhan dang yeu la kieu hong te nhat."""
    ranking = _advisor().rank([AugmentChoice(["A"], confidence=0.41)], GameState())
    row = build_rows(ranking)[0]
    assert row.low_confidence
    assert any("41%" in b for b in row.badges)


def test_high_confidence_has_no_badge() -> None:
    ranking = _advisor().rank([AugmentChoice(["A"], confidence=0.99)], GameState())
    assert build_rows(ranking)[0].badges == []


def test_bar_ratio_is_bounded() -> None:
    ranking = _advisor().rank(["A", "B"], GameState())
    assert all(0.0 <= r.bar_ratio <= 1.0 for r in build_rows(ranking))


def test_render_text_contains_name_and_score() -> None:
    ranking = _advisor().rank(["A"], GameState(stage="2-1"))
    text = render_text(build_rows(ranking))
    assert "Augment A" in text
    assert f"{ranking.entries[0].total:.3f}" in text


# --- Dong hanh dong cho khuyen nghi doi the (SPEC 3.5.5) --------------------


def _advice(**kwargs):
    from src.decision.reroll_policy import RerollAdvice

    base = dict(
        action="REROLL",
        target_slot=0,
        fallback_slot=2,
        expected_gain=0.0123,
        reason="ly do",
        threshold=0.6,
        depletion_cost=0.0,
        pool_source="test",
        pool_n=100,
        evidence="measured",
    )
    base.update(kwargs)
    return RerollAdvice(**base)


def test_reroll_line_names_the_slot_to_click_in_human_numbering() -> None:
    """O danh so tu 0 trong code, tu 1 tren man hinh. Nhieu nhat mot cho lech."""
    line = build_reroll_line(_advice(target_slot=0, fallback_slot=2))
    assert "ô 1" in line
    assert "giữ ô 3" in line


def test_reroll_line_shows_the_action_word_first() -> None:
    assert build_reroll_line(_advice(action="REROLL")).startswith("▶ ĐỔI")
    assert build_reroll_line(_advice(action="PICK")).startswith("▶ CHỌN")


def test_reroll_line_marks_a_recommendation_built_on_uncalibrated_data() -> None:
    """Ha giong khuyen nghi, KHONG giau khuyen nghi."""
    weak = build_reroll_line(_advice(evidence="uncalibrated"))
    strong = build_reroll_line(_advice(evidence="measured"))
    assert weak.endswith("?")
    assert not strong.endswith("?")
    assert "ĐỔI ô 1" in weak  # hanh dong van con nguyen


def test_panel_without_advice_renders_exactly_as_before() -> None:
    """Hoi quy: moi cho goi cu khong truyen `advice` phai khong doi mot ky tu."""
    ranking = _advisor().rank(["A", "B"], GameState(stage="2-1", hp=90))
    rows = build_rows(ranking)
    assert render_text(rows, None) == render_text(rows)


def test_advice_line_sits_above_the_ranking() -> None:
    rows = build_rows(_advisor().rank(["A", "B"], GameState(stage="2-1", hp=90)))
    text = render_text(rows, _advice())
    assert text.splitlines()[0].startswith("▶")
