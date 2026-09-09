"""Test bo nhan dang chu so ocr_engine (src/vision/ocr_engine.py).

Kiem tra:
- Injected call seam
- Parse cac dang chu so
- Crop rong nem OcrError
- Singleton engine chi khoi tao mot lan
"""

from __future__ import annotations

import numpy as np
import pytest

from src.vision.ocr_engine import DigitRead, OcrError, engine, read_digits

cv2 = pytest.importorskip("cv2")


def _dummy_crop() -> np.ndarray:
    """Tao mot anh crop hop le 30x30 co nen den chu trang."""
    img = np.zeros((30, 30, 3), dtype=np.uint8)
    cv2.putText(img, "42", (2, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return img


def test_read_digits_with_injected_call() -> None:
    # Test seam: truyen call tra ve RapidOCR tuple schema
    crop = _dummy_crop()
    called = False

    def fake_call(img: np.ndarray) -> list[str]:
        nonlocal called
        called = True
        return ["42"]

    res = read_digits(crop, call=fake_call)
    assert called is True
    assert isinstance(res, DigitRead)
    assert res.value == 42
    assert res.text == "42"
    assert res.reason == "hợp lệ"


@pytest.mark.parametrize(
    ("ocr_output", "expected_val", "expected_text"),
    [
        (["18"], 18, "18"),
        ([" 100 "], 100, "100"),
        (["Cap 7"], 7, "Cap 7"),
        (["10/60"], 10, "10/60"),
        (["0"], 0, "0"),
        (["999"], 999, "999"),
    ],
)
def test_read_digits_parsing_variants(
    ocr_output: list[str],
    expected_val: int,
    expected_text: str,
) -> None:
    crop = _dummy_crop()
    res = read_digits(crop, call=lambda img: ocr_output)
    assert res.value == expected_val
    assert res.text == expected_text
    assert res.reason == "hợp lệ"


def test_read_digits_no_digits() -> None:
    crop = _dummy_crop()
    res = read_digits(crop, call=lambda img: ["abc"])
    assert res.value is None
    assert res.text == "abc"
    assert "chuỗi không chứa chữ số" in res.reason


def test_read_digits_empty_output() -> None:
    crop = _dummy_crop()
    res = read_digits(crop, call=lambda img: [])
    assert res.value is None
    assert res.text == ""
    assert "không phát hiện ký tự" in res.reason


@pytest.mark.parametrize(
    "bad_crop",
    [
        np.zeros((0, 0, 3), dtype=np.uint8),
        np.zeros((10, 0, 3), dtype=np.uint8),
        np.zeros((0, 10, 3), dtype=np.uint8),
        None,
    ],
)
def test_read_digits_empty_crop_raises(bad_crop: np.ndarray | None) -> None:
    with pytest.raises(OcrError, match="crop rỗng"):
        read_digits(bad_crop, call=lambda img: ["1"])  # type: ignore[arg-type]


def test_read_digits_call_exception_raises_ocr_error() -> None:
    crop = _dummy_crop()

    def buggy_call(img: np.ndarray) -> Any:
        raise ValueError("loi runtime bat ngo")

    with pytest.raises(OcrError, match="loi khi goi OCR"):
        read_digits(crop, call=buggy_call)


def test_singleton_engine_reused() -> None:
    import src.vision.ocr_engine as mod

    old = mod._ENGINE
    try:
        e1 = mod.engine()
        e2 = mod.engine()
        assert e1 is e2
    finally:
        mod._ENGINE = old


def test_singleton_engine_cached() -> None:
    import src.vision.ocr_engine as mod

    sentinel = object()
    old = mod._ENGINE
    try:
        mod._ENGINE = sentinel
        assert mod.engine() is sentinel
    finally:
        mod._ENGINE = old
