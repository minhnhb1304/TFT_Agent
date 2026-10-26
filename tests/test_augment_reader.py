"""Test bo doc the augment va toc/he (src/vision/augment_reader.py).

TAT CA TEST DEU OFFLINE 100%:
- Khong goi mang, khong phu thuoc API key.
- Dung plain callable `call=...` de tiem du lieu gia lap.
- Khong dung unittest.mock.patch.
- ScreenRegions dung trong bo nho thong qua Region.from_pixels.
"""

from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any

import numpy as np
import pytest

from src.capture.regions import Region, ScreenRegions
from src.knowledge.name_index import NameIndex
from src.vision.augment_reader import (
    AugmentReader,
    AugmentReading,
    AugmentReadError,
    CardRead,
    compute_ahash,
    build_composite,
)

cv2 = pytest.importorskip("cv2")

ROOT = Path(__file__).resolve().parent.parent
NAME_INDEX_PATH = ROOT / "data" / "name_index.json"


def _make_regions() -> ScreenRegions:
    """Tao ScreenRegions gia lap trong bo nho, khong can doc YAML."""
    return ScreenRegions(
        screens={
            "hud": {
                "traits": Region.from_pixels(0, 258, 238, 792, 1920, 1080),
            },
            "augment_select": {
                "card_text_0": Region.from_pixels(410, 515, 690, 700, 1920, 1080),
                "card_text_1": Region.from_pixels(820, 515, 1100, 700, 1920, 1080),
                "card_text_2": Region.from_pixels(1230, 515, 1510, 700, 1920, 1080),
                "cards": Region.from_pixels(410, 515, 1510, 700, 1920, 1080),
            },
        },
        blockers={},
        meta={"set": "TFTSet18"},
    )


def _make_frame(seed: int = 42) -> np.ndarray:
    """Tao mot khung hinh synthetic 1920x1080."""
    rng = np.random.default_rng(seed)
    # Dung kich thuoc chuan de crop khong bi loi toa do
    frame = rng.integers(30, 220, size=(1080, 1920, 3), dtype=np.uint8)
    return frame


@pytest.fixture(scope="module")
def name_index() -> NameIndex:
    return NameIndex.load(NAME_INDEX_PATH)


def test_injected_call_returning_canned_json(name_index: NameIndex) -> None:
    """Kiem tra pipeline co ban voi call tiem vao tra ve JSON chuan."""
    canned = {
        "cards": [
            {"slot": 0, "title": "Bài Học Sơ Khai", "body": "Mô tả bài học sơ khai"},
            {"slot": 1, "title": "Băng Trộm II", "body": "Nhận 2 Găng Đạo Tặc"},
            {"slot": 2, "title": "Chỉ Một Con Đường II", "body": "Nhận SMCK"},
        ],
        "traits": [
            {"name": "Tàn Phá", "count": 2},
            {"name": "Hỏa Ngục", "count": 4},
        ],
    }

    reader = AugmentReader(
        regions=_make_regions(),
        names=name_index,
        call=lambda img_bytes: json.dumps(canned, ensure_ascii=False),
    )

    frame = _make_frame()
    reading = reader.read(frame)

    assert isinstance(reading, AugmentReading)
    assert reading.resolved() is True
    assert len(reading.cards) == 3

    # Kiem tra the slot 0
    c0 = reading.cards[0]
    assert c0.slot == 0
    assert c0.title == "Bài Học Sơ Khai"
    assert c0.api_names == ("DA_EarlyLearnings",)
    assert c0.confidence == 1.0
    assert "Khớp duy nhất" in c0.reason

    # Kiem tra the slot 1
    c1 = reading.cards[1]
    assert c1.slot == 1
    assert c1.title == "Băng Trộm II"
    assert c1.api_names == ("DA_BandOfThievesII",)

    # Kiem tra the slot 2
    c2 = reading.cards[2]
    assert c2.slot == 2
    assert c2.api_names == ("DA_VerticalityII",)

    # Kiem tra to_choices
    choices = reading.to_choices()
    assert len(choices) == 3
    assert choices[0].api_names == ["DA_EarlyLearnings"]
    assert choices[0].display_name == "Bài Học Sơ Khai"
    assert choices[0].ambiguous is False

    # Kiem tra api_names_flat khi khong co the map mo
    flat = reading.api_names_flat()
    assert flat == ["DA_EarlyLearnings", "DA_BandOfThievesII", "DA_VerticalityII"]

    # Kiem tra to_dict
    d = reading.to_dict()
    assert d["resolved"] is True
    assert len(d["cards"]) == 3
    assert "DA_18_Slayer" in d["traits"]


