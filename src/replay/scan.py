"""Quet nhanh ca video de tim cac vong chon augment (moc M1, vo replay).

KHONG Qt, KHONG OCR the: chi doc nut reroll (template matching, vai ms) o nhip
thua, roi gom cac moc lien nhau. OCR chi chay khi nguoi dung thuc su xem mot
vong - quet ca video bang OCR thi mat hang chuc phut ma khong them thong tin.

Gom voi `merge_gap_s` LON (30 s): nguoi choi hay an man chon augment ~10 s de
nhin ban co roi mo lai. Tach chung ra thanh hai vong la sai, va se lam mat
luot reroll da dung (docs/playtest-fixes/eval-dataset.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from ..capture.regions import ScreenRegions
from ..capture.video_source import VideoFrameSource
from ..vision.hud_reader import HudReader
from ..vision.reroll_buttons import RerollButtonReader


@dataclass(frozen=True)
class ScreenMarker:
    """Mot vong chon augment tim duoc trong video."""

    open_s: float
    close_s: float
    stage: str = ""

    @property
    def label(self) -> str:
        m, s = divmod(int(self.open_s), 60)
        return f"{self.stage or '?'} ({m:02d}:{s:02d})"


def merge_spans(times: Iterable[float], present: Iterable[bool], gap_s: float) -> list[tuple[float, float]]:
    spans: list[tuple[float, float]] = []
    for t, ok in zip(times, present):
        if not ok:
            continue
        if spans and t - spans[-1][1] <= gap_s:
            spans[-1] = (spans[-1][0], t)
        else:
            spans.append((t, t))
    return spans


def find_screens(
    video: str,
    regions: ScreenRegions,
    *,
    fps: float = 1.0,
    merge_gap_s: float = 30.0,
    read_stage: bool = True,
    progress: Callable[[float, str], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> list[ScreenMarker]:
    """Tra ve cac vong chon augment, som nhat truoc."""
    src = VideoFrameSource(video)
    buttons = RerollButtonReader.load(regions)
    duration = src.duration or 1.0

    times: list[float] = []
    present: list[bool] = []
    for frame in src.frames(fps=fps):
        if cancelled is not None and cancelled():
            return []
        times.append(frame.t)
        present.append(buttons.read(frame.image).screen_present)
        if progress is not None and len(times) % 30 == 0:
            progress(frame.t / duration, f"đang quét {int(frame.t // 60):02d}:{int(frame.t % 60):02d}")

    spans = merge_spans(times, present, merge_gap_s)
    if not read_stage:
        return [ScreenMarker(a, b) for a, b in spans]

    hud = HudReader.load(regions)
    markers: list[ScreenMarker] = []
    for a, b in spans:
        # Doc stage TRONG man: truoc khi mo man HUD van con hien vong truoc (3-1 thay vi 3-2).
        frame = src.grab(a + min(1.0, max(0.0, b - a)))
        stage = ""
        if frame is not None:
            try:
                read = hud.read(frame.image).find("stage")
                stage = str(read.value) if read and read.value else ""
            except Exception:                       # noqa: BLE001 - thieu stage khong lam hong danh sach moc
                stage = ""
        markers.append(ScreenMarker(a, b, stage))
    return markers
