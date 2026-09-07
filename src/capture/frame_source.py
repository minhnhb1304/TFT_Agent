"""Hop dong giua tang capture va tang vision (SPEC 3.1).

SPEC 3.1 chot dau ra cua capture la "numpy array (BGR/BGRA)". File nay bien
cau do thanh mot Protocol co the kiem tra duoc, va do la ca diem:

    VideoFrameSource   (doc file video)      -> dung Protocol nay
    ScreenCapture      (dxcam / WGC, sau)    -> dung Protocol nay

Nho vay moi thu o tang vision viet DUA TREN VOD hom nay se chay nguyen xi
tren game that sau nay, khong sua mot dong. Do la ly do bo cong nay duoc bo
ra bay gio thay vi viet mot script doc video dung mot lan roi vut.

VI SAO CO `ref` CHU KHONG PHAI DUONG DAN FILE

`Scenario.frame_ref` can truy nguoc ve dung khoanh khac da sinh ra ban ghi.
Mot chuoi dang "vod:vQDqc9eiDpk@00:30:45.000" dan duoc nguoi cham do an toi
dung giay trong video goc; mot duong dan PNG thi khong - no chi tro toi mot
file co the da bi xoa. Voi nguon song thi ref la dau thoi gian wall-clock.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Protocol, runtime_checkable

import numpy as np


def format_ref(prefix: str, seconds: float) -> str:
    """Dung chuoi truy nguyen: `<prefix>@HH:MM:SS.mmm`.

    Moc am bi kep ve 0: `divmod` voi so am cho ra `-1:59:59` - mot chuoi trong
    co ve hop le nhung dan nguoi doc toi sai cho trong video. Tha bao 0 con hon.
    """
    ms = max(0, int(round(seconds * 1000)))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{prefix}@{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


@dataclass(frozen=True)
class Frame:
    """Mot khung hinh, doc lap voi nguon."""

    image: np.ndarray   # BGR, (H, W, 3), uint8
    t: float            # giay. VOD = vi tri trong file; song = thoi diem chup
    ref: str            # chuoi truy nguyen, xem docstring dau file

    @property
    def size(self) -> tuple[int, int]:
        """(width, height) - dung thu tu cua man hinh, khong phai cua numpy."""
        h, w = self.image.shape[:2]
        return w, h


@runtime_checkable
class FrameSource(Protocol):
    """Moi nguon frame deu phai tra ve dung mot kieu du lieu."""

    @property
    def size(self) -> tuple[int, int]:
        """(width, height) cua nguon."""
        ...

    def grab(self, at: float | None = None) -> Frame | None:
        """Mot frame. `at` = None nghia la 'bay gio' voi nguon song."""
        ...

    def frames(
        self, start: float = 0.0, end: float | None = None
    ) -> Iterator[Frame]:
        """Duyet frame theo thu tu thoi gian."""
        ...
