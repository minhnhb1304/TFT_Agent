"""Theo doi MOT man chon augment: o nao vua doi, khi nao doc lai (moc M1/M2).

Day la cho sua loi #2 cua buoi test 2026-09-16: `run_replay.py` chi doc mot
lan luc mo man, nen moi lan reroll sau do deu hien the cu ma khong bao gi
(0/16 lan reroll bat duoc; xem docs/playtest-fixes/eval-dataset.md).

BA TIN HIEU, THEO DUNG THU TU TIN CAY:

    1. Nut o i chuyen `active` -> `pressed`/`disabled`  ->  o i CHAC CHAN doi.
       Do tren record: dau hieu nay ro rang, khong nhap nhang.
    2. Anh thu nho cua o i lech >= `change_thr` so voi lan doc truoc  ->  du
       phong khi khung hinh bi mat nhip va khong thay luc bam nut.
    3. Lech < `settle_thr` giua hai khung lien tiep  ->  the da dung yen, doc
       duoc. Do duoc: dung yen <= 0,6 | doi chu 6-12 | dang lat 20-90, nen hai
       nguong nay PHAI tach roi.

Sau khi bam nut chi doi 2 khung yen thay vi `stable_frames`: hai lan roll lien
tay chi cach nhau ~0,8 s (record 2026-09-16, game 2 man 3-2), doi lau hon thi
nuot mat lan thu hai.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from ..capture.regions import ScreenRegions

SCREEN = "augment_select"
SLOTS = 3
THUMB_SIZE = (48, 12)          # (w, h) - du thay chu doi, du nho de khong nhay theo nhieu


def make_thumb(image: np.ndarray, regions: ScreenRegions, slot: int) -> np.ndarray:
    import cv2  # noqa: PLC0415

    crop = regions.crop(image, SCREEN, f"card_text_{slot}")
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    return cv2.resize(gray, THUMB_SIZE, interpolation=cv2.INTER_AREA).astype(np.float32)


def thumb_diff(a: np.ndarray | None, b: np.ndarray | None) -> float:
    if a is None or b is None:
        return float("inf")
    return float(np.mean(np.abs(a - b)))


@dataclass
class SlotTracker:
    """Trang thai theo doi cua MOT o."""

    slot: int
    last_thumb: np.ndarray | None = None      # khung truoc do
    read_thumb: np.ndarray | None = None      # anh o luc doc thanh cong gan nhat
    steady: int = 0
    pending: bool = True                      # dang cho doc lai
    pressed: bool = False                     # da thay bam nut ke tu lan doc cuoi

    def observe(self, thumb: np.ndarray, pressed: bool, settle_thr: float, change_thr: float) -> None:
        if pressed:
            self.pressed = True
            self.pending = True
            self.steady = 0
        elif thumb_diff(self.last_thumb, thumb) < settle_thr:
            self.steady += 1
        else:
            # Khung dau tien cua noi dung moi VAN tinh la mot khung yen: doi du
            # so khung KE TU no, neu khong hai lan roll lien tay se bi nuot.
            self.steady = 1
        if not self.pending and thumb_diff(self.read_thumb, thumb) >= change_thr:
            self.pending = True               # doi noi dung ma khong thay luc bam
        self.last_thumb = thumb

    def ready(self, stable_frames: int, press_stable_frames: int) -> bool:
        if not self.pending:
            return False
        need = press_stable_frames if self.pressed else stable_frames
        if self.steady < need:
            return False
        # Vua bam thi phai doi den khi noi dung THAT SU doi, khong chot the cu.
        return not (self.pressed and self.read_thumb is not None
                    and thumb_diff(self.read_thumb, self.last_thumb) < 1.0)

    def mark_read(self) -> None:
        self.read_thumb = self.last_thumb
        self.pending = False
        self.pressed = False


@dataclass
class AugmentScreenTracker:
    """Quyet dinh o nao can doc lai o khung hinh nay."""

    regions: ScreenRegions
    settle_thr: float = 2.0
    change_thr: float = 4.0
    stable_frames: int = 3
    press_stable_frames: int = 2
    slots: list[SlotTracker] = field(default_factory=lambda: [SlotTracker(i) for i in range(SLOTS)])
    _last_buttons: tuple[str, ...] = ()

    def reset(self) -> None:
        """Man moi: quen sach, doc lai ca ba o."""
        self.slots = [SlotTracker(i) for i in range(SLOTS)]
        self._last_buttons = ()

    def force_refresh(self) -> None:
        """Nguoi dung yeu cau doc lai (F3 / nut Quet lai)."""
        for s in self.slots:
            s.pending = True
            s.read_thumb = None

    def update(self, image: np.ndarray, button_states: Sequence[str]) -> tuple[int, ...]:
        """Nhan mot khung, tra ve cac o DA SAN SANG doc lai."""
        pressed_now = self._pressed_slots(button_states)
        for i, tracker in enumerate(self.slots):
            tracker.observe(
                make_thumb(image, self.regions, i),
                pressed=i in pressed_now,
                settle_thr=self.settle_thr,
                change_thr=self.change_thr,
            )
        self._last_buttons = tuple(button_states)
        return tuple(
            i for i, t in enumerate(self.slots)
            if t.ready(self.stable_frames, self.press_stable_frames)
        )

    def mark_read(self, slots: Sequence[int]) -> None:
        for i in slots:
            self.slots[i].mark_read()

    def _pressed_slots(self, states: Sequence[str]) -> set[int]:
        if not self._last_buttons:
            return set()
        return {
            i for i, (before, after) in enumerate(zip(self._last_buttons, states))
            if before == "active" and after in ("pressed", "disabled")
        }
