"""TFT Advisory Agent - Replay & Live Game Analysis Runner (Hoàn Toàn Động).

Chạy:
    .\\.venv\\Scripts\\python run_replay.py --video "duong_dan_video.mp4"
    hoặc kéo thả video vào chay_replay.bat

Tính năng tự động 100% trên MỌI VIDEO:
    1. Trình phát video 1080p 60fps mượt mà, hỗ trợ tua thời gian và chỉnh tốc độ (1x..8x).
    2. Tự động quét tìm các mốc chọn Lõi (Augment Selection) của video đó bằng thuật toán
       nhận diện glyph xúc xắc (Reroll Button Template Matching).
    3. Tự động sinh các nút nhảy nhanh tương ứng với các vòng Lõi của trận đấu đó.
    4. Nhận diện động 100% nội dung 3 thẻ Lõi tại bất kỳ frame nào bằng OCR tiếng Việt
       kết hợp giải thuật so khớp ngữ nghĩa không dấu (Unaccented Fuzzy Matcher) với NameIndex.
    5. Đọc động thanh HUD (Stage, Vàng, Cấp độ, Máu, XP) qua HudReader + GameStateTracker.
    6. Cố vấn tối ưu thời gian thực với Advisor và Sequential Reroll Policy.
"""

from __future__ import annotations

import argparse
import difflib
import os
from pathlib import Path
import sys
import time
from typing import Any
import unicodedata

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cv2
import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets

from src.capture.regions import ScreenRegions
from src.decision.advisor import Advisor
from src.decision.reroll_policy import RerollState
from src.game_state.models import GameState
from src.game_state.state_tracker import GameStateTracker
from src.knowledge.name_index import NameIndex
from src.overlay.widgets.augment_panel import create_panel
from src.utils.settings import Settings
from src.vision.hud_reader import HudReader
from src.vision.ocr_engine import engine
from src.vision.preprocess import ocr_texts
from src.vision.reroll_buttons import RerollButtonReader

DEFAULT_VIDEO_PATH = (
    r"D:\tft_records\Outplayed\Screen recorder\Screen recorder_09-16-2026_17-8-8-8"
    r"\Screen recorder_09-16-2026_17-43-52-150.mp4"
)


def strip_accents(s: str) -> str:
    """Xóa dấu tiếng Việt để so khớp tương đồng chuẩn xác."""
    s = s.lower().replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").strip()


class DynamicCardRecognizer:
    """Bộ nhận diện 3 thẻ Lõi động từ hình ảnh crop bằng OCR + Fuzzy Matcher."""

    def __init__(self, regions: ScreenRegions, name_index: NameIndex):
        self.regions = regions
        self.name_index = name_index
        self.ocr = engine()

        # Xay dung ban do tra cuu ten khong dau -> (ten goc, apiName)
        self.lookup: dict[str, tuple[str, str]] = {}
        for api_name, langs in name_index.display.get("augments", {}).items():
            disp = langs.get("vi", "")
            if disp:
                norm = strip_accents(disp)
                self.lookup[norm] = (disp, api_name)

    def recognize_cards(self, frame: np.ndarray) -> list[dict[str, Any]]:
        """Nhận diện 3 ô Lõi từ khung hình BGR."""
        cards = []
        for slot in range(3):
            crop = self.regions.crop(frame, "augment_select", f"card_text_{slot}")
            res = self.ocr(crop)
            texts = ocr_texts(res)
            raw_title = texts[0] if texts else ""
            norm_title = strip_accents(raw_title)

            # Tim match gan nhat trong NameIndex
            matches = difflib.get_close_matches(norm_title, self.lookup.keys(), n=1, cutoff=0.45)
            if matches:
                disp_name, api_name = self.lookup[matches[0]]
                ratio = difflib.SequenceMatcher(None, norm_title, matches[0]).ratio()
                cards.append({
                    "slot": slot,
                    "display_name": disp_name,
                    "api_name": api_name,
                    "confidence": ratio,
                    "raw_text": raw_title,
                })
            else:
                cards.append({
                    "slot": slot,
                    "display_name": raw_title or "Chưa nhận diện",
                    "api_name": "",
                    "confidence": 0.0,
                    "raw_text": raw_title,
                })
        return cards