def test_ambiguous_title_returns_multiple_api_names(name_index: NameIndex) -> None:
    """Tieu de map mo phai giu du tat ca apiName va tao AugmentChoice.ambiguous = True."""
    canned = {
        "cards": [
            {"slot": 0, "title": "Búp Bê Xây Tổ", "body": "Mô tả búp bê xây tổ"},
            {"slot": 1, "title": "Băng Trộm II", "body": "Nhận 2 Găng"},
            {"slot": 2, "title": "Chỉ Một Con Đường II", "body": "Nhận SMCK"},
        ],
        "traits": [],
    }

    reader = AugmentReader(
        regions=_make_regions(),
        names=name_index,
        call=lambda img_bytes: json.dumps(canned, ensure_ascii=False),
    )

    frame = _make_frame()
    reading = reader.read(frame)

    assert reading.resolved() is True
    c0 = reading.cards[0]
    assert len(c0.api_names) == 2
    assert "DA_NestingDollsPlus" in c0.api_names
    assert "DA_NestingDollsPlusPlus" in c0.api_names
    assert "mập mờ" in c0.reason.lower()

    choices = reading.to_choices()
    assert choices[0].ambiguous is True
    assert set(choices[0].api_names) == {"DA_NestingDollsPlus", "DA_NestingDollsPlusPlus"}


def test_api_names_flat_raises_on_ambiguity(name_index: NameIndex) -> None:
    """api_names_flat phai nem AugmentReadError khi bat ky o nao bi map mo."""
    canned = {
        "cards": [
            {"slot": 0, "title": "Búp Bê Xây Tổ", "body": "Mô tả búp bê"},
            {"slot": 1, "title": "Băng Trộm II", "body": "Nhận 2 Găng"},
            {"slot": 2, "title": "Chỉ Một Con Đường II", "body": "Nhận SMCK"},
        ],
        "traits": [],
    }

    reader = AugmentReader(
        regions=_make_regions(),
        names=name_index,
        call=lambda img_bytes: json.dumps(canned, ensure_ascii=False),
    )

    reading = reader.read(_make_frame())
    with pytest.raises(AugmentReadError) as exc_info:
        reading.api_names_flat()
    assert "mập mờ" in str(exc_info.value).lower()


def test_unresolvable_title_gives_empty_api_names_and_reason(name_index: NameIndex) -> None:
    """Ten khong ton tai trong NameIndex phai de trong api_names va neu ro ly do, khong doan."""
    canned = {
        "cards": [
            {"slot": 0, "title": "Nang Cap Khong Co That ABCXYZ", "body": "Mo ta"},
            {"slot": 1, "title": "Băng Trộm II", "body": "Nhận 2 Găng"},
            {"slot": 2, "title": "Chỉ Một Con Đường II", "body": "Nhận SMCK"},
        ],
        "traits": [],
    }

    reader = AugmentReader(
        regions=_make_regions(),
        names=name_index,
        call=lambda img_bytes: json.dumps(canned, ensure_ascii=False),
    )

    reading = reader.read(_make_frame())
    assert reading.resolved() is False

    c0 = reading.cards[0]
    assert c0.api_names == ()
    assert c0.confidence == 0.0
    assert "Không tìm thấy" in c0.reason

    # Demanding choices hoac flat list khi chua resolved phai nem loi
    with pytest.raises(AugmentReadError) as exc_choices:
        reading.to_choices()
    assert "chưa xác định" in str(exc_choices.value).lower()

    with pytest.raises(AugmentReadError) as exc_flat:
        reading.api_names_flat()
    assert "chưa xác định" in str(exc_flat.value).lower()


