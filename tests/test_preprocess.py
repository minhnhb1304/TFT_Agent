"""Test tien xu ly anh + doc dau ra OCR (src/vision/preprocess.py).

`ocr_texts` la lop dem truoc mot thu vien co schema DOI GIUA CAC BAN. Neu no
doc sai kieu, ket quả khong phai loi ma la RONG - va mot ti le nhan dien tut
xuong 0% ma khong co ngoai le nao thi rat lau moi bi phat hien. Vi the o day
liet ke tat ca cac dang da biet, ke ca dang cua ban cu.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from src.vision.preprocess import (
    binarize_for_ocr,
    has_digit,
    hud_bar_present,
    ocr_join,
    ocr_texts,
)


# --- doc dau ra OCR -------------------------------------------------------


@dataclass
class _V3Output:
    """Dang cua rapidocr 3.x: doi tuong co .txts (tuple hoac None)."""
    txts: object


def test_reads_the_current_v3_object() -> None:
    assert ocr_texts(_V3Output(txts=("18",))) == ("18",)
    assert ocr_texts(_V3Output(txts=("Cap", "7"))) == ("Cap", "7")


def test_empty_v3_output_has_txts_none_not_empty_tuple() -> None:
    """Do that: RapidOCR tra `.txts = None` khi khong thay chu.

    Va `bool(output)` cung la False - nen `if out:` bo qua ca truong hop hop le.
    """
    assert ocr_texts(_V3Output(txts=None)) == ()


def test_reads_the_legacy_tuple_form() -> None:
    """rapidocr 1.x/2.x tra `(result, elapse)` voi result la [box, text, score]."""
    legacy = ([[[0, 0, 1, 1], "18", 0.99], [[2, 2, 3, 3], "vang", 0.95]], 0.31)
    assert ocr_texts(legacy) == ("18", "vang")


def test_reads_a_bare_list_of_rows() -> None:
    assert ocr_texts([[[0, 0], "4-6", 0.9]]) == ("4-6",)


def test_reads_a_list_of_plain_strings() -> None:
    assert ocr_texts(["10/60"]) == ("10/60",)


def test_reads_dict_rows() -> None:
    assert ocr_texts([{"text": "18", "score": 0.9}]) == ("18",)


def test_reads_a_dict_result() -> None:
    assert ocr_texts({"txts": ["18", "vang"]}) == ("18", "vang")


def test_none_and_empty_are_not_errors() -> None:
    assert ocr_texts(None) == ()
    assert ocr_texts([]) == ()
    assert ocr_texts(()) == ()


def test_unknown_shape_degrades_to_empty_instead_of_raising() -> None:
    """Thu vien doi schema thi ta mat du lieu - nhung khong duoc lam sap ca lan quet."""
    assert ocr_texts(object()) == ()
    assert ocr_texts(12345) == ()


def test_single_string_attribute_is_wrapped() -> None:
    assert ocr_texts(_V3Output(txts="18")) == ("18",)


def test_join_and_digit_detection() -> None:
    out = _V3Output(txts=("Cap", "7"))
    assert ocr_join(out) == "Cap7"
    assert ocr_join(out, sep=" ") == "Cap 7"
    assert has_digit(out) is True
    assert has_digit(_V3Output(txts=("Cap",))) is False
    assert has_digit(None) is False


def test_legacy_form_also_finds_digits() -> None:
    """Bay chinh: neu `ocr_texts` khong hieu dang cu thi day tra False im lang."""
    assert has_digit(([[[0, 0], "18", 0.9]], 0.2)) is True


# --- nhi phan hoa ---------------------------------------------------------


def _gold_like(w: int = 36, h: int = 28) -> np.ndarray:
    """Nen toi + vai chu so gan trang - giong o `gold` that."""
    img = np.full((h, w, 3), 30, np.uint8)
    img[8:20, 6:12] = 235
    img[8:20, 18:24] = 235
    return img


def test_binarize_returns_bgr_scaled_up() -> None:
    out = binarize_for_ocr(_gold_like(), scale=6)
    assert out.shape == (28 * 6, 36 * 6, 3)
    assert out.dtype == np.uint8


def test_binarize_yields_only_two_levels() -> None:
    """Otsu la cai bien `stage` tu truot thanh 3/3 - phai that su nhi phan."""
    out = binarize_for_ocr(_gold_like(), scale=1)
    assert set(np.unique(out)).issubset({0, 255})


def test_binarize_accepts_grayscale_input() -> None:
    gray = np.full((20, 20), 40, np.uint8)
    gray[5:15, 5:15] = 220
    assert binarize_for_ocr(gray, scale=2).shape == (40, 40, 3)


def test_binarize_survives_a_flat_crop() -> None:
    """Anh mot mau -> normalize chia cho 0 neu khong can than."""
    out = binarize_for_ocr(np.zeros((10, 10, 3), np.uint8), scale=1)
    assert np.isfinite(out).all()


def test_empty_crop_fails_loudly_at_the_right_place() -> None:
    """ROI lam tron ve 0 pixel: bao o day, khong de cv2 nem o tan sau."""
    with pytest.raises(ValueError, match="rong"):
        binarize_for_ocr(np.zeros((0, 0, 3), np.uint8))
    with pytest.raises(ValueError, match="rong"):
        binarize_for_ocr(None)


def test_scale_below_one_is_rejected() -> None:
    with pytest.raises(ValueError, match="scale"):
        binarize_for_ocr(_gold_like(), scale=0)


# --- thanh HUD co hien khong ---------------------------------------------


def test_hud_present_on_a_gold_like_crop() -> None:
    assert hud_bar_present(_gold_like()) is True


def test_hud_absent_on_terrain() -> None:
    """12/12 khung "truot" tren VOD that deu la co nay: khong co gi de doc."""
    rng = np.random.default_rng(0)
    terrain = rng.integers(95, 190, (28, 36, 3), dtype=np.uint8)
    assert hud_bar_present(terrain) is False


def test_hud_absent_on_an_all_dark_crop() -> None:
    """Toi khong thoi chua du - phai co CA chu sang."""
    assert hud_bar_present(np.zeros((28, 36, 3), np.uint8)) is False


def test_hud_absent_on_an_all_bright_crop() -> None:
    assert hud_bar_present(np.full((28, 36, 3), 255, np.uint8)) is False


def test_hud_present_is_false_on_empty_not_an_exception() -> None:
    assert hud_bar_present(np.zeros((0, 0, 3), np.uint8)) is False
    assert hud_bar_present(None) is False
