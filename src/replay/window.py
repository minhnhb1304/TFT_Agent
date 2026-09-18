"""Cua so replay: phat video, hien loi khuyen tu LiveSession (moc M1).

VO MONG. Quy tac duy nhat, va la quy tac sua loi #3 cua buoi test 2026-09-16:

    Cua so KHONG doc the, KHONG doc HUD, KHONG tu dung GameState.

No chi: lay khung tu video, day sang luong phan tich, roi hien thu nhan lai.
Moi so tren man hinh deu den tu `AdviceReady` - dung trang thai da duoc dung
de tinh ra xep hang do, khong phai mot ban do lai cua rieng giao dien.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
from PyQt6 import QtCore, QtGui, QtWidgets

from ..capture.frame_source import Frame, format_ref
from ..capture.regions import ScreenRegions
from ..decision.advisor import Advisor
from ..knowledge.name_index import NameIndex
from ..live.card_reader import GeminiCardReader, OcrCardReader
from ..live.events import AdviceReady, Cleared, Idle, Status
from ..live.session import LiveSession
from ..utils.settings import Settings
from ..vision.hud_reader import HudReader
from ..vision.reroll_buttons import RerollButtonReader
from . import theme, widgets
from .scan import ScreenMarker
from .viewmodel import build_view
from .worker import AnalysisWorker, ScanWorker

def build_session(
    regions: ScreenRegions, settings: Settings, name_index: NameIndex, card_reader: str = "ocr"
) -> LiveSession:
    """Dung LiveSession y het cach vo live se dung - do la diem cua M1."""
    if card_reader == "gemini":
        from ..vision.augment_reader import AugmentReader

        reader: Any = GeminiCardReader(AugmentReader.load(regions))
    else:
        reader = OcrCardReader(regions, name_index)
    return LiveSession(
        card_reader=reader,
        hud_reader=HudReader.load(regions),
        reroll_reader=RerollButtonReader.load(regions),
        advisor=Advisor(settings=settings),
        regions=regions,
    )


class ReplayWindow(QtWidgets.QMainWindow):
    """Trinh phat video kem bang co van."""

    def __init__(
        self,
        video_path: str,
        *,
        regions_path: str = "config/screen_regions.yaml",
        card_reader: str = "ocr",
        analysis_fps: float = 5.0,
        palette: str = "neon",
    ) -> None:
        super().__init__()
        theme.apply(palette)
        self.settings = Settings.load()
        self.regions = ScreenRegions.load(regions_path)
        self.name_index = NameIndex.load(self.settings.path("name_index"))
        self.card_reader_name = card_reader
        self.analysis_fps = analysis_fps

        self.markers: list[ScreenMarker] = []
        self.features = None
        self.scan_worker: ScanWorker | None = None
        self.playback_speed = 1.0
        self.is_playing = False
        self._last_submit_t = float("-inf")

        self._init_ui()
        self._clear_panel("Đang quét video…")
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._next_frame)

        session = build_session(self.regions, self.settings, self.name_index, card_reader)
        self.features = getattr(getattr(session.advisor, "augment_advisor", None), "features", None)
        self.worker = AnalysisWorker(session)
        self.worker.event.connect(self._on_event)
        self.worker.start()

        self.load_video(video_path)

    # -- giao dien ---------------------------------------------------------

    def _init_ui(self) -> None:
        self.setWindowTitle("TFT Advisory Agent — Replay")
        self.setMinimumSize(1300, 780)
        self.resize(1440, 860)
        self.setStyleSheet(theme.qss())

        root = QtWidgets.QWidget()
        self.setCentralWidget(root)
        layout = QtWidgets.QVBoxLayout(root)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # Hang moc vong chon lõi
        nav = QtWidgets.QFrame()
        nav.setObjectName("bar")
        nav_layout = QtWidgets.QHBoxLayout(nav)
        nav_layout.setContentsMargins(10, 6, 10, 6)
        self.markers_box = QtWidgets.QHBoxLayout()
        nav_layout.addLayout(self.markers_box)
        nav_layout.addStretch()

        self.btn_open = QtWidgets.QPushButton("Mở video khác")
        self.btn_open.clicked.connect(self._choose_video)
        nav_layout.addWidget(self.btn_open)
        self.btn_rescan = QtWidgets.QPushButton("Quét lại video")
        self.btn_rescan.clicked.connect(self.start_scan)
        nav_layout.addWidget(self.btn_rescan)
        self.btn_refresh = QtWidgets.QPushButton("Đọc lại thẻ [F3]")
        self.btn_refresh.clicked.connect(self.force_refresh)
        nav_layout.addWidget(self.btn_refresh)
        layout.addWidget(nav)

        content = QtWidgets.QHBoxLayout()
        content.setSpacing(12)

        left = QtWidgets.QVBoxLayout()
        self.video_label = QtWidgets.QLabel()
        self.video_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet(
            f"background: {theme.SURFACE_1}; border-radius: {theme.RADIUS}px;"
            f" border: 1px solid {theme.BORDER};"
        )
        self.video_label.setMinimumSize(720, 405)
        self.video_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        left.addWidget(self.video_label, stretch=1)

        controls = QtWidgets.QFrame()
        controls.setObjectName("bar")
        ctrl = QtWidgets.QVBoxLayout(controls)
        ctrl.setContentsMargins(10, 6, 10, 8)

        row = QtWidgets.QHBoxLayout()
        self.time_label = QtWidgets.QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet(f"font-family: {theme.MONO}; color: {theme.TEXT_2};")
        self.time_label.setFixedWidth(110)
        row.addWidget(self.time_label)
        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider.sliderMoved.connect(lambda pos: self.seek_to_frame(pos))
        row.addWidget(self.slider)
        ctrl.addLayout(row)

        row2 = QtWidgets.QHBoxLayout()
        self.btn_play = QtWidgets.QPushButton("Phát")
        self.btn_play.setFixedWidth(100)
        self.btn_play.clicked.connect(self.toggle_play)
        row2.addWidget(self.btn_play)
        for label, delta in (("−5s", -5), ("+5s", 5)):
            b = QtWidgets.QPushButton(label)
            b.setFixedWidth(70)
            b.clicked.connect(lambda _, d=delta: self.seek_relative(d))
            row2.addWidget(b)
        row2.addStretch()
        row2.addWidget(QtWidgets.QLabel("Tốc độ:"))
        self.speed = QtWidgets.QComboBox()
        self.speed.addItems(["1.0x", "2.0x", "4.0x", "8.0x"])
        self.speed.currentTextChanged.connect(self._on_speed)
        row2.addWidget(self.speed)
        ctrl.addLayout(row2)
        left.addWidget(controls)
        content.addLayout(left, stretch=6)

        right = QtWidgets.QVBoxLayout()
        right.setSpacing(10)
        self.strip = widgets.StateStrip()
        right.addWidget(self.strip)
        self.verdict = widgets.VerdictBar()
        right.addWidget(self.verdict)

        columns = QtWidgets.QHBoxLayout()
        columns.setSpacing(10)
        self.columns = [widgets.SlotColumn() for _ in range(3)]
        for column in self.columns:
            columns.addWidget(column, stretch=1)
        right.addLayout(columns)
        right.addStretch(1)
        content.addLayout(right, stretch=5)
        layout.addLayout(content)

        self.timeline = widgets.Timeline()
        self.timeline.seek.connect(self.seek_to_seconds)
        layout.addWidget(self.timeline)

    # -- video -------------------------------------------------------------

    def load_video(self, path: str) -> None:
        self.video_path = path
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            QtWidgets.QMessageBox.critical(self, "Lỗi video", f"Không mở được:\n{path}")
            return
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 60.0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration_s = self.total_frames / self.fps if self.fps else 0.0
        self.frame_index = 0
        self.ref_prefix = f"replay:{Path(path).stem}"
        self.slider.setRange(0, max(0, self.total_frames - 1))
        self.setWindowTitle(f"TFT Advisory Agent — Replay — {Path(path).name}")
        self._update_timer()
        self.worker.new_game()
        self.seek_to_frame(0)
        self.start_scan()

    def _choose_video(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Chọn video", str(Path(self.video_path).parent), "Video (*.mp4 *.mkv *.avi *.mov)"
        )
        if path:
            self.load_video(path)

    def start_scan(self) -> None:
        if self.scan_worker is not None and self.scan_worker.isRunning():
            self.scan_worker.cancel()
            self.scan_worker.wait()
        self._clear_markers()
        self.btn_rescan.setEnabled(False)
        self._clear_panel("Đang quét video để tìm các vòng chọn lõi…")
        self.scan_worker = ScanWorker(self.video_path, self.regions, self)
        self.scan_worker.progress.connect(lambda _p, msg: self.strip.set_data(self._last_strip, msg))
        self.scan_worker.finished_scan.connect(self._on_scan_done)
        self.scan_worker.start()

    def _clear_markers(self) -> None:
        while self.markers_box.count():
            item = self.markers_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_scan_done(self, markers: list) -> None:
        self.btn_rescan.setEnabled(True)
        self.markers = list(markers)
        self._clear_markers()
        if not self.markers:
            self._clear_panel("Không thấy vòng chọn lõi nào — vẫn tua tay được.")
            return
        for marker in self.markers:
            btn = QtWidgets.QPushButton(marker.label)
            btn.clicked.connect(lambda _, m=marker: self.seek_to_seconds(max(0.0, m.open_s - 1.0)))
            self.markers_box.addWidget(btn)
        self.timeline.set_data(self.duration_s, [m.open_s for m in self.markers], [])
        self._clear_panel(f"Thấy {len(self.markers)} vòng chọn lõi. Bấm một mốc để xem.")
        self.seek_to_seconds(max(0.0, self.markers[0].open_s - 1.0))

    # -- phat / tua --------------------------------------------------------

    def toggle_play(self) -> None:
        self.is_playing = not self.is_playing
        self.btn_play.setText("Dừng" if self.is_playing else "Phát")
        self.timer.start() if self.is_playing else self.timer.stop()

    def _on_speed(self, text: str) -> None:
        self.playback_speed = float(text.replace("x", ""))
        self._update_timer()

    def _update_timer(self) -> None:
        self.timer.setInterval(max(10, int(1000.0 / min(60.0, self.fps * self.playback_speed))))

    def seek_relative(self, delta_s: float) -> None:
        self.seek_to_seconds(self.frame_index / self.fps + delta_s)

    def seek_to_seconds(self, t: float) -> None:
        self.seek_to_frame(int(max(0.0, t) * self.fps))

    def seek_to_frame(self, index: int) -> None:
        """Nhay toi mot khung. `cap.set` cham, nen CHI goi khi that su nhay."""
        target = max(0, min(index, max(0, self.total_frames - 1)))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, target)
        self.worker.seek(target / self.fps)
        self._last_submit_t = float("-inf")
        self._show_frame()

    def force_refresh(self) -> None:
        self.worker.force_refresh()
        self._last_submit_t = float("-inf")
        self.strip.set_data(self._last_strip, "Đang đọc lại thẻ…")
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.frame_index)
        self._show_frame()

    def _next_frame(self) -> None:
        if not self.is_playing:
            return
        step = max(1, int(self.playback_speed))
        if self.frame_index + step >= self.total_frames:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.worker.new_game()
        elif step > 1:                      # tua nhanh: nhay, con 1x thi doc tuan tu
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.frame_index + step)
        self._show_frame()

    def _show_frame(self) -> None:
        ok, image = self.cap.read()
        if not ok or image is None:
            return
        self.frame_index = max(0, int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1)
        t = self.frame_index / self.fps

        if t - self._last_submit_t >= 1.0 / self.analysis_fps:
            self._last_submit_t = t
            self.worker.submit(Frame(image=image.copy(), t=t, ref=format_ref(self.ref_prefix, t)))

        self._paint(image, t)

    def _paint(self, image, t: float) -> None:
        cur_m, cur_s = divmod(int(t), 60)
        tot_m, tot_s = divmod(int(self.duration_s), 60)
        self.time_label.setText(f"{cur_m:02d}:{cur_s:02d} / {tot_m:02d}:{tot_s:02d}")
        self.slider.blockSignals(True)
        self.slider.setValue(self.frame_index)
        self.slider.blockSignals(False)

        size = self.video_label.size()
        h, w = image.shape[:2]
        scale = min(max(320, size.width()) / w, max(180, size.height()) / h)
        resized = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        qimg = QtGui.QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.shape[1] * 3,
                            QtGui.QImage.Format.Format_RGB888)
        self.video_label.setPixmap(QtGui.QPixmap.fromImage(qimg))

    # -- nhan su kien tu lõi ----------------------------------------------

    def _on_event(self, event: Any) -> None:
        if isinstance(event, Idle):
            return
        if isinstance(event, Cleared):
            self._clear_panel("Đã rời màn chọn lõi.")
            return
        if isinstance(event, Status):
            self.strip.set_data(self._last_strip, " · ".join([event.message, *event.degraded]))
            return
        if isinstance(event, AdviceReady):
            self._show_advice(event)

    def _clear_panel(self, status: str) -> None:
        from .viewmodel import SlotVM, StripVM, VerdictVM

        self._last_strip = StripVM()
        self.strip.set_data(self._last_strip, status)
        self.verdict.set_data(VerdictVM())
        for i, column in enumerate(self.columns):
            column.set_data(SlotVM(i, "—"))

    def _show_advice(self, event: AdviceReady) -> None:
        strip, verdict, slots = build_view(event, rarity_of=self._rarity_of)
        self._last_strip = strip
        self.strip.set_data(strip, self._status_line(event))
        self.verdict.set_data(verdict)
        for column, slot in zip(self.columns, slots):
            column.set_data(slot)
        self.timeline.set_position(event.t)

    def _status_line(self, event: AdviceReady) -> str:
        notes = []
        if event.latency_ms:
            notes.append("đọc " + ", ".join(f"{k} {v:.0f}ms" for k, v in event.latency_ms.items()))
        return " · ".join(notes)

    def _rarity_of(self, api_name: str) -> int | None:
        feature = self.features.get(api_name) if self.features else None
        return getattr(feature, "tier", None)

    # -- vong doi ----------------------------------------------------------

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:  # noqa: N802
        key = event.key()
        if key == QtCore.Qt.Key.Key_Space:
            self.toggle_play()
        elif key == QtCore.Qt.Key.Key_Left:
            self.seek_relative(-5)
        elif key == QtCore.Qt.Key.Key_Right:
            self.seek_relative(5)
        elif key == QtCore.Qt.Key.Key_F3:
            self.force_refresh()
        elif key in (QtCore.Qt.Key.Key_Escape, QtCore.Qt.Key.Key_Q):
            self.close()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:   # noqa: N802
        self.timer.stop()
        if self.scan_worker is not None and self.scan_worker.isRunning():
            self.scan_worker.cancel()
            self.scan_worker.wait(3000)
        self.worker.stop()
        self.worker.wait(5000)
        if self.cap.isOpened():
            self.cap.release()
        event.accept()
