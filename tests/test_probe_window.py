"""Bo chon cua so cua tools/probe_environment.py.

Cac truong hop duoi day deu la tinh huong da gap that khi probe 2026-10-13
(data/live_probe/20261013_222700 va _222933).
"""

from __future__ import annotations

from tools.probe_environment import WINDOW_CANDIDATES, pick_window

TFT = {"title": "TFT  ", "class": "UnrealWindow", "w": 1920, "h": 1080}
RIOT_CLIENT = {"title": "League of Legends", "class": "RCLIENT", "w": 136, "h": 39}
OLD_CLIENT = {"title": "League of Legends (TM) Client", "class": "RiotWindowClass",
              "w": 1920, "h": 1080}
OTHER_UNREAL = {"title": "Some Other Game", "class": "UnrealWindow", "w": 1920, "h": 1080}
IME = {"title": "Default IME", "class": "IME", "w": 0, "h": 0}


def test_standalone_client_wins_over_riot_client():
    win, matched_by, _ = pick_window([RIOT_CLIENT, IME, TFT], WINDOW_CANDIDATES)
    assert win is TFT
    assert matched_by == {"title": "TFT", "class": "UnrealWindow"}


def test_game_closed_matches_nothing():
    # Truoc day FindWindow(None, None) tra ve 'Default IME' o day.
    win, matched_by, skipped = pick_window([IME], WINDOW_CANDIDATES)
    assert win is None and matched_by is None and skipped == []


def test_small_riot_client_is_skipped_and_reported():
    win, _, skipped = pick_window([RIOT_CLIENT], WINDOW_CANDIDATES)
    assert win is None
    assert skipped == [RIOT_CLIENT]


def test_other_unreal_game_is_not_tft():
    win, _, _ = pick_window([OTHER_UNREAL], WINDOW_CANDIDATES)
    assert win is None


def test_old_client_still_matches():
    win, matched_by, _ = pick_window([OLD_CLIENT], WINDOW_CANDIDATES)
    assert win is OLD_CLIENT
    assert matched_by["class"] == "RiotWindowClass"


def test_title_matches_when_class_changed():
    renamed = dict(TFT, **{"class": "SomethingNew"})
    win, matched_by, _ = pick_window([renamed], WINDOW_CANDIDATES)
    assert win is renamed
    assert matched_by == {"title": "TFT", "class": None}