def test_resolve_stem_fallback_when_tier_suffix_missing(name_index: NameIndex) -> None:
    """Khi ten thieu hau to tier (I/II/III), fallback sang resolve_stem voi confidence giam."""
    canned = {
        "cards": [
            {"slot": 0, "title": "Cầu Hồi Phục", "body": "Khong co hau to I hoac II"},
            {"slot": 1, "title": "Băng Trộm II", "body": "Nhận 2 Găng"},
            {"slot": 2, "title": "Bài Học Sơ Khai", "body": "Bài học"},
        ],
        "traits": [],
    }

    reader = AugmentReader(
        regions=_make_regions(),
        names=name_index,
        call=lambda img_bytes: json.dumps(canned, ensure_ascii=False),
    )

    reading = reader.read(_make_frame())
    c0 = reading.cards[0]
    assert len(c0.api_names) > 1
    assert c0.confidence == 0.7
    assert "resolve_stem" in c0.reason


def test_traits_resolved_to_api_names(name_index: NameIndex) -> None:
    """Bang toc/he phai duoc resolve sang apiName de khong gay loi board_fit."""
    canned = {
        "cards": [
            {"slot": 0, "title": "Bài Học Sơ Khai", "body": "Mô tả"},
            {"slot": 1, "title": "Băng Trộm II", "body": "Mô tả"},
            {"slot": 2, "title": "Chỉ Một Con Đường II", "body": "Mô tả"},
        ],
        "traits": [
            {"name": "Tàn Phá", "count": 2},
            {"name": "Hỏa Ngục", "count": 4},
        ],
    }

    reader = AugmentReader(
        regions=_make_regions(),
        names=name_index,
        call=lambda img_bytes: json.dumps(canned, ensure_ascii=False),
    )

    reading = reader.read(_make_frame())
    assert reading.traits == {
        "DA_18_Slayer": 2,
        "DA_18_Inferno": 4,
    }
    # Khong duoc chua chuoi tieng Viet lam khoa
    assert "Tàn Phá" not in reading.traits
    assert "Hỏa Ngục" not in reading.traits


def test_timeout_refuses_safely_without_crash(name_index: NameIndex) -> None:
    """Khi Gemini timeout, tu choi an toan, tra ve api_names rong, khong crash."""
    def slow_call(img_bytes: bytes) -> str:
        time.sleep(0.3)
        return "{}"

    reader = AugmentReader(
        regions=_make_regions(),
        names=name_index,
        timeout_s=0.05,
        call=slow_call,
    )

    reading = reader.read(_make_frame())
    assert reading.resolved() is False
    assert len(reading.cards) == 3
    for c in reading.cards:
        assert c.api_names == ()
        assert "timeout" in c.reason.lower()


def test_call_exception_refuses_safely_without_crash(name_index: NameIndex) -> None:
    """Khi call nem ngoai le (vi du mang loi / thieu key), tu choi an toan."""
    def broken_call(img_bytes: bytes) -> str:
        raise RuntimeError("Network error 503")

    reader = AugmentReader(
        regions=_make_regions(),
        names=name_index,
        call=broken_call,
    )

    reading = reader.read(_make_frame())
    assert reading.resolved() is False
    for c in reading.cards:
        assert c.api_names == ()
        assert "Network error 503" in c.reason