class VideoScannerThread(QtCore.QThread):
    """Luồng chạy ngầm quét toàn bộ video để tìm các thời điểm xuất hiện 3 Lõi chọn."""

    progress = QtCore.pyqtSignal(int, str)
    finished_scan = QtCore.pyqtSignal(list)

    def __init__(self, video_path: str, regions: ScreenRegions):
        super().__init__()
        self.video_path = video_path
        self.regions = regions
        self.is_cancelled = False

    def cancel(self) -> None:
        self.is_cancelled = True

    def run(self) -> None:
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            self.finished_scan.emit([])
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 60.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_s = total_frames / fps if fps > 0 else 0

        reader = RerollButtonReader.load(self.regions)
        hud = HudReader.load(self.regions)

        # Quet mau moi 4 giay
        step_s = 4.0
        step_frames = int(step_s * fps)
        hits: list[dict[str, Any]] = []

        cur_frame = 0
        total_steps = max(1, total_frames // step_frames)
        step_idx = 0

        while cur_frame < total_frames and not self.is_cancelled:
            cap.set(cv2.CAP_PROP_POS_FRAMES, cur_frame)
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            step_idx += 1
            if step_idx % 5 == 0:
                pct = int((cur_frame / total_frames) * 100)
                t_cur = cur_frame / fps
                self.progress.emit(pct, f"Đang quét video ({pct}%)... mốc {int(t_cur//60):02d}:{int(t_cur%60):02d}")

            res = reader.read(frame)
            if res.screen_present:
                t_sec = cur_frame / fps
                stage_val = None
                try:
                    hud_res = hud.read(frame)
                    f_stage = hud_res.find("stage")
                    if f_stage and f_stage.value:
                        stage_val = str(f_stage.value)
                except Exception:
                    pass

                hits.append({
                    "time_s": t_sec,
                    "frame_idx": cur_frame,
                    "stage": stage_val,
                })

            cur_frame += step_frames

        cap.release()

        if self.is_cancelled or not hits:
            self.finished_scan.emit([])
            return

        # Gom nhom cac frame lien tiep thanh cac cum (Cluster)
        clusters: list[list[dict[str, Any]]] = []
        cur_cluster: list[dict[str, Any]] = [hits[0]]

        for h in hits[1:]:
            if h["time_s"] - cur_cluster[-1]["time_s"] <= 25.0:
                cur_cluster.append(h)
            else:
                clusters.append(cur_cluster)
                cur_cluster = [h]
        if cur_cluster:
            clusters.append(cur_cluster)

        # Tao danh sach cac moc quan trong
        scenarios = []
        for i, cl in enumerate(clusters, start=1):
            first_t = cl[0]["time_s"]
            stage_cand = None
            for item in cl:
                if item["stage"]:
                    stage_cand = item["stage"]
                    break

            default_stages = ["2-1", "3-2", "4-2", "5-2", "6-2"]
            stage_name = stage_cand or (default_stages[i - 1] if i <= len(default_stages) else f"Vòng {i}")

            m, s = int(first_t // 60), int(first_t % 60)
            scenarios.append({
                "time_s": first_t,
                "stage": stage_name,
                "label": f"{stage_name} ({m:02d}:{s:02d})",
                "desc": f"Vòng chọn Lõi #{i} (từ {m:02d}:{s:02d})",
            })

        self.finished_scan.emit(scenarios)


class VideoReplayWindow(QtWidgets.QMainWindow):
    """Cửa sổ ứng dụng Replay & Cố vấn trực tiếp ĐTCL (Động trên mọi video)."""

    def __init__(self, video_path: str = DEFAULT_VIDEO_PATH):
        super().__init__()
        self.video_path = video_path
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            QtWidgets.QMessageBox.critical(
                None, "Lỗi đọc video", f"Không thể mở file video:\n{video_path}"
            )
            sys.exit(1)

        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 60.0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration_s = self.total_frames / self.fps if self.fps > 0 else 0
        self.current_frame_idx = 0
        self.is_playing = False
        self.playback_speed = 1.0

        # Khoi tao cac module co van va thi giac
        self.settings = Settings.load()
        self.advisor = Advisor(settings=self.settings)
        self.name_index = NameIndex.load(ROOT / "data" / "name_index.json")

        self.regions = ScreenRegions.load(ROOT / "config" / "screen_regions.yaml")
        self.reroll_reader = RerollButtonReader.load(self.regions)
        self.hud_reader = HudReader.load(self.regions)
        self.card_recognizer = DynamicCardRecognizer(self.regions, self.name_index)
        self.tracker = GameStateTracker()

        self.detected_scenarios: list[dict[str, Any]] = []
        self._last_analyzed_second = -999.0
        self.scanner_thread: VideoScannerThread | None = None

        self._init_ui()

        # Timer phat video
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._next_frame)
        self._update_timer_interval()

        # Bat dau o frame dau tien va chay quet tu dong cac moc
        self.seek_to_frame(0)
        self.start_auto_scan()

    def _init_ui(self) -> None:
        self.setWindowTitle("TFT Advisory Agent — Trình Phân Tích & Cố Vấn Trận Đấu (Dynamic Replay)")
        self.setMinimumSize(1300, 780)
        self.resize(1440, 850)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #070d19;
                color: #e0e8f5;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #e0e8f5;
            }
            QPushButton {
                background-color: #122238;
                border: 1px solid #23426a;
                border-radius: 5px;
                color: #a8cded;
                padding: 6px 12px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1a365d;
                border-color: #00b4d8;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #0077b6;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #15263d;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #00d2ff;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 2px solid #00d2ff;
                width: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
            }
            QComboBox {
                background-color: #122238;
                border: 1px solid #23426a;
                border-radius: 5px;
                color: #00e5ff;
                padding: 4px 8px;
                font-weight: bold;
            }
        """)

        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)
        root_layout = QtWidgets.QVBoxLayout(central)
        root_layout.setContentsMargins(12, 10, 12, 10)
        root_layout.setSpacing(8)

        # 1. Top Bar: Tieu de + Thong tin video
        top_bar = QtWidgets.QHBoxLayout()
        icon_lbl = QtWidgets.QLabel("🎮")
        icon_lbl.setStyleSheet("font-size: 22px;")
        top_bar.addWidget(icon_lbl)

        title_lbl = QtWidgets.QLabel("TFT AGENT — CO-PILOT PHÂN TÍCH TRẬN ĐẤU (DYNAMIC)")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #00e5ff; letter-spacing: 0.5px;")
        top_bar.addWidget(title_lbl)

        top_bar.addStretch()

        video_name = Path(self.video_path).name
        dur_min = int(self.duration_s // 60)
        dur_sec = int(self.duration_s % 60)
        info_lbl = QtWidgets.QLabel(f"📹 {video_name} ({dur_min}:{dur_sec:02d} | 1080p)")
        info_lbl.setStyleSheet("color: #7997b8; font-size: 12px;")
        top_bar.addWidget(info_lbl)

        btn_open = QtWidgets.QPushButton("📂 Mở Video Khác")
        btn_open.clicked.connect(self._open_new_video)
        top_bar.addWidget(btn_open)

        root_layout.addLayout(top_bar)

        # 2. Key Stages Navigation Bar (Các nút nhảy động được tự sinh theo video)
        nav_card = QtWidgets.QFrame()
        nav_card.setStyleSheet("background-color: #0d1a2d; border: 1px solid #1a3254; border-radius: 8px;")
        self.nav_layout = QtWidgets.QHBoxLayout(nav_card)
        self.nav_layout.setContentsMargins(10, 6, 10, 6)
        self.nav_layout.setSpacing(8)

        self.nav_title = QtWidgets.QLabel("⚡ Mốc chọn Lõi (Tự động phát hiện):")
        self.nav_title.setStyleSheet("font-weight: bold; color: #ffb703; font-size: 13px;")
        self.nav_layout.addWidget(self.nav_title)

        # Container cho cac nut moc dong
        self.dynamic_btn_container = QtWidgets.QWidget()
        self.dynamic_btn_layout = QtWidgets.QHBoxLayout(self.dynamic_btn_container)
        self.dynamic_btn_layout.setContentsMargins(0, 0, 0, 0)
        self.dynamic_btn_layout.setSpacing(6)
        self.nav_layout.addWidget(self.dynamic_btn_container)

        self.nav_layout.addStretch()

        self.btn_rescan_video = QtWidgets.QPushButton("⚡ Quét Lại Toàn Bộ Video")
        self.btn_rescan_video.setToolTip("Quét lại toàn bộ video để tìm các vòng chọn Lõi mới")
        self.btn_rescan_video.setStyleSheet("background-color: #162c4a; color: #a8cded;")
        self.btn_rescan_video.clicked.connect(self.start_auto_scan)
        self.nav_layout.addWidget(self.btn_rescan_video)

        self.btn_scan_current = QtWidgets.QPushButton("🔍 Quét Frame Này [F3]")
        self.btn_scan_current.setToolTip("Nhận diện 3 Lõi và phân tích cố vấn ngay tại thời điểm đang dừng")
        self.btn_scan_current.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0077b6, stop:1 #00b4d8); color: white; font-weight: bold;"
        )
        self.btn_scan_current.clicked.connect(self.analyze_current_frame)
        self.nav_layout.addWidget(self.btn_scan_current)

        root_layout.addWidget(nav_card)

        # 3. Main Split View: Video Player (Trai) & Advisory Panel (Phai)
        content_layout = QtWidgets.QHBoxLayout()
        content_layout.setSpacing(12)

        # --- Left Column: Video Viewport & Player Controls ---
        left_col = QtWidgets.QVBoxLayout()
        left_col.setSpacing(6)

        self.video_label = QtWidgets.QLabel()
        self.video_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: #030710; border-radius: 8px; border: 1px solid #162a45;")
        self.video_label.setMinimumSize(720, 405)
        self.video_label.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding
        )
        left_col.addWidget(self.video_label, stretch=1)

        # Timeline Slider & Controls
        controls_card = QtWidgets.QFrame()
        controls_card.setStyleSheet("background-color: #0b1626; border-radius: 6px; padding: 4px;")
        ctrl_layout = QtWidgets.QVBoxLayout(controls_card)
        ctrl_layout.setContentsMargins(8, 4, 8, 6)
        ctrl_layout.setSpacing(4)

        slider_row = QtWidgets.QHBoxLayout()
        self.time_label = QtWidgets.QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("font-family: monospace; font-size: 12px; color: #88aacc;")
        self.time_label.setFixedWidth(110)
        slider_row.addWidget(self.time_label)

        self.seek_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, self.total_frames)
        self.seek_slider.sliderMoved.connect(self._on_slider_moved)
        slider_row.addWidget(self.seek_slider)
        ctrl_layout.addLayout(slider_row)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(6)

        self.btn_play = QtWidgets.QPushButton("▶ Phát Video")
        self.btn_play.setFixedWidth(110)
        self.btn_play.clicked.connect(self.toggle_play)
        btn_row.addWidget(self.btn_play)

        btn_step_back = QtWidgets.QPushButton("◀ -5s")
        btn_step_back.setFixedWidth(65)
        btn_step_back.clicked.connect(lambda: self.seek_relative(-5))
        btn_row.addWidget(btn_step_back)

        btn_step_fwd = QtWidgets.QPushButton("+5s ▶")
        btn_step_fwd.setFixedWidth(65)
        btn_step_fwd.clicked.connect(lambda: self.seek_relative(5))
        btn_row.addWidget(btn_step_fwd)

        btn_row.addStretch()

        speed_lbl = QtWidgets.QLabel("Tốc độ:")
        speed_lbl.setStyleSheet("color: #88aacc; font-size: 12px;")
        btn_row.addWidget(speed_lbl)

        self.speed_combo = QtWidgets.QComboBox()
        self.speed_combo.addItems(["1.0x", "2.0x", "4.0x", "8.0x"])
        self.speed_combo.currentTextChanged.connect(self._on_speed_changed)
        btn_row.addWidget(self.speed_combo)

        ctrl_layout.addLayout(btn_row)
        left_col.addWidget(controls_card)

        content_layout.addLayout(left_col, stretch=6)

        # --- Right Column: Live HUD State & Advisor Overlay Panel ---
        right_col = QtWidgets.QVBoxLayout()
        right_col.setSpacing(8)

        self.hud_card = QtWidgets.QFrame()
        self.hud_card.setStyleSheet(
            "background-color: #0c182b; border: 1px solid #1a3559; border-radius: 8px; padding: 6px;"
        )
        hud_layout = QtWidgets.QVBoxLayout(self.hud_card)
        hud_layout.setContentsMargins(8, 6, 8, 6)
        hud_layout.setSpacing(4)

        hud_title = QtWidgets.QLabel("📡 THÔNG TIN TRẬN ĐẤU (LIVE HUD TRACKER)")
        hud_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #00d2ff;")
        hud_layout.addWidget(hud_title)

        self.hud_stats_lbl = QtWidgets.QLabel("🎯 Stage: --  |  💰 Vàng: --  |  👑 Cấp: --  |  ❤️ Máu: --")
        self.hud_stats_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        hud_layout.addWidget(self.hud_stats_lbl)

        self.hud_status_lbl = QtWidgets.QLabel("🟢 Đang quét video để nhận diện các vòng chọn Lõi...")
        self.hud_status_lbl.setStyleSheet("font-size: 11px; color: #73e6a7;")
        hud_layout.addWidget(self.hud_status_lbl)

        right_col.addWidget(self.hud_card)

        self.panel_container = QtWidgets.QFrame()
        self.panel_container.setStyleSheet(
            "background-color: #0b1424; border: 2px solid #00b4d8; border-radius: 10px;"
        )
        panel_layout = QtWidgets.QVBoxLayout(self.panel_container)
        panel_layout.setContentsMargins(8, 6, 8, 8)
        panel_layout.setSpacing(6)

        panel_hdr = QtWidgets.QHBoxLayout()
        panel_title = QtWidgets.QLabel("💡 CỐ VẤN LÕI NÂNG CẤP (ADVISOR)")
        panel_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #00e5ff;")
        panel_hdr.addWidget(panel_title)
        panel_hdr.addStretch()

        self.reroll_status_badge = QtWidgets.QLabel("Đổi bài: --/3")
        self.reroll_status_badge.setStyleSheet(
            "background: #1a3352; color: #ffcc00; padding: 2px 8px; border-radius: 4px; font-weight: bold;"
        )
        panel_hdr.addWidget(self.reroll_status_badge)
        panel_layout.addLayout(panel_hdr)

        self.advisor_panel = create_panel(self.panel_container)
        self.advisor_panel.setMinimumSize(420, 360)
        panel_layout.addWidget(self.advisor_panel)

        right_col.addWidget(self.panel_container, stretch=1)
        content_layout.addLayout(right_col, stretch=4)
        root_layout.addLayout(content_layout)

    def _open_new_video(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Chọn video trận đấu TFT để phân tích",
            str(ROOT),
            "Video Files (*.mp4 *.mkv *.avi *.mov);;All Files (*.*)",
        )
        if file_path:
            self.load_video(file_path)

    def load_video(self, video_path: str) -> None:
        self.timer.stop()
        if self.scanner_thread and self.scanner_thread.isRunning():
            self.scanner_thread.cancel()
            self.scanner_thread.wait()

        self.video_path = video_path
        if self.cap.isOpened():
            self.cap.release()

        self.cap = cv2.VideoCapture(self.video_path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 60.0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration_s = self.total_frames / self.fps if self.fps > 0 else 0
        self.seek_slider.setRange(0, self.total_frames)

        self.seek_to_frame(0)
        self.start_auto_scan()

    def start_auto_scan(self) -> None:
        """Kích hoạt tiến trình quét tự động các vòng chọn Lõi trong video mới."""
        self.btn_rescan_video.setEnabled(False)
        self.hud_status_lbl.setText("⏳ Đang quét toàn bộ video để tìm các vòng Lõi...")

        # Xoa cac nut cu
        while self.dynamic_btn_layout.count():
            item = self.dynamic_btn_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        lbl_loading = QtWidgets.QLabel("Đang dò tìm các vòng Lõi...")
        lbl_loading.setStyleSheet("color: #7997b8; font-style: italic;")
        self.dynamic_btn_layout.addWidget(lbl_loading)

        self.scanner_thread = VideoScannerThread(self.video_path, self.regions)
        self.scanner_thread.progress.connect(lambda _, msg: self.hud_status_lbl.setText(msg))
        self.scanner_thread.finished_scan.connect(self._on_scan_finished)
        self.scanner_thread.start()

    def _on_scan_finished(self, scenarios: list[dict[str, Any]]) -> None:
        self.btn_rescan_video.setEnabled(True)
        self.detected_scenarios = scenarios

        # Xoa loading label
        while self.dynamic_btn_layout.count():
            item = self.dynamic_btn_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not scenarios:
            self.hud_status_lbl.setText("Không phát hiện vòng Lõi nào. Bạn có thể tua tới bất kỳ lúc nào và bấm [Quét Frame Này].")
            lbl_none = QtWidgets.QLabel("(Không phát hiện vòng Lõi tự động)")
            lbl_none.setStyleSheet("color: #7997b8;")
            self.dynamic_btn_layout.addWidget(lbl_none)
            return

        self.hud_status_lbl.setText(f"✅ Đã tìm thấy {len(scenarios)} vòng chọn Lõi! Bấm các nút mốc phía trên để xem.")

        for sc in scenarios:
            btn = QtWidgets.QPushButton(sc["label"])
            btn.setToolTip(f"{sc['desc']} (Nhảy tới {int(sc['time_s'])}s)")
            btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #162c4a, stop:1 #1a3c68);
                    color: #d8ecff;
                    border: 1px solid #2b558c;
                    padding: 6px 10px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0077b6, stop:1 #00b4d8);
                    color: #ffffff;
                    border: 1px solid #90e0ef;
                }
            """)
            target_t = sc["time_s"]
            btn.clicked.connect(lambda _, t=target_t: self.seek_and_analyze(t))
            self.dynamic_btn_layout.addWidget(btn)

        # Nhay den moc dau tien va phan tich luon
        self.seek_and_analyze(scenarios[0]["time_s"])

    def seek_and_analyze(self, time_s: float) -> None:
        target_frame = int(time_s * self.fps)
        self.seek_to_frame(target_frame)
        self.analyze_current_frame()

    def analyze_current_frame(self) -> None:
        """Nhận diện ĐỘNG 100% tại frame hiện tại: đọc HUD, nhận diện 3 thẻ Lõi qua OCR, và chạy Advisor."""
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_idx)
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return

        self.hud_status_lbl.setText("⏳ Đang quét nhận diện HUD và 3 Lõi...")
        QtWidgets.QApplication.processEvents()

        # 1. Doc HUD bang HudReader
        stage_val = None
        gold_val = 0
        lvl_val = 1
        hp_val = 100
        try:
            hud_reading = self.hud_reader.read(frame)
            self.tracker.update(hud_reading)
            st = self.tracker.state()
            stage_val = st.stage
            gold_val = st.gold or 0
            lvl_val = st.level or 1
            hp_val = st.hp or 100
        except Exception:
            pass

        # 2. Doc trang thai nut Reroll
        reroll_res = self.reroll_reader.read(frame)
        avail = [b.state == "active" for b in reroll_res.reads]
        rerolls = RerollState(available=tuple(avail))
        r_avail = sum(1 for a in avail if a)
        self.reroll_status_badge.setText(f"Đổi bài: {r_avail}/3")

        # 3. Nhan dien dong 3 the Loi qua DynamicCardRecognizer
        cards = self.card_recognizer.recognize_cards(frame)
        choices = [c["api_name"] for c in cards if c["api_name"]]

        stage_str = stage_val or "Không rõ"
        self.hud_stats_lbl.setText(
            f"🎯 Stage: {stage_str}  |  💰 Vàng: {gold_val}  |  👑 Cấp: {lvl_val}  |  ❤️ Máu: {hp_val}"
        )

        if choices:
            state = GameState(gold=gold_val, level=lvl_val, hp=hp_val, stage=stage_str)
            bundle = self.advisor.advise(state=state, choices=choices, rerolls=rerolls)
            self.advisor_panel.set_ranking(bundle.ranking, bundle.reroll)

            card_names = ", ".join(f"[{c['display_name']}]" for c in cards if c["api_name"])
            action_desc = "ĐỔI Ô" if bundle.reroll.action == "REROLL" else "CHỌN LÕI"
            self.hud_status_lbl.setText(
                f"✅ Đã nhận diện: {card_names} ➔ Khuyên: {action_desc} (Lõi tốt nhất: {bundle.ranking.top.name})"
            )
        else:
            if reroll_res.screen_present:
                self.hud_status_lbl.setText("Đang mở màn chọn Lõi nhưng chưa đọc rõ tên thẻ (hãy bấm Quét Lại hoặc tua thêm 1-2s).")
            else:
                self.hud_status_lbl.setText(f"Frame lúc {self.time_label.text().split(' / ')[0]} không ở màn chọn Lõi.")

    def _update_timer_interval(self) -> None:
        target_fps = min(60.0, self.fps * self.playback_speed)
        interval_ms = max(10, int(1000.0 / target_fps))
        self.timer.setInterval(interval_ms)

    def _on_speed_changed(self, text: str) -> None:
        try:
            self.playback_speed = float(text.replace("x", ""))
            self._update_timer_interval()
        except ValueError:
            pass

    def toggle_play(self) -> None:
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.btn_play.setText("⏸ Tạm Dừng")
            self.timer.start()
        else:
            self.btn_play.setText("▶ Tiếp Tục")
            self.timer.stop()

    def seek_relative(self, delta_s: float) -> None:
        delta_frames = int(delta_s * self.fps)
        target = max(0, min(self.total_frames - 1, self.current_frame_idx + delta_frames))
        self.seek_to_frame(target)

    def _on_slider_moved(self, pos: int) -> None:
        self.seek_to_frame(pos)

    def seek_to_frame(self, frame_idx: int) -> None:
        self.current_frame_idx = frame_idx
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        self._display_current_frame()

    def _next_frame(self) -> None:
        if not self.is_playing:
            return

        step = max(1, int(self.playback_speed))
        self.current_frame_idx += step
        if self.current_frame_idx >= self.total_frames:
            self.current_frame_idx = 0
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        if step > 1:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_idx)

        self._display_current_frame()

    def _display_current_frame(self) -> None:
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return

        current_t = self.current_frame_idx / self.fps
        cur_m, cur_s = int(current_t // 60), int(current_t % 60)
        tot_m, tot_s = int(self.duration_s // 60), int(self.duration_s % 60)
        self.time_label.setText(f"{cur_m:02d}:{cur_s:02d} / {tot_m:02d}:{tot_s:02d}")

        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(self.current_frame_idx)
        self.seek_slider.blockSignals(False)

        lbl_size = self.video_label.size()
        lbl_w = max(320, lbl_size.width())
        lbl_h = max(180, lbl_size.height())

        h, w = frame.shape[:2]
        scale = min(lbl_w / w, lbl_h / h)
        nw, nh = int(w * scale), int(h * scale)

        resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        qimg = QtGui.QImage(rgb.data, nw, nh, nw * 3, QtGui.QImage.Format.Format_RGB888)
        pix = QtGui.QPixmap.fromImage(qimg)
        self.video_label.setPixmap(pix)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:  # noqa: N802
        k = event.key()
        if k == QtCore.Qt.Key.Key_Space:
            self.toggle_play()
        elif k == QtCore.Qt.Key.Key_Left:
            self.seek_relative(-5)
        elif k == QtCore.Qt.Key.Key_Right:
            self.seek_relative(5)
        elif k == QtCore.Qt.Key.Key_F3:
            self.analyze_current_frame()
        elif k in (QtCore.Qt.Key.Key_Escape, QtCore.Qt.Key.Key_Q):
            self.close()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        self.timer.stop()
        if self.scanner_thread and self.scanner_thread.isRunning():
            self.scanner_thread.cancel()
            self.scanner_thread.wait()
        if self.cap.isOpened():
            self.cap.release()
        event.accept()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="TFT Advisory Agent - Replay & Live Game Analysis Runner."
    )
    parser.add_argument(
        "--video",
        "-v",
        default=None,
        help="Đường dẫn file video trận đấu (.mp4, .mkv)",
    )
    args = parser.parse_args(argv)

    app = QtWidgets.QApplication(sys.argv)

    video_path = args.video
    if not video_path:
        if os.path.exists(DEFAULT_VIDEO_PATH):
            video_path = DEFAULT_VIDEO_PATH
        else:
            file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
                None,
                "Chọn video trận đấu TFT để phân tích",
                str(ROOT),
                "Video Files (*.mp4 *.mkv *.avi *.mov);;All Files (*.*)",
            )
            if file_path:
                video_path = file_path
            else:
                print("Không có video nào được chọn. Thoát ứng dụng.")
                return 0

    window = VideoReplayWindow(video_path=video_path)
    window.show()
    window.raise_()
    window.activateWindow()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
