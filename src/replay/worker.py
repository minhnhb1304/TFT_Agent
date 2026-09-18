"""Hai luong nen cua vo replay (moc M1).

Qt chi duoc dung o day va trong window.py. `src/live/` khong biet gi ve Qt, va
`tests/test_live_session.py` khoa dieu do lai.

Luong phan tich giu HOP THU MOT CHO: khung moi de len khung cu chua kip xu ly.
Doc mot the mat vai tram ms, con video chay 60 fps - xep hang day lai thi panel
se tut hau ca chuc giay sau hinh anh, dung kieu loi ma nguoi choi khong hieu noi.
"""

from __future__ import annotations

import queue
from typing import Any

from PyQt6 import QtCore

from ..capture.frame_source import Frame
from ..capture.regions import ScreenRegions
from ..live.session import LiveSession
from .scan import ScreenMarker, find_screens


class ScanWorker(QtCore.QThread):
    """Quet ca video tim cac vong chon augment."""

    progress = QtCore.pyqtSignal(float, str)
    finished_scan = QtCore.pyqtSignal(list)

    def __init__(self, video: str, regions: ScreenRegions, parent: Any = None) -> None:
        super().__init__(parent)
        self.video = video
        self.regions = regions
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:                                  # noqa: D102
        try:
            markers = find_screens(
                self.video,
                self.regions,
                progress=lambda p, msg: self.progress.emit(p, msg),
                cancelled=lambda: self._cancelled,
            )
        except Exception as exc:                            # noqa: BLE001 - loi quet khong duoc giet app
            self.progress.emit(1.0, f"quét lỗi: {exc}")
            markers = []
        self.finished_scan.emit(list(markers))


class AnalysisWorker(QtCore.QThread):
    """Chay `LiveSession.step` ngoai luong giao dien."""

    event = QtCore.pyqtSignal(object)                       # LiveEvent, du lieu thuan

    def __init__(self, session: LiveSession, parent: Any = None) -> None:
        super().__init__(parent)
        self.session = session
        self._mailbox: queue.Queue[Frame | None] = queue.Queue(maxsize=1)
        # Lenh dieu khien di duong RIENG va duoc xu ly truoc: tua/doc lai phai
        # tac dung ngay, khong duoc xep hang sau mot khung dang doc do.
        self._control: queue.Queue[tuple[str, float]] = queue.Queue()
        self._running = True

    def submit(self, frame: Frame) -> None:
        """Gui mot khung. Con khung cu chua xu ly thi VUT no di, lay khung moi."""
        try:
            self._mailbox.put_nowait(frame)
        except queue.Full:
            try:
                self._mailbox.get_nowait()
            except queue.Empty:
                pass
            try:
                self._mailbox.put_nowait(frame)
            except queue.Full:
                pass

    def seek(self, t: float) -> None:
        self._control.put(("seek", t))

    def force_refresh(self) -> None:
        self._control.put(("refresh", 0.0))

    def new_game(self) -> None:
        self._control.put(("new_game", 0.0))

    def _drain_control(self) -> None:
        while True:
            try:
                name, value = self._control.get_nowait()
            except queue.Empty:
                return
            if name == "seek":
                self.session.seek(value)
            elif name == "refresh":
                self.session.force_refresh()
            elif name == "new_game":
                self.session.new_game()

    def stop(self) -> None:
        self._running = False
        self.submit_sentinel()

    def submit_sentinel(self) -> None:
        try:
            self._mailbox.put_nowait(None)
        except queue.Full:
            pass

    def run(self) -> None:                                  # noqa: D102
        while self._running:
            self._drain_control()
            try:
                frame = self._mailbox.get(timeout=0.2)
            except queue.Empty:
                continue
            self._drain_control()
            if frame is None:
                break
            try:
                self.event.emit(self.session.step(frame))
            except Exception as exc:                        # noqa: BLE001 - mot khung hong khong duoc dung vong lap
                from ..live.events import Status

                self.event.emit(Status(frame.t, f"lỗi phân tích: {exc}"))