def test_malformed_json_refuses_safely_without_crash(name_index: NameIndex) -> None:
    """Khi Gemini tra ve JSON hong hoac khong hop le, khong crash."""
    reader = AugmentReader(
        regions=_make_regions(),
        names=name_index,
        call=lambda img_bytes: "Day khong phai la JSON {cards: hong",
    )

    reading = reader.read(_make_frame())
    assert reading.resolved() is False
    for c in reading.cards:
        assert c.api_names == ()
        assert "hỏng hoặc sai định dạng" in c.reason


def test_ahash_caching_makes_zero_calls_on_duplicate_frame(name_index: NameIndex) -> None:
    """Kiem tra co che aHash caching: lan 2 doc anh giong anh truoc thi khong goi Gemini."""
    calls = 0

    def counting_call(img_bytes: bytes) -> str:
        nonlocal calls
        calls += 1
        return json.dumps({
            "cards": [
                {"slot": 0, "title": "Bài Học Sơ Khai", "body": "Mô tả"},
                {"slot": 1, "title": "Băng Trộm II", "body": "Mô tả"},
                {"slot": 2, "title": "Chỉ Một Con Đường II", "body": "Mô tả"},
            ],
            "traits": [{"name": "Tàn Phá", "count": 2}],
        })

    reader = AugmentReader(
        regions=_make_regions(),
        names=name_index,
        call=counting_call,
    )

    frame1 = _make_frame(seed=100)
    reading1 = reader.read(frame1)
    assert calls == 1
    assert reading1.source.startswith("gemini:")
    assert reading1.resolved() is True

    # Lan 2: truyen dung frame1 -> cache hit, calls van la 1
    reading2 = reader.read(frame1)
    assert calls == 1
    assert reading2.source == "cache"
    assert reading2.resolved() is True
    assert reading2.cards[0].api_names == reading1.cards[0].api_names

    # Lan 3: truyen frame moi khac hoan toan -> cache miss, calls tang len 2
    frame2 = _make_frame(seed=999)
    reading3 = reader.read(frame2)
    assert calls == 2
    assert reading3.source.startswith("gemini:")


def test_empty_frame_raises_augment_read_error(name_index: NameIndex) -> None:
    """Khung hinh rong phai nem AugmentReadError."""
    reader = AugmentReader(
        regions=_make_regions(),
        names=name_index,
        call=lambda img: "{}",
    )
    with pytest.raises(AugmentReadError):
        reader.read(np.zeros((0, 0, 3), dtype=np.uint8))


def test_missing_required_roi_raises_at_init(name_index: NameIndex) -> None:
    """Thieu ROI can thiet trong ScreenRegions phai no ngay luc khoi tao (__init__)."""
    broken_regions = ScreenRegions(
        screens={"augment_select": {}, "hud": {}},
        blockers={},
        meta={},
    )
    with pytest.raises(AugmentReadError) as exc_info:
        AugmentReader(regions=broken_regions, names=name_index, call=lambda img: "{}")
    assert "Thiếu ROI" in str(exc_info.value)


def test_compute_ahash_and_build_composite() -> None:
    """Kiem tra cac ham tien ich tinh ahash va ghep anh composite."""
    # aHash
    img1 = np.full((100, 100, 3), 128, dtype=np.uint8)
    img2 = np.full((100, 100, 3), 128, dtype=np.uint8)
    img3 = np.zeros((100, 100, 3), dtype=np.uint8)

    h1 = compute_ahash(img1)
    h2 = compute_ahash(img2)
    h3 = compute_ahash(img3)
    assert h1 == h2
    assert isinstance(h1, int)

    # build_composite
    cards = [
        np.zeros((50, 80, 3), dtype=np.uint8),
        np.zeros((50, 80, 3), dtype=np.uint8),
        np.zeros((60, 80, 3), dtype=np.uint8),  # Chenh lech chieu cao
    ]
    traits = np.zeros((120, 60, 3), dtype=np.uint8)

    composite = build_composite(cards, traits)
    assert composite.ndim == 3
    assert composite.shape[0] >= 120
    assert composite.shape[1] >= (60 + 80 * 3)
