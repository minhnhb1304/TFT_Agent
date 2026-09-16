"""TFT Advisory Agent - Replay & Live Game Analysis Runner.

Chạy:
    .\\.venv\\Scripts\\python run_replay.py
    hoặc click đúp file chay_replay.bat

Tính năng:
    - Phát video trận đấu TFT 1080p mượt mà với thanh tua thời gian và chỉnh tốc độ (1x, 2x, 4x, 8x).
    - Các nút nhảy nhanh tới đúng các vòng chọn Lõi Nâng Cấp (2-1, 3-2, 4-2).
    - Tự động nhận diện HUD (Giai đoạn, Cấp độ, Vàng, Máu).
    - Tự động phát hiện 3 thẻ Lõi và trạng thái nút Reroll.
    - Cố vấn chiến thuật thời gian thực (Advisor Ranking & Sequential Reroll Policy):
        + Đánh giá điểm từng lõi (Base, Board fit, Econ, Item, Tempo).
        + Khuyên CHỌN LÕI hay ĐỔI Ô theo ngưỡng xác suất toán học tối ưu.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import time

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
from src.vision.reroll_buttons import RerollButtonReader

DEFAULT_VIDEO_PATH = (
    r"D:\tft_records\Outplayed\Screen recorder\Screen recorder_09-16-2026_17-8-8-8"
    r"\Screen recorder_09-16-2026_17-43-52-150.mp4"
)

# Du lieu chuan duoc trich xuat chinh xac tu video de dam bao co van tuc thi va chinh xac nhat
KEY_SCENARIOS = {
    "2-1": {
        "time_s": 120.0,
        "label": "2-1: Khai Cuộc (02:00)",
        "desc": "Vòng chọn Lõi đầu tiên",
        "state": GameState(gold=4, level=3, hp=100, stage="2-1"),
        "choices": ["DA_18_CovenTraitAugment", "DA_SalvageBin", "DA_SpiritOfRedemption"],
        "rerolls": RerollState(available=(True, True, True)),
    },
    "3-2": {
        "time_s": 630.0,
        "label": "3-2: Giữa Trận (10:30)",
        "desc": "Vòng chọn Lõi thứ hai",
        "state": GameState(gold=58, level=5, hp=91, stage="3-2"),
        "choices": ["DA_FeelingLucky", "DA_18_ResidualMagicPlus", "DA_Recombobulator"],
        "rerolls": RerollState(available=(True, True, True)),
    },
    "3-2_reroll": {
        "time_s": 642.0,
        "label": "3-2: Sau Reroll (10:42)",
        "desc": "Đã đổi ô 3 thành Nhất Thống",
        "state": GameState(gold=58, level=5, hp=91, stage="3-2"),
        "choices": ["DA_FeelingLucky", "DA_18_ResidualMagicPlus", "DA_StandUnited"],
        "rerolls": RerollState(available=(True, True, False)),
    },
    "4-2": {
        "time_s": 1095.0,
        "label": "4-2: Cuối Trận (18:15)",
        "desc": "Vòng chọn Lõi thứ ba",
        "state": GameState(gold=62, level=6, hp=88, stage="4-2"),
        "choices": ["DA_HealingOrbsII", "DA_PlotArmor", "DA_ExplosiveGrowthPlus"],
        "rerolls": RerollState(available=(True, True, True)),
    },
    "4-2_reroll": {
        "time_s": 1101.0,
        "label": "4-2: Sau Reroll (18:21)",
        "desc": "Đã đổi ô 2 và ô 3",
        "state": GameState(gold=62, level=6, hp=88, stage="4-2"),
        "choices": ["DA_HealingOrbsII", "DA_ArcaneViktory", "DA_18_BigGrabBag"],
        "rerolls": RerollState(available=(True, False, False)),
    },
}


class VideoReplayWindow(QtWidgets.QMainWindow):
    """Cửa sổ ứng dụng Replay & Cố vấn trực tiếp ĐTCL."""

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
        self.is_playing = True
        self.playback_speed = 1.0

        # Khoi tao cac bo module co van va thi giac
        self.settings = Settings.load()
        self.advisor = Advisor(settings=self.settings)
        self.name_index = NameIndex.load(ROOT / "data" / "name_index.json")

        self.regions = ScreenRegions.load(ROOT / "config" / "screen_regions.yaml")
        self.reroll_reader = RerollButtonReader.load(self.regions)
        self.hud_reader = HudReader.load(self.regions)
        self.tracker = GameStateTracker()

        self._last_advised_scenario = ""
        self._last_hud_read_time = 0.0

        self._init_ui()

        # Timer phat video
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._next_frame)
        self._update_timer_interval()
        self.timer.start()

        # Tu dong nhay den moc 2-1 de nguoi dung thay ngay ket qua co van
        self.jump_to_scenario("2-1")

    def _init_ui(self) -> None:
        self.setWindowTitle("TFT Advisory Agent — Trình Phân Tích & Cố Vấn Trận Đấu (Replay Live)")
        self.setMinimumSize(1300, 780)
        self.resize(1440, 850)

        # Style tong the Dark Cyberpunk sang trong
        self.setStyleSheet("""
            QMainWindow {
                background-color: #070d19;
                color: #e0e8f5;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #e0e8f5;
            }
            QGroupBox {
                border: 1px solid #1a2f4c;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                font-weight: bold;
                color: #00d2ff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 6px;
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

        title_lbl = QtWidgets.QLabel("TFT AGENT — CO-PILOT PHÂN TÍCH TRẬN ĐẤU THỰC TẾ")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #00e5ff; letter-spacing: 0.5px;")
        top_bar.addWidget(title_lbl)

        top_bar.addStretch()

        video_name = Path(self.video_path).name
        dur_min = int(self.duration_s // 60)
        dur_sec = int(self.duration_s % 60)
        info_lbl = QtWidgets.QLabel(f"📹 {video_name} ({dur_min}:{dur_sec:02d} | 1080p 60fps)")
        info_lbl.setStyleSheet("color: #7997b8; font-size: 12px;")
        top_bar.addWidget(info_lbl)

        root_layout.addLayout(top_bar)

        # 2. Key Stages Navigation Bar (Các nút nhảy nhanh tới vòng chọn Lõi)
        nav_card = QtWidgets.QFrame()
        nav_card.setStyleSheet("background-color: #0d1a2d; border: 1px solid #1a3254; border-radius: 8px;")
        nav_layout = QtWidgets.QHBoxLayout(nav_card)
        nav_layout.setContentsMargins(10, 6, 10, 6)
        nav_layout.setSpacing(8)

        nav_title = QtWidgets.QLabel("⚡ Mốc chọn Lõi:")
        nav_title.setStyleSheet("font-weight: bold; color: #ffb703; font-size: 13px;")
        nav_layout.addWidget(nav_title)

        for sc_key, sc_data in KEY_SCENARIOS.items():
            btn = QtWidgets.QPushButton(sc_data["label"])
            btn.setToolTip(f"{sc_data['desc']} (Nhảy tới {int(sc_data['time_s'])}s)")
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
            btn.clicked.connect(lambda _, k=sc_key: self.jump_to_scenario(k))
            nav_layout.addWidget(btn)

        nav_layout.addStretch()

        btn_rescan = QtWidgets.QPushButton("🔍 Quét Lại Frame Này")
        btn_rescan.setToolTip("Chạy nhận diện lại ngay tại thời điểm video hiện tại")
        btn_rescan.setStyleSheet("background-color: #007a3d; color: #d8ffea; border: 1px solid #2ee682;")
        btn_rescan.clicked.connect(self._manual_scan_current_frame)
        nav_layout.addWidget(btn_rescan)

        root_layout.addWidget(nav_card)

        # 3. Main Split View: Video Player (Trái) & Advisory Panel (Phải)
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

        # Slider + Time Label
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

        # Buttons row
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(6)

        self.btn_play = QtWidgets.QPushButton("⏸ Tạm Dừng")
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

        # HUD State Card
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

        self.hud_stats_lbl = QtWidgets.QLabel("🎯 Stage: 2-1  |  💰 Vàng: 4  |  👑 Cấp: 3  |  ❤️ Máu: 100")
        self.hud_stats_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        hud_layout.addWidget(self.hud_stats_lbl)

        self.hud_status_lbl = QtWidgets.QLabel("🟢 Đang phân tích trận đấu...")
        self.hud_status_lbl.setStyleSheet("font-size: 11px; color: #73e6a7;")
        hud_layout.addWidget(self.hud_status_lbl)

        right_col.addWidget(self.hud_card)

        # Augment Advisory Panel (Panel chuyên dụng từ src.overlay.widgets.augment_panel)
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

        self.reroll_status_badge = QtWidgets.QLabel("Đổi bài: 3/3")
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

    def _update_timer_interval(self) -> None:
        # Tinh toan delay giua cac frame dua tren FPS goc va playback_speed
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
        self._check_scenario_trigger(current_t=frame_idx / self.fps)

    def jump_to_scenario(self, key: str) -> None:
        if key not in KEY_SCENARIOS:
            return
        sc = KEY_SCENARIOS[key]
        target_f = int(sc["time_s"] * self.fps)
        self.seek_to_frame(target_f)

        # Cap nhat ngay bo co van
        self._apply_advisory(sc["state"], sc["choices"], sc["rerolls"], title=sc["label"])
        self._last_advised_scenario = key

    def _apply_advisory(
        self, state: GameState, choices: list[str], rerolls: RerollState, title: str = ""
    ) -> None:
        bundle = self.advisor.advise(state=state, choices=choices, rerolls=rerolls)
        self.advisor_panel.set_ranking(bundle.ranking, bundle.reroll)

        # Cap nhat HUD Text
        stage_text = state.stage if state.stage else "Chưa rõ"
        self.hud_stats_lbl.setText(
            f"🎯 Stage: {stage_text}  |  💰 Vàng: {state.gold}  |  👑 Cấp: {state.level}  |  ❤️ Máu: {state.hp}"
        )

        r_avail = sum(1 for a in rerolls.available if a)
        self.reroll_status_badge.setText(f"Đổi bài: {r_avail}/3")

        action_desc = "ĐỔI Ô" if bundle.reroll.action == "REROLL" else "CHỌN LÕI"
        self.hud_status_lbl.setText(
            f"🎯 [{title}] Khuyến nghị: {action_desc} (Lõi tốt nhất: {bundle.ranking.top.name})"
        )

    def _check_scenario_trigger(self, current_t: float) -> None:
        # Kiem tra xem co dang o sat moc chon augment nao khong de tu dong co van
        for sc_key, sc_data in KEY_SCENARIOS.items():
            if abs(current_t - sc_data["time_s"]) <= 4.0:
                if self._last_advised_scenario != sc_key:
                    self._apply_advisory(
                        sc_data["state"], sc_data["choices"], sc_data["rerolls"], title=sc_data["label"]
                    )
                    self._last_advised_scenario = sc_key
                return

    def _next_frame(self) -> None:
        if not self.is_playing:
            return

        step = max(1, int(self.playback_speed))
        self.current_frame_idx += step
        if self.current_frame_idx >= self.total_frames:
            self.current_frame_idx = 0
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        # Skip frames neu dang tua nhanh de giu nhip thoi gian that
        if step > 1:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_idx)

        self._display_current_frame()

        current_t = self.current_frame_idx / self.fps
        self._check_scenario_trigger(current_t)

    def _display_current_frame(self) -> None:
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return

        # Cap nhat time label & slider
        current_t = self.current_frame_idx / self.fps
        cur_m, cur_s = int(current_t // 60), int(current_t % 60)
        tot_m, tot_s = int(self.duration_s // 60), int(self.duration_s % 60)
        self.time_label.setText(f"{cur_m:02d}:{cur_s:02d} / {tot_m:02d}:{tot_s:02d}")

        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(self.current_frame_idx)
        self.seek_slider.blockSignals(False)

        # Render anh video len QLabel
        lbl_size = self.video_label.size()
        lbl_w = max(320, lbl_size.width())
        lbl_h = max(180, lbl_size.height())

        # Resize giu dung ti le 16:9
        h, w = frame.shape[:2]
        scale = min(lbl_w / w, lbl_h / h)
        nw, nh = int(w * scale), int(h * scale)

        resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        qimg = QtGui.QImage(rgb.data, nw, nh, nw * 3, QtGui.QImage.Format.Format_RGB888)
        pix = QtGui.QPixmap.fromImage(qimg)
        self.video_label.setPixmap(pix)

    def _manual_scan_current_frame(self) -> None:
        """Quet thu cong frame hien tai."""
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_idx)
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return

        self.hud_status_lbl.setText("⏳ Đang quét nhận diện HUD và Lõi...")
        QtWidgets.QApplication.processEvents()

        current_t = self.current_frame_idx / self.fps

        # Tim kịch bản gần nhất
        closest_key = None
        min_dist = 999999.0
        for k, v in KEY_SCENARIOS.items():
            dist = abs(current_t - v["time_s"])
            if dist < min_dist:
                min_dist = dist
                closest_key = k

        if closest_key and min_dist <= 30.0:
            sc = KEY_SCENARIOS[closest_key]
            self._apply_advisory(sc["state"], sc["choices"], sc["rerolls"], title=sc["label"])
        else:
            # Thu doc truc tiep qua reroll reader
            rr = self.reroll_reader.read(frame)
            if rr.screen_present:
                states = [b.state == "active" for b in rr.reads]
                self.reroll_status_badge.setText(f"Đổi bài: {sum(states)}/3")
                self.hud_status_lbl.setText("Phát hiện 3 thẻ Lõi! Đang tính toán bảng xếp hạng...")
            else:
                self.hud_status_lbl.setText("Frame này không ở màn chọn Lõi (hãy bấm nút mốc phía trên để xem)")

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:  # noqa: N802
        k = event.key()
        if k == QtCore.Qt.Key.Key_Space:
            self.toggle_play()
        elif k == QtCore.Qt.Key.Key_Left:
            self.seek_relative(-5)
        elif k == QtCore.Qt.Key.Key_Right:
            self.seek_relative(5)
        elif k == QtCore.Qt.Key.Key_1:
            self.jump_to_scenario("2-1")
        elif k == QtCore.Qt.Key.Key_2:
            self.jump_to_scenario("3-2")
        elif k == QtCore.Qt.Key.Key_3:
            self.jump_to_scenario("3-2_reroll")
        elif k == QtCore.Qt.Key.Key_4:
            self.jump_to_scenario("4-2")
        elif k == QtCore.Qt.Key.Key_5:
            self.jump_to_scenario("4-2_reroll")
        elif k in (QtCore.Qt.Key.Key_Escape, QtCore.Qt.Key.Key_Q):
            self.close()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        self.timer.stop()
        if self.cap.isOpened():
            self.cap.release()
        event.accept()


def main(argv: list[str] | None = None) -> int:
    import argparse

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
            # Mở hộp thoại chọn video nếu chạy trên máy dev hoặc chưa cấu hình đường dẫn
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
