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
