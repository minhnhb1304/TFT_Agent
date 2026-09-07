"""Test phan thuan tinh toan cua scripts/scan_vod.py.

Ba ham nay quyet dinh dataset co dung khong, va ca ba deu de sai mot cach im
lang: gop nham hai lan xuat hien thanh mot, hoac khong che khung chat truoc
khi so sanh, deu cho ra ket qua "co ve dung" ma khong bao gi.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from src.capture.regions import Region, ScreenRegions

ROOT = Path(__file__).resolve().parent.parent


def _load_scan_vod():
    """Nap script nhu mot module - scripts/ khong phai package."""
    spec = importlib.util.spec_from_file_location(
        "scan_vod", ROOT / "scripts" / "scan_vod.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scan_vod = _load_scan_vod()


# --- gop khoang ------------------------------------------------------------


def test_contiguous_hits_become_one_appearance() -> None:
    """Man chon augment hien lien vai chuc giay - do la MOT su kien."""
    times = np.arange(0.0, 20.0, 1.0)
    hits = np.zeros(20, bool)
    hits[5:12] = True
    assert scan_vod._group_runs(times, hits, gap=5.0) == [(5.0, 11.0)]


def test_hits_separated_by_a_long_gap_stay_separate() -> None:
    times = np.arange(0.0, 60.0, 1.0)
    hits = np.zeros(60, bool)
    hits[2:6] = True
    hits[40:44] = True
    runs = scan_vod._group_runs(times, hits, gap=5.0)
    assert runs == [(2.0, 5.0), (40.0, 43.0)]


def test_a_one_frame_flicker_is_still_reported() -> None:
    """Khong tu y bo diem le: bo sot thi nguoi doc bang thay thieu, con lang
    le vut di thi khong ai biet."""
    times = np.arange(0.0, 10.0, 1.0)
    hits = np.zeros(10, bool)
    hits[7] = True
    assert scan_vod._group_runs(times, hits, gap=5.0) == [(7.0, 7.0)]


def test_no_hits_is_an_empty_list_not_an_error() -> None:
    times = np.arange(0.0, 10.0, 1.0)
    assert scan_vod._group_runs(times, np.zeros(10, bool), gap=5.0) == []


# --- chuan hoa -------------------------------------------------------------


def test_znorm_makes_brightness_irrelevant() -> None:
    """Cung mot canh o hai do sang phai tuong quan bang 1.0.

    Neu khong chuan hoa, mot pha sang cua hieu ung trong game se lam diem
    tuong quan tut xuong duoi nguong va lam mat su kien.
    """
    base = np.random.default_rng(0).integers(0, 255, (1, 8, 8), dtype=np.uint8)
    dim = (base // 2).astype(np.uint8)
    a, b = scan_vod._znorm(base), scan_vod._znorm(dim)
    assert (a @ b.T).item() / a.size == pytest.approx(1.0, abs=0.02)


def test_znorm_survives_a_flat_image() -> None:
    """Man hinh den tuyen - do lech 0 - khong duoc chia cho 0."""
    flat = np.zeros((1, 8, 8), np.uint8)
    assert np.isfinite(scan_vod._znorm(flat)).all()


# --- che khung ------------------------------------------------------------


def _regions_with_chat() -> ScreenRegions:
    return ScreenRegions(
        screens={},
        blockers={"stream_chat": Region.from_pixels(0, 0, 64, 20, 128, 72)},
        meta={},
    )


def test_scrolling_chat_is_masked_before_comparing() -> None:
    """Chat cuon lien tuc la nhieu thuan tuy - hai frame cung mot man hinh
    khong duoc lech nhau chi vi co nguoi vua chat."""
    a = np.zeros((1, 72, 128), np.uint8)
    b = np.zeros((1, 72, 128), np.uint8)
    b[0, 0:20, 0:64] = 255                    # chi khac o vung chat
    regions = _regions_with_chat()
    assert np.array_equal(
        scan_vod._mask_blockers(a, regions), scan_vod._mask_blockers(b, regions)
    )


def test_masking_leaves_the_rest_of_the_frame_alone() -> None:
    thumbs = np.full((1, 72, 128), 200, np.uint8)
    masked = scan_vod._mask_blockers(thumbs, _regions_with_chat())
    assert masked[0, 30, 100] == 200          # ngoai vung che: nguyen ven
    assert masked[0, 5, 5] == 0               # trong vung che: da xoa


def test_masking_does_not_mutate_the_cached_array() -> None:
    """thumbs.npy duoc nap mot lan va dung nhieu lan - suachua tai cho la bay."""
    thumbs = np.full((1, 72, 128), 200, np.uint8)
    scan_vod._mask_blockers(thumbs, _regions_with_chat())
    assert thumbs[0, 5, 5] == 200


def test_no_regions_means_no_masking() -> None:
    thumbs = np.full((1, 72, 128), 200, np.uint8)
    assert scan_vod._mask_blockers(thumbs, None) is thumbs


# --- dinh dang -------------------------------------------------------------


def test_timestamps_are_printed_for_humans_to_scrub_to() -> None:
    assert scan_vod._hhmmss(0) == "00:00:00"
    assert scan_vod._hhmmss(11000) == "03:03:20"
    assert scan_vod._hhmmss(18224.5) == "05:03:44"


def test_exemplar_argument_parsing() -> None:
    assert scan_vod._parse_exemplar("game_end=12000") == ("game_end", 12000.0)
    with pytest.raises(Exception):
        scan_vod._parse_exemplar("thieu-dau-bang")


# --- suy ra van tu cac doan ngoai tran -------------------------------------


def test_games_are_the_gaps_between_windowed_periods() -> None:
    """Van = luc KHONG thay cua so client. Do la tin hieu on dinh nhat co."""
    runs = [(0.0, 400.0), (2600.0, 3000.0), (5400.0, 5800.0)]
    games = scan_vod._derive_games(runs, duration=8000.0, min_game_s=900.0,
                                   join_gap_s=180.0)
    assert games == [(400.0, 2600.0), (3000.0, 5400.0), (5800.0, 8000.0)]


def test_short_transition_blips_do_not_split_a_game() -> None:
    """Man chuyen canh cuoi van lam client hien ra vai giay - khong phai
    ranh gioi van moi."""
    runs = [(0.0, 400.0), (2600.0, 2606.0), (2623.0, 2625.0), (2707.0, 3200.0)]
    games = scan_vod._derive_games(runs, duration=6000.0, min_game_s=900.0,
                                   join_gap_s=180.0)
    assert games == [(400.0, 2600.0), (3200.0, 6000.0)]


def test_a_gap_too_short_to_be_a_game_is_not_reported() -> None:
    runs = [(0.0, 100.0), (200.0, 300.0)]
    assert scan_vod._derive_games(runs, 400.0, min_game_s=900.0, join_gap_s=10.0) == []


def test_video_that_is_all_game_yields_one_game() -> None:
    assert scan_vod._derive_games([], 3000.0, 900.0, 180.0) == [(0.0, 3000.0)]


def test_trailing_game_after_the_last_windowed_period_is_kept() -> None:
    """Van cuoi khong co doan sanh cho dang sau - de sot la mat mot van."""
    games = scan_vod._derive_games([(0.0, 500.0)], 4000.0, 900.0, 180.0)
    assert games == [(500.0, 4000.0)]


def test_overlapping_runs_are_merged_not_double_counted() -> None:
    runs = [(0.0, 500.0), (300.0, 800.0)]
    assert scan_vod._derive_games(runs, 3000.0, 900.0, 10.0) == [(800.0, 3000.0)]
