"""Test bo doc HUD hud_reader (src/vision/hud_reader.py).

Kiem tra:
- Crop HUD tong hop (synthetic frame)
- Tat ca validation bounds:
  * gold: 0-999 (1000 bi tu choi)
  * level: 1-10 (11, 0 bi tu choi)
  * xp: 0-99 (100 bi tu choi)
  * hp: 0-100 (101, -1 bi tu choi)
  * stage: RE_STAGE (chuoi sai bi tu choi)
- bar_visible=False khi o gold la dia hinh / khong co thanh HUD
- Thieu ROI nem HudReadError ngay luc khoi tao
- Cac file config chua day du cac ROI can thiet
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytest

from src.capture.regions import Region, ScreenRegions
from src.vision.hud_reader import (
    FRACTION_FIELDS,
    HUD_FIELDS,
    FieldRead,
    HudReadError,
    HudReader,
    HudReading,
)

cv2 = pytest.importorskip("cv2")

ROOT = Path(__file__).resolve().parent.parent


def _make_test_regions(exclude_field: str | None = None) -> ScreenRegions:
    """Tao ScreenRegions tren bo nho kich thuoc 1920x1080."""
    boxes = {
        "stage": (768, 5, 815, 34),
        "gold": (1022, 882, 1058, 910),
        "level": (348, 882, 415, 914),
        "xp": (455, 882, 520, 914),
        "hp": (1810, 265, 1860, 305),
    }
    if exclude_field:
        boxes.pop(exclude_field, None)

    return ScreenRegions(
        screens={
            "hud": {
                name: Region.from_pixels(*px, 1920, 1080)
                for name, px in boxes.items()
            }
        },
        blockers={},
        meta={"reference_size": [1920, 1080]},
    )


def _draw_player_ring(frame: np.ndarray, center_y: int = 400) -> None:
    """Ve vong tron vang quanh avatar nguoi choi o cot ben phai.

    Tu M2, o mau doc theo DONG co vong vang chu khong theo ROI co dinh (bang 8
    nguoi sap lai theo mau). Khung test vi the phai co vong vang, neu khong bo
    doc se bao "khong thay vong vang" - dung nhu tren khung that.
    """
    cv2.circle(frame, (1880, center_y), 24, (40, 190, 235), thickness=6)


def _make_frame(bar_visible: bool = True, player_ring: bool = True) -> np.ndarray:
    """Tao frame 1920x1080 co hoac khong co thanh HUD o o gold."""
    frame = np.full((1080, 1920, 3), 120, dtype=np.uint8)  # Nen xam trung tinh
    if player_ring:
        _draw_player_ring(frame)

    if bar_visible:
        # To o gold: nen toi (den 0) va chu sang (trang 255) de thoa man hud_bar_present
        # gold box: (1022, 882, 1058, 910)
        frame[882:910, 1022:1058] = 0
        frame[890:905, 1030:1045] = 255

    return frame


def test_missing_roi_raises_at_construction() -> None:
    # Thieu field hp trong ScreenRegions phai nem HudReadError ngay
    regions = _make_test_regions(exclude_field="hp")
    with pytest.raises(HudReadError, match="thieu ROI 'hp'"):
        HudReader(regions)


def test_empty_frame_raises_hud_read_error() -> None:
    reader = HudReader(_make_test_regions(), call=lambda img: ["1"])
    with pytest.raises(HudReadError, match="khung hinh rong"):
        reader.read(np.zeros((0, 0, 3), dtype=np.uint8))

    with pytest.raises(HudReadError, match="khung hinh rong"):
        reader.read(None)  # type: ignore[arg-type]


def test_bar_visible_false_on_terrain_crop() -> None:
    # Frame khong co thanh HUD: o gold khong dat nguong tuong phan
    frame = _make_frame(bar_visible=False)
    reader = HudReader(_make_test_regions(), call=lambda img: ["10"])

    reading = reader.read(frame)
    assert reading.bar_visible is False

    # gold, level, xp phai bao present=False
    for field in ("gold", "level", "xp"):
        f_read = reading.get(field)  # type: ignore[arg-type]
        assert f_read.present is False
        assert f_read.value is None
        assert "thanh HUD không hiển thị" in f_read.reason


def test_validation_bounds_accepted_values() -> None:
    frame = _make_frame(bar_visible=True)

    # Fake OCR tra ve cac gia tri hop le cho tung field
    canned = {
        "stage": ["3-2"],
        "gold": ["50"],
        "level": ["7"],
        "xp": ["20"],
        "hp": ["85"],
    }
    # Dem luot goi theo thu tu HUD_FIELDS = ("stage", "gold", "level", "xp", "hp")
    call_idx = 0

    def fake_call(img: np.ndarray) -> list[str]:
        nonlocal call_idx
        field = HUD_FIELDS[call_idx % len(HUD_FIELDS)]
        call_idx += 1
        return canned[field]

    reader = HudReader(_make_test_regions(), call=fake_call)
    reading = reader.read(frame)

    assert reading.bar_visible is True
    assert reading.get("stage").value == "3-2"
    assert reading.get("stage").present is True
    assert reading.get("stage").reason == "hợp lệ"

    assert reading.get("gold").value == 50
    assert reading.get("gold").present is True

    assert reading.get("level").value == 7
    assert reading.get("level").present is True

    assert reading.get("xp").value == 20
    assert reading.get("xp").present is True

    assert reading.get("hp").value == 85
    assert reading.get("hp").present is True


@pytest.mark.parametrize(
    ("field", "ocr_val", "expected_err_pattern"),
    [
        ("gold", "1000", "vàng ngoài khoảng"),
        ("gold", "-1", "vàng ngoài khoảng"),
        ("level", "11", "cấp độ ngoài khoảng"),
        ("level", "0", "cấp độ ngoài khoảng"),
        ("xp", "100", "kinh nghiệm ngoài khoảng"),
        ("hp", "105", "máu ngoài khoảng"),
        ("stage", "stage 2", "giai đoạn không khớp"),
        ("stage", "4/2", "giai đoạn không khớp"),
        ("stage", "4.2", "giai đoạn không khớp"),
    ],
)
def test_validation_bounds_rejected_values(
    field: str,
    ocr_val: str,
    expected_err_pattern: str,
) -> None:
    frame = _make_frame(bar_visible=True)

    def fake_call(img: np.ndarray) -> list[str]:
        return [ocr_val]

    reader = HudReader(_make_test_regions(), call=fake_call)
    reading = reader.read(frame)

    f_read = reading.get(field)  # type: ignore[arg-type]
    assert f_read.value is None
    assert f_read.present is True
    assert expected_err_pattern in f_read.reason


def test_hud_reading_to_dict() -> None:
    field_reads = (
        FieldRead("stage", "4-2", "4-2", True, "hợp lệ", 5.2),
        FieldRead("gold", 50, "50", True, "hợp lệ", 4.1),
        FieldRead("level", 8, "Cap 8", True, "hợp lệ", 3.8),
        FieldRead("xp", 10, "10/60", True, "hợp lệ", 3.5),
        FieldRead("hp", 100, "100", True, "hợp lệ", 2.9),
    )
    reading = HudReading(fields=field_reads, _bar_visible=True)
    d = reading.to_dict()
    assert d["bar_visible"] is True
    assert d["fields"]["stage"]["value"] == "4-2"
    assert d["fields"]["gold"]["value"] == 50
    assert d["fields"]["gold"]["latency_ms"] == 4.1


@pytest.mark.parametrize(
    "cfg_path",
    [
        ROOT / "config" / "screen_regions.yaml",
        ROOT / "config" / "screen_regions.s7h-jHMpFmQ.yaml",
        ROOT / "config" / "screen_regions.5tshRxYLwv8.yaml",
    ],
)
def test_config_files_have_all_hud_regions(cfg_path: Path) -> None:
    if not cfg_path.exists():
        pytest.skip(f"{cfg_path} chua ton tai")
    regs = ScreenRegions.load(cfg_path)
    for field in HUD_FIELDS:
        if field in FRACTION_FIELDS:
            continue        # doc theo ty le khung, khong co trong config
        region = regs.region("hud", field)
        assert region.w > 0
        assert region.h > 0


# --- Thanh XP "hien_co/can" -----------------------------------------------------


def _read_xp_text(text: str):
    reader = HudReader(_make_test_regions(), call=lambda img: [text])
    reading = reader.read(_make_frame(bar_visible=True))
    return reading.get("xp"), reading.get("xp_needed")


@pytest.mark.parametrize("text", ["12/56", "12 / 56", "12|56", "12l56", r"12\56"])
def test_xp_bar_splits_current_and_needed(text: str) -> None:
    """Mau so la so cua client - OCR hay doc nham "/" nen chap nhan cac bien the."""
    xp, needed = _read_xp_text(text)
    assert (xp.value, needed.value) == (12, 56)
    assert needed.present is True


def test_xp_current_not_below_needed_is_a_misread() -> None:
    xp, needed = _read_xp_text("56/56")
    assert xp.value is None and needed.value is None
    assert "đọc nhầm" in xp.reason


def test_xp_without_denominator_keeps_current_only() -> None:
    xp, needed = _read_xp_text("20")
    assert xp.value == 20
    assert needed.value is None
    assert "mẫu số" in needed.reason


def test_hidden_bar_hides_xp_needed_too() -> None:
    reader = HudReader(_make_test_regions(), call=lambda img: ["12/56"])
    reading = reader.read(_make_frame(bar_visible=False))
    assert reading.get("xp_needed").present is False


# --- Chuỗi thắng/thua (M2) --------------------------------------------------


def _paint_streak_icon(frame: np.ndarray, hue: int) -> None:
    """Vẽ biểu tượng lửa: hue 10 ≈ cam (thắng), hue 100 ≈ xanh (thua)."""
    h, w = frame.shape[:2]
    x0, x1 = int(0.578 * w), int(0.591 * w)
    y0, y1 = int(0.812 * h), int(0.838 * h)
    patch = np.zeros((y1 - y0, x1 - x0, 3), np.uint8)
    patch[:, :] = (hue, 200, 220)
    frame[y0:y1, x0:x1] = cv2.cvtColor(patch, cv2.COLOR_HSV2BGR)


def _streak_reader(text: str) -> HudReader:
    return HudReader(_make_test_regions(), call=lambda img: [text])


def test_streak_orange_icon_is_a_win_streak() -> None:
    frame = _make_frame()
    _paint_streak_icon(frame, hue=10)
    read = _streak_reader("3").read(frame).get("streak")
    assert read.value == 3
    assert "thắng" in read.reason


def test_streak_blue_icon_is_a_loss_streak() -> None:
    """Cùng con số, khác màu biểu tượng → khác dấu. Đo trên bản record 2026-09-16."""
    frame = _make_frame()
    _paint_streak_icon(frame, hue=100)
    read = _streak_reader("1").read(frame).get("streak")
    assert read.value == -1
    assert "thua" in read.reason


def test_streak_without_icon_is_zero() -> None:
    read = _streak_reader("7").read(_make_frame()).get("streak")
    assert read.value == 0
    assert read.present is True


def test_hp_without_player_ring_is_reported_missing() -> None:
    """Không thấy vòng vàng thì bỏ trống, KHÔNG đọc ROI cố định — đó là máu người khác."""
    frame = _make_frame(player_ring=False)
    read = HudReader(_make_test_regions(), call=lambda img: ["85"]).read(frame).get("hp")
    assert read.value is None
    assert read.present is False
    assert "vòng vàng" in read.reason
