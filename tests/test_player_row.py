"""Test tìm dòng của người chơi trong bảng 8 người (mốc M2).

Bảng 8 người **sắp xếp lại theo máu** sau mỗi vòng, nên một ROI cố định đọc
trúng dòng nào là chuyện may rủi — đo trên bản record 2026-09-16 thì chỉ đúng
27–36% và hai lần đọc ra máu của người khác. Dấu hiệu duy nhất đáng tin: avatar
của người chơi có **vòng tròn vàng**, bảy người còn lại vòng đỏ.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from src.vision.player_row import find_player_row, hp_box

W, H = 1920, 1080
GOLD = (40, 190, 235)      # BGR — vàng
RED = (60, 60, 210)        # BGR — đỏ của bảy người còn lại


def frame_with_rows(gold_y: int | None, red_ys: tuple[int, ...] = (200, 300, 500)) -> np.ndarray:
    frame = np.full((H, W, 3), 25, np.uint8)
    for y in red_ys:
        cv2.circle(frame, (1880, y), 22, RED, thickness=5)
    if gold_y is not None:
        cv2.circle(frame, (1880, gold_y), 24, GOLD, thickness=6)
    return frame


def test_finds_the_gold_ring_among_red_ones():
    row = find_player_row(frame_with_rows(gold_y=400))
    assert row is not None
    assert abs(row.center_y - 400) <= 4


def test_returns_none_without_a_gold_ring():
    assert find_player_row(frame_with_rows(gold_y=None)) is None


def test_ignores_gold_specks_that_are_not_rings():
    """Vệt vàng nhỏ hoặc dài ngoẵng trong panel không được nhận nhầm là vòng."""
    frame = frame_with_rows(gold_y=None)
    frame[300:304, 1800:1900] = GOLD        # một vạch ngang
    frame[500:508, 1850:1858] = GOLD        # một chấm nhỏ
    assert find_player_row(frame) is None


def test_row_moves_with_the_ring():
    """Cùng khung hình, vòng vàng ở dòng khác thì ô máu cắt ở chỗ khác."""
    high = find_player_row(frame_with_rows(gold_y=250))
    low = find_player_row(frame_with_rows(gold_y=700))
    assert high is not None and low is not None
    assert low.center_y - high.center_y > 400


def test_hp_box_is_left_of_the_avatar_and_bounded():
    frame = frame_with_rows(gold_y=400)
    row = find_player_row(frame)
    box = hp_box(frame, row)
    assert box.shape[0] > 0 and box.shape[1] > 0
    assert box.shape[0] <= 40


def test_empty_frame_is_not_a_crash():
    assert find_player_row(np.zeros((0, 0, 3), np.uint8)) is None
    assert find_player_row(None) is None


@pytest.mark.parametrize("width", (1280, 2560))
def test_works_at_other_resolutions(width: int):
    """Ngưỡng kích thước vòng phải theo tỉ lệ khung, không phải số pixel cứng."""
    height = int(width * 9 / 16)
    frame = np.full((height, width, 3), 25, np.uint8)
    scale = width / W
    cv2.circle(frame, (int(0.979 * width), int(0.37 * height)), int(24 * scale),
               GOLD, thickness=max(2, int(6 * scale)))
    row = find_player_row(frame)
    assert row is not None
    assert abs(row.center_y - int(0.37 * height)) <= 6
