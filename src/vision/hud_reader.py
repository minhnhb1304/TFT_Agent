"""Doc cac thong so HUD tu khung hinh (SPEC 3.1, 3.2).

Pipeline cho tung truong:
crop -> hud_bar_present gate -> binarize_for_ocr -> read_digits/OCR -> validate bounds.

Khong bao gio clamp gia tri. Neu sai khoang gia tri, tra ve value=None kem reason.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal

import numpy as np

from ..capture.regions import ScreenRegions
from ..game_state.models import RE_STAGE
from .ocr_engine import DigitRead, engine, read_digits
from .preprocess import binarize_for_ocr, brighten_dimmed, hud_bar_present, ocr_texts

HudField = Literal["stage", "gold", "level", "xp", "xp_needed", "hp", "streak"]

# Truong co ROI rieng - moi truong mot lan goi OCR.
HUD_FIELDS: tuple[HudField, ...] = ("stage", "gold", "level", "xp", "hp", "streak")

# Chuoi thang/thua: SO nam ben phai bieu tuong lua, DAU nam o MAU bieu tuong -
# lua cam la thang lien tiep, lua xanh la thua lien tiep. Do tren ban record
# 2026-09-16: hue 8-22 khi thang, 94-105 khi thua, khong bieu tuong khi chuoi = 0.
STREAK_NUMBER = (0.590, 0.612, 0.809, 0.841)      # x0, x1, y0, y1 theo ty le khung
STREAK_ICON = (0.578, 0.591, 0.812, 0.838)
STREAK_WIN_HUE = 40
STREAK_MIN_ICON_PX = 20

# Truong doc theo ty le khung thay vi ROI trong config (them sau khi config da chot).
FRACTION_FIELDS: tuple[HudField, ...] = ("streak",)

# Cache theo TUNG O: mot lan doc day du la ~3 s (7 lan OCR), trong khi vang/cap/
# XP hiem khi doi giua hai lan doc. So sanh anh thu nho cua chinh o do; giong
# thi dung lai ket qua cu. Do duoc tren ban record: cat phan lon cong doc.
CACHE_THUMB = (24, 10)
CACHE_TOL = 1.5
# `xp_needed` KHONG co ROI: thanh XP hien "hien_co/can_de_len_cap" trong CUNG
# mot o, nen ca hai tach ra tu mot lan doc cua ROI `xp`.
DERIVED_FIELDS: tuple[HudField, ...] = ("xp_needed",)
DEFAULT_REGIONS = "config/screen_regions.yaml"

# "12/56". OCR hay doc nham dau "/" thanh "|", "\", "l" hoac "I".
RE_XP = re.compile(r"(\d{1,2})\s*[/|\\lI]\s*(\d{1,3})")
XP_NEEDED_RANGE = (2, 99)


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
        found = self.find(field)
        if found is None:
            raise KeyError(f"field '{field}' khong ton tai trong HudReading")
        return found

    def find(self, field: HudField) -> FieldRead | None:
        return next((f for f in self.fields if f.field == field), None)

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
            if field in FRACTION_FIELDS:
                continue        # doc theo ty le khung, khong can ROI trong cau hinh
            try:
                regions.region("hud", field)
            except Exception as exc:
                raise HudReadError(
                    f"thieu ROI '{field}' trong man hinh 'hud': {exc}"
                ) from exc
        self.regions = regions
        self.call = call
        self._cache: dict[str, tuple[Any, FieldRead]] = {}

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
        # Panel trong game (Team Planner) phu mot lop toi len thanh HUD: chu con
        # nguyen, chi mo. Keo sang roi kiem lai truoc khi ket luan "khong co gi".
        dimmed = not bar_vis and hud_bar_present(brighten_dimmed(gold_crop))
        bar_vis = bar_vis or dimmed

        reads: list[FieldRead] = []

        for field in HUD_FIELDS:
            t0 = time.perf_counter()
            if field in ("gold", "level", "xp") and not bar_vis:
                latency = (time.perf_counter() - t0) * 1000.0
                hidden = [field, "xp_needed"] if field == "xp" else [field]
                reads.extend(
                    FieldRead(
                        field=name,
                        value=None,
                        raw_text="",
                        present=False,
                        reason="thanh HUD không hiển thị",
                        latency_ms=latency,
                    )
                    for name in hidden
                )
                continue

            crop = None if field == "streak" else self.regions.crop(frame, "hud", field)
            if dimmed and crop is not None:
                crop = brighten_dimmed(crop)

            if field == "streak":
                reads.append(self._cached(field, self._streak_crop(frame),
                                          lambda: self._read_streak(frame, t0)))
                continue
            if field == "hp":
                reads.append(self._read_hp_row(frame, crop, t0))
                continue
            cached = self._cached(field, crop, lambda: None)
            if cached is not None:
                reads.append(cached)
                continue
            if field == "stage":
                read = self._read_stage(crop, t0)
            elif field == "gold":
                read = self._read_gold(crop, t0)
            elif field == "level":
                read = self._read_level(crop, t0)
            elif field == "xp":
                reads.extend(self._read_xp(crop, t0))
                continue
            else:
                latency = (time.perf_counter() - t0) * 1000.0
                read = FieldRead(field, None, "", False, "trường không xác định", latency)

            reads.append(self._remember(field, crop, read) if field != "xp" else read)

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

    def _read_xp(self, crop: np.ndarray, t0: float) -> tuple[FieldRead, FieldRead]:
        """Thanh XP "hien_co/can" -> (xp, xp_needed).

        Mau so la so cua CLIENT, khong phai cua bang XP ben thu ba - no vua cho
        phep tinh chinh xac, vua kiem chung duoc bang XP.
        """
        try:
            d = read_digits(crop, call=self.call)
        except Exception as exc:
            latency = (time.perf_counter() - t0) * 1000.0
            return (
                FieldRead("xp", None, "", False, f"lỗi OCR: {exc}", latency),
                FieldRead("xp_needed", None, "", False, f"lỗi OCR: {exc}", latency),
            )

        latency = (time.perf_counter() - t0) * 1000.0
        if not d.text:
            return (
                FieldRead("xp", None, "", False, d.reason, latency),
                FieldRead("xp_needed", None, "", False, d.reason, latency),
            )

        pair = RE_XP.search(d.text)
        if pair:
            current, needed = int(pair.group(1)), int(pair.group(2))
            low, high = XP_NEEDED_RANGE
            if not low <= needed <= high:
                reason = f"XP cần ngoài khoảng [{low}, {high}]: {needed}"
            elif current >= needed:
                reason = f"XP hiện có {current} ≥ XP cần {needed} — đọc nhầm"
            else:
                return (
                    FieldRead("xp", current, d.text, True, "hợp lệ", latency),
                    FieldRead("xp_needed", needed, d.text, True, "hợp lệ", latency),
                )
            return (
                FieldRead("xp", None, d.text, True, reason, latency),
                FieldRead("xp_needed", None, d.text, True, reason, latency),
            )

        missing = FieldRead("xp_needed", None, d.text, True, f"không thấy mẫu số trong '{d.text}'", latency)
        if d.value is None:
            return FieldRead("xp", None, d.text, True, d.reason, latency), missing
        if 0 <= d.value <= 99:
            return FieldRead("xp", d.value, d.text, True, "hợp lệ", latency), missing
        return (
            FieldRead("xp", None, d.text, True, f"kinh nghiệm ngoài khoảng [0, 99]: {d.value}", latency),
            missing,
        )

    # -- cache theo tung o -------------------------------------------------

    def _thumb(self, crop: np.ndarray) -> Any:
        import cv2  # noqa: PLC0415

        if crop is None or crop.size == 0:
            return None
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
        return cv2.resize(gray, CACHE_THUMB, interpolation=cv2.INTER_AREA).astype("float32")

    def _cached(self, field: str, crop: np.ndarray, compute) -> FieldRead | None:
        """Tra ket qua cu neu o nay khong doi; None neu chua co gi de dung."""
        thumb = self._thumb(crop)
        previous = self._cache.get(field)
        if previous is not None and thumb is not None:
            old_thumb, read = previous
            if old_thumb is not None and float(np.mean(np.abs(old_thumb - thumb))) < CACHE_TOL:
                return read
        value = compute()
        if value is not None:
            self._cache[field] = (thumb, value)
        return value

    def _remember(self, field: str, crop: np.ndarray, read: FieldRead) -> FieldRead:
        self._cache[field] = (self._thumb(crop), read)
        return read

    def _streak_crop(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        nx0, nx1, ny0, ny1 = STREAK_NUMBER
        return frame[int(ny0 * h):int(ny1 * h), int(nx0 * w):int(nx1 * w)]

    def _read_hp_row(self, frame: np.ndarray, _static_crop: np.ndarray, t0: float) -> FieldRead:
        """Doc mau cua NGUOI CHOI, tim dong bang vong tron vang quanh avatar.

        Bang 8 nguoi sap lai theo mau sau moi vong, nen ROI co dinh doc trung
        nguoi khac (do duoc: chi dung 27-36% so lan). Khong thay vong vang thi
        lui ve ROI tinh va NOI RO la da lui.
        """
        from .player_row import find_player_row, hp_box  # noqa: PLC0415

        row = find_player_row(frame, self.regions)
        if row is None:
            # KHONG lui ve ROI co dinh: o do la mau cua NGUOI KHAC. Tha bao chua
            # doc duoc de tracker giu lai gia tri cu cua chinh nguoi choi.
            return FieldRead("hp", None, "", False,
                             "không thấy vòng vàng của người chơi — bỏ qua thay vì đọc nhầm dòng",
                             (time.perf_counter() - t0) * 1000.0)
        box = hp_box(frame, row)
        cached = self._cached("hp", box, lambda: None)
        if cached is not None:
            return cached
        return self._remember("hp", box, self._read_hp(box, t0))

    def _read_streak(self, frame: np.ndarray, t0: float) -> FieldRead:
        """So chuoi + dau lay tu mau bieu tuong lua."""
        import cv2  # noqa: PLC0415

        h, w = frame.shape[:2]
        nx0, nx1, ny0, ny1 = STREAK_NUMBER
        ix0, ix1, iy0, iy1 = STREAK_ICON
        icon = frame[int(iy0 * h):int(iy1 * h), int(ix0 * w):int(ix1 * w)]
        hsv = cv2.cvtColor(icon, cv2.COLOR_BGR2HSV)
        lit = (hsv[..., 1] > 110) & (hsv[..., 2] > 90)

        if int(lit.sum()) < STREAK_MIN_ICON_PX:
            return FieldRead("streak", 0, "", True, "không có biểu tượng chuỗi — chuỗi 0",
                             (time.perf_counter() - t0) * 1000.0)

        hue = float(np.median(hsv[..., 0][lit]))
        win = hue < STREAK_WIN_HUE or hue > 160
        try:
            d = read_digits(frame[int(ny0 * h):int(ny1 * h), int(nx0 * w):int(nx1 * w)],
                            call=self.call)
        except Exception as exc:                                    # noqa: BLE001
            return FieldRead("streak", None, "", False, f"lỗi OCR: {exc}",
                             (time.perf_counter() - t0) * 1000.0)

        elapsed = (time.perf_counter() - t0) * 1000.0
        if d.value is None or not 0 <= d.value <= 30:
            reason = d.reason if d.value is None else f"chuỗi ngoài khoảng: {d.value}"
            return FieldRead("streak", None, d.text, True, reason, elapsed)
        kind = "thắng" if win else "thua"
        return FieldRead("streak", d.value if win else -d.value, d.text, True,
                         f"chuỗi {kind} {d.value} (hue {hue:.0f})", elapsed)

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
