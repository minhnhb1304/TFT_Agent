"""Test cach chon moc frame trong scripts/extract_frames.py.

Ham nay quyet dinh anh trich ra co dung duoc khong. Do that tren VOD YBY1:
man chon augment mat vai giay lat bai, va nguoi choi chuyen nghiep bam rat
nhanh - co su kien chi keo dai 1 giay. Lay mot moc duy nhat o giua khoang la
de trung dung pha lat bai, ra anh khong gan nhan duoc.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "extract_frames", ROOT / "scripts" / "extract_frames.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


extract_frames = _load()
_sample_times = extract_frames._sample_times


def test_one_sample_lands_in_the_middle() -> None:
    assert _sample_times(10.0, 20.0, 1) == [15.0]


def test_samples_are_spread_and_avoid_both_edges() -> None:
    """Khung dau con dang mo dan, khung cuoi da bat dau dong."""
    got = _sample_times(0.0, 10.0, 4)
    assert got == [2.0, 4.0, 6.0, 8.0]
    assert all(0.0 < t < 10.0 for t in got)


def test_sample_from_skips_the_flip_animation() -> None:
    """Chi lay nua sau cua khoang - luc ba the bai da ngua."""
    got = _sample_times(0.0, 10.0, 2, sample_from=0.5)
    assert all(t >= 5.0 for t in got)


def test_zero_length_event_still_yields_the_requested_count() -> None:
    """Su kien 1 giay van xuat hien trong timeline; khong duoc tra rong."""
    assert _sample_times(7.0, 7.0, 3) == [7.0, 7.0, 7.0]


def test_sample_from_is_clamped_so_the_window_never_collapses() -> None:
    got = _sample_times(0.0, 10.0, 2, sample_from=5.0)
    assert len(got) == 2
    assert all(0.0 <= t <= 10.0 for t in got)


def test_more_samples_cover_a_short_event_more_densely() -> None:
    """Cach doi pho voi pha lat bai: lay day hon, roi de nguoi chon.

    Do that: 5 frame moi su kien bat duoc anh 'bai da ngua' o ca 18/18 su kien,
    trong khi 2 frame thi truot vai cai.
    """
    sparse = _sample_times(0.0, 5.0, 2)
    dense = _sample_times(0.0, 5.0, 5)
    assert len(dense) > len(sparse)
    gaps = [b - a for a, b in zip(dense, dense[1:])]
    assert max(gaps) < 5.0 / 2


def test_filename_stamp_is_sortable_and_traceable() -> None:
    assert extract_frames._hhmmss(0) == "000000"
    assert extract_frames._hhmmss(3356.5) == "005556"
    assert extract_frames._hhmmss(11000) == "030320"


def test_filename_stamps_sort_in_video_order() -> None:
    stamps = [extract_frames._hhmmss(t) for t in (59, 61, 3599, 3601, 11000)]
    assert stamps == sorted(stamps)


@pytest.mark.parametrize("count", [1, 2, 3, 5, 8])
def test_requested_count_is_always_honoured(count: int) -> None:
    assert len(_sample_times(100.0, 134.0, count)) == count


# --- Hoi quy: duong dan ra ngoai goc repo (2026-09-07) --------------------


def test_paths_under_the_repo_are_recorded_relative() -> None:
    got = extract_frames._rel(ROOT / "data" / "frames" / "a.png")
    assert got == "data/frames/a.png"


def test_a_path_outside_the_repo_does_not_crash_the_run() -> None:
    """HOI QUY: `Path.relative_to` NEM khi duong dan khong nam duoi goc.

    `--out-dir` tro sang o dia khac la chuyen binh thuong; truoc day no lam
    ca lan trich chet ngay o anh dau tien, sau khi da ghi file ra dia.
    """
    outside = Path("C:/somewhere/else/a.png") if sys.platform == "win32"         else Path("/somewhere/else/a.png")
    got = extract_frames._rel(outside)
    assert "a.png" in got
    assert "\\" not in got


def test_rel_normalises_separators() -> None:
    assert "\\" not in extract_frames._rel(ROOT / "data" / "x" / "y.png")


# --- Hoi quy: kiem tham so ------------------------------------------------


def test_zero_frames_per_event_is_rejected() -> None:
    with pytest.raises(SystemExit):
        extract_frames.main(["--video", "x.mp4", "--per-event", "0"])


def test_sample_from_outside_the_unit_interval_is_rejected() -> None:
    for bad in ("1.0", "-0.1", "2"):
        with pytest.raises(SystemExit):
            extract_frames.main(["--video", "x.mp4", "--sample-from", bad])
