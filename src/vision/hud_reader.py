"""Doc cac thong so HUD tu khung hinh (SPEC 3.1, 3.2).

Pipeline cho tung truong:
crop -> hud_bar_present gate -> binarize_for_ocr -> read_digits/OCR -> validate bounds.

Khong bao gio clamp gia tri. Neu sai khoang gia tri, tra ve value=None kem reason.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal

import numpy as np

from ..capture.regions import ScreenRegions
from ..game_state.models import RE_STAGE
from .ocr_engine import DigitRead, engine, read_digits
from .preprocess import binarize_for_ocr, hud_bar_present, ocr_texts

HudField = Literal["stage", "gold", "level", "xp", "hp"]

HUD_FIELDS: tuple[HudField, ...] = ("stage", "gold", "level", "xp", "hp")
DEFAULT_REGIONS = "config/screen_regions.yaml"


class HudReadError(RuntimeError):
    """Loi cau hinh ROI hoac khung hinh khong hop le."""


@dataclass(frozen=True)
class FieldRead:
    field: HudField
    value: int | str | None
    raw_text: str
    present: bool          # Co noi dung tren man hinh de doc khong
    reason: str
    latency_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "value": self.value,
            "raw_text": self.raw_text,
            "present": self.present,
            "reason": self.reason,
            "latency_ms": round(self.latency_ms, 2),
        }


@dataclass(frozen=True)
class HudReading:
    fields: tuple[FieldRead, ...]
    _bar_visible: bool = True

    def get(self, field: HudField) -> FieldRead:
        for f in self.fields:
            if f.field == field:
                return f
        raise KeyError(f"field '{field}' khong ton tai trong HudReading")

    @property
    def bar_visible(self) -> bool:
        return self._bar_visible

    def to_dict(self) -> dict[str, Any]:
        return {
            "bar_visible": self.bar_visible,
            "fields": {f.field: f.to_dict() for f in self.fields},
        }


class HudReader:
    """Bo doc HUD tu cac crop da dinh nghia trong ScreenRegions."""

    def __init__(
        self,
        regions: ScreenRegions,
        *,
        call: Callable[[Any], Any] | None = None,
    ) -> None:
        for field in HUD_FIELDS:
            try:
                regions.region("hud", field)
            except Exception as exc:
                raise HudReadError(
                    f"thieu ROI '{field}' trong man hinh 'hud': {exc}"
                ) from exc
        self.regions = regions
        self.call = call

    @classmethod
    def load(
        cls,
        regions: str | Path | ScreenRegions = DEFAULT_REGIONS,
        *,
        call: Callable[[Any], Any] | None = None,
    ) -> HudReader:
        if isinstance(regions, ScreenRegions):
            regs = regions
        else:
            regs = ScreenRegions.load(Path(regions))
        return cls(regs, call=call)

    def read(self, frame: np.ndarray) -> HudReading:
        if frame is None or frame.size == 0 or frame.ndim != 3:
            raise HudReadError("khung hinh rong hoac khong hop le")

        # Kiem tra xem thanh HUD phia duoi (gold, level, xp) co hien thi khong
        gold_crop = self.regions.crop(frame, "hud", "gold")
        bar_vis = hud_bar_present(gold_crop)

        reads: list[FieldRead] = []

        for field in HUD_FIELDS:
            t0 = time.perf_counter()
            if field in ("gold", "level", "xp") and not bar_vis:
                latency = (time.perf_counter() - t0) * 1000.0
                reads.append(
                    FieldRead(
                        field=field,
                        value=None,
                        raw_text="",
                        present=False,
                        reason="thanh HUD không hiển thị",
                        latency_ms=latency,
                    )
                )
                continue

            crop = self.regions.crop(frame, "hud", field)

            if field == "stage":
                read = self._read_stage(crop, t0)
            elif field == "gold":
                read = self._read_gold(crop, t0)
            elif field == "level":
                read = self._read_level(crop, t0)
            elif field == "xp":
                read = self._read_xp(crop, t0)
            elif field == "hp":
                read = self._read_hp(crop, t0)
            else:
                latency = (time.perf_counter() - t0) * 1000.0
                read = FieldRead(field, None, "", False, "trường không xác định", latency)

            reads.append(read)

        return HudReading(fields=tuple(reads), _bar_visible=bar_vis)

    def _read_stage(self, crop: np.ndarray, t0: float) -> FieldRead:
        try:
            binarized = binarize_for_ocr(crop)
            ocr_fn = self.call if self.call is not None else engine()
            result = ocr_fn(binarized)
            raw_text = "".join(ocr_texts(result)).strip()
        except Exception as exc:
            latency = (time.perf_counter() - t0) * 1000.0
            return FieldRead("stage", None, "", False, f"lỗi OCR: {exc}", latency)

        latency = (time.perf_counter() - t0) * 1000.0
        if not raw_text:
            return FieldRead("stage", None, "", False, "không phát hiện ký tự", latency)

        m = RE_STAGE.match(raw_text)
        if m:
            stage_val = f"{m.group(1)}-{m.group(2)}"
            return FieldRead("stage", stage_val, raw_text, True, "hợp lệ", latency)

        return FieldRead(
            "stage",
            None,
            raw_text,
            True,
            f"giai đoạn không khớp định dạng 'X-Y': '{raw_text}'",
            latency,
        )

    def _read_gold(self, crop: np.ndarray, t0: float) -> FieldRead:
        try:
            d = read_digits(crop, call=self.call)
        except Exception as exc:
            latency = (time.perf_counter() - t0) * 1000.0
            return FieldRead("gold", None, "", False, f"lỗi OCR: {exc}", latency)

        latency = (time.perf_counter() - t0) * 1000.0
        if not d.text:
            return FieldRead("gold", None, "", False, d.reason, latency)
        if d.value is None:
            return FieldRead("gold", None, d.text, True, d.reason, latency)
        if 0 <= d.value <= 999:
            return FieldRead("gold", d.value, d.text, True, "hợp lệ", latency)
        return FieldRead("gold", None, d.text, True, f"vàng ngoài khoảng [0, 999]: {d.value}", latency)

    def _read_level(self, crop: np.ndarray, t0: float) -> FieldRead:
        try:
            d = read_digits(crop, call=self.call)
        except Exception as exc:
            latency = (time.perf_counter() - t0) * 1000.0
            return FieldRead("level", None, "", False, f"lỗi OCR: {exc}", latency)

        latency = (time.perf_counter() - t0) * 1000.0
        if not d.text:
            return FieldRead("level", None, "", False, d.reason, latency)
        if d.value is None:
            return FieldRead("level", None, d.text, True, d.reason, latency)
        if 1 <= d.value <= 10:
            return FieldRead("level", d.value, d.text, True, "hợp lệ", latency)
        return FieldRead("level", None, d.text, True, f"cấp độ ngoài khoảng [1, 10]: {d.value}", latency)

    def _read_xp(self, crop: np.ndarray, t0: float) -> FieldRead:
        try:
            d = read_digits(crop, call=self.call)
        except Exception as exc:
            latency = (time.perf_counter() - t0) * 1000.0
            return FieldRead("xp", None, "", False, f"lỗi OCR: {exc}", latency)

        latency = (time.perf_counter() - t0) * 1000.0
        if not d.text:
            return FieldRead("xp", None, "", False, d.reason, latency)
        if d.value is None:
            return FieldRead("xp", None, d.text, True, d.reason, latency)
        if 0 <= d.value <= 99:
            return FieldRead("xp", d.value, d.text, True, "hợp lệ", latency)
        return FieldRead("xp", None, d.text, True, f"kinh nghiệm ngoài khoảng [0, 99]: {d.value}", latency)

    def _read_hp(self, crop: np.ndarray, t0: float) -> FieldRead:
        try:
            d = read_digits(crop, call=self.call)
        except Exception as exc:
            latency = (time.perf_counter() - t0) * 1000.0
            return FieldRead("hp", None, "", False, f"lỗi OCR: {exc}", latency)

        latency = (time.perf_counter() - t0) * 1000.0
        if not d.text:
            return FieldRead("hp", None, "", False, d.reason, latency)
        if d.value is None:
            return FieldRead("hp", None, d.text, True, d.reason, latency)
        if 0 <= d.value <= 100:
            return FieldRead("hp", d.value, d.text, True, "hợp lệ", latency)
        return FieldRead("hp", None, d.text, True, f"máu ngoài khoảng [0, 100]: {d.value}", latency)
