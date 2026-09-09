"""Test GameStateTracker (src/game_state/state_tracker.py).

Kiem tra:
- Khoi tao ban dau va never_seen
- Majority vote tren truong flickering (loc nhieu OCR)
- Carry-forward va stale khi HUD bi an (man chon augment)
- Window eviction khi day cac frame cu ra khoi cua so
- Ghep active_traits vao GameState
"""

from __future__ import annotations

import pytest

from src.game_state.models import GameState
from src.game_state.state_tracker import GameStateTracker
from src.vision.hud_reader import FieldRead, HudReading


def _make_reading(
    stage: tuple[str | None, bool] = ("3-2", True),
    gold: tuple[int | None, bool] = (50, True),
    level: tuple[int | None, bool] = (7, True),
    xp: tuple[int | None, bool] = (20, True),
    hp: tuple[int | None, bool] = (85, True),
    bar_visible: bool = True,
) -> HudReading:
    """Tao mot HudReading trong bo nho phuc vu test."""
    fields = (
        FieldRead("stage", stage[0], str(stage[0] or ""), stage[1], "hợp lệ" if stage[1] else "ẩn", 1.0),
        FieldRead("gold", gold[0], str(gold[0] or ""), gold[1], "hợp lệ" if gold[1] else "ẩn", 1.0),
        FieldRead("level", level[0], str(level[0] or ""), level[1], "hợp lệ" if level[1] else "ẩn", 1.0),
        FieldRead("xp", xp[0], str(xp[0] or ""), xp[1], "hợp lệ" if xp[1] else "ẩn", 1.0),
        FieldRead("hp", hp[0], str(hp[0] or ""), hp[1], "hợp lệ" if hp[1] else "ẩn", 1.0),
    )
    return HudReading(fields=fields, _bar_visible=bar_visible)


def test_initial_state_all_never_seen() -> None:
    tracker = GameStateTracker()
    assert set(tracker.never_seen) == {"stage", "gold", "level", "xp", "hp"}
    assert tracker.stale == ()

    state = tracker.state()
    assert isinstance(state, GameState)
    assert state.gold == 0
    assert state.level == 1
    assert state.hp == 100
    assert state.xp == 0
    assert state.stage == "1-1"


def test_single_png_augment_select_scenario() -> None:
    # Frame duy nhat o man augment_select: bottom bar bi an -> gold/level/xp absent
    tracker = GameStateTracker()
    reading = _make_reading(
        stage=("2-1", True),
        hp=(100, True),
        gold=(None, False),
        level=(None, False),
        xp=(None, False),
        bar_visible=False,
    )
    tracker.update(reading)

    # stage va hp doc duoc that su
    state = tracker.state()
    assert state.stage == "2-1"
    assert state.hp == 100
    # gold/level/xp o default va nam trong never_seen
    assert state.gold == 0
    assert state.level == 1
    assert state.xp == 0

    assert set(tracker.never_seen) == {"gold", "level", "xp"}
    assert tracker.stale == ()


def test_carry_forward_and_stale() -> None:
    tracker = GameStateTracker()

    # Frame 1: planning phase, day du cac truong
    frame_planning = _make_reading(
        stage=("3-2", True),
        gold=(42, True),
        level=(6, True),
        xp=(18, True),
        hp=(76, True),
    )
    tracker.update(frame_planning)

    assert tracker.never_seen == ()
    assert tracker.stale == ()
    assert tracker.state().gold == 42

    # Frame 2: augment select xuat hien, bottom bar bi an
    frame_augment = _make_reading(
        stage=("3-2", True),
        hp=(76, True),
        gold=(None, False),
        level=(None, False),
        xp=(None, False),
        bar_visible=False,
    )
    tracker.update(frame_augment)

    # gold, level, xp phai duoc carry-forward va danh dau la stale
    assert tracker.never_seen == ()
    assert set(tracker.stale) == {"gold", "level", "xp"}

    state = tracker.state()
    assert state.gold == 42
    assert state.level == 6
    assert state.xp == 18
    assert state.stage == "3-2"
    assert state.hp == 76


def test_majority_vote_kills_flicker() -> None:
    tracker = GameStateTracker(window=5)

    # 4 khung doc gold = 50, 1 khung giat doc nham 52
    readings = [
        _make_reading(gold=(50, True)),
        _make_reading(gold=(50, True)),
        _make_reading(gold=(52, True)),
        _make_reading(gold=(50, True)),
        _make_reading(gold=(50, True)),
    ]
    for r in readings:
        tracker.update(r)

    # Majority vote phai la 50 (4 phieu vs 1 phieu)
    assert tracker.state().gold == 50


def test_tie_breaking_favors_most_recent() -> None:
    tracker = GameStateTracker(window=2)
    tracker.update(_make_reading(gold=(10, True)))
    tracker.update(_make_reading(gold=(20, True)))

    # Tie 1 phieu cho 10 va 1 phieu cho 20 -> uu tien 20 vi gan nhat
    assert tracker.state().gold == 20


def test_window_eviction() -> None:
    tracker = GameStateTracker(window=3)

    # Dua [10, 10, 20] -> majority 10
    tracker.update(_make_reading(gold=(10, True)))
    tracker.update(_make_reading(gold=(10, True)))
    tracker.update(_make_reading(gold=(20, True)))
    assert tracker.state().gold == 10

    # Dua them [20, 20] -> lich su thanh [20, 20, 20] do maxlen=3
    tracker.update(_make_reading(gold=(20, True)))
    tracker.update(_make_reading(gold=(20, True)))
    assert tracker.state().gold == 20


def test_state_with_traits() -> None:
    tracker = GameStateTracker()
    tracker.update(_make_reading(stage=("4-1", True), gold=(35, True)))

    traits = {"TFT18_Enforcer": 4, "TFT18_Sniper": 2}
    state = tracker.state(traits=traits)

    assert state.active_traits == traits
    assert state.gold == 35
    assert state.stage == "4-1"


def test_reset() -> None:
    tracker = GameStateTracker()
    tracker.update(_make_reading(gold=(50, True)))
    assert tracker.state().gold == 50

    tracker.reset()
    assert set(tracker.never_seen) == {"stage", "gold", "level", "xp", "hp"}
    assert tracker.stale == ()
    assert tracker.state().gold == 0
