"""Bo nhan dang chu so bang RapidOCR (SPEC 3.2).

Lazy singleton cho RapidOCR de tranh chi phi khoi tao per-frame.
Dau ra OCR luon duoc boc qua `binarize_for_ocr` va `ocr_texts`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from .preprocess import DEFAULT_OCR_SCALE, binarize_for_ocr, ocr_texts


class OcrError(RuntimeError):
    """Loi trong qua trinh nhan dang OCR hoac cau hinh engine."""


@dataclass(frozen=True)
class DigitRead:
    text: str            # Chuoi tho ghep tu OCR, giu nguyen de truy vet
    value: int | None    # So nguyen da parse; None neu khong parse duoc hoac loi
    reason: str          # Ly do (tieng Viet co dau neu nguoi dung xem)


_ENGINE: Any | None = None


def engine() -> Any:
    """Process-wide lazy singleton. Tao mot lan, khong bao gio tren frame path."""
    global _ENGINE
    if _ENGINE is None:
        try:
            from rapidocr import RapidOCR
            _ENGINE = RapidOCR()
        except Exception as exc:
            raise OcrError(f"khong the khoi tao RapidOCR: {exc}") from exc
    return _ENGINE


def read_digits(
    crop: np.ndarray,
    *,
    scale: int = DEFAULT_OCR_SCALE,
    call: Callable[[Any], Any] | None = None,
) -> DigitRead:
    """Tien xu ly crop va doc chu so qua OCR.

    Tham so `call` la injection seam cho test de khong can khoi tao engine that.
    """
    if crop is None or crop.size == 0 or crop.shape[0] < 1 or crop.shape[1] < 1:
        raise OcrError("crop rỗng - kiểm tra lại tọa độ ROI")

    binarized = binarize_for_ocr(crop, scale=scale)

    ocr_fn = call if call is not None else engine()
    try:
        result = ocr_fn(binarized)
    except Exception as exc:
        raise OcrError(f"loi khi goi OCR: {exc}") from exc

    texts = ocr_texts(result)
    raw_text = "".join(texts).strip()

    if not raw_text:
        return DigitRead(text="", value=None, reason="không phát hiện ký tự")

    # Tim chuoi chu so dau tien (ho tro ca so am de bat loi ngoai khoang)
    match = re.search(r"-?\d+", raw_text)
    if match:
        val = int(match.group())
        return DigitRead(text=raw_text, value=val, reason="hợp lệ")

    return DigitRead(
        text=raw_text,
        value=None,
        reason=f"chuỗi không chứa chữ số: '{raw_text}'",
    )
