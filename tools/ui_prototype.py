"""Prototype giao dien vo replay - chay bang du lieu mau, khong can video (moc M1b).

    .venv\\Scripts\\python tools\\ui_prototype.py

Phim:
    1..4   doi tinh huong mau (binh thuong / khuyen doi the / mot o chua doc / thieu HUD)
    T      doi bang mau: blitz (do tu CSS that cua blitz.gg) <-> amber
    F5     nap lai src/replay/theme.py va ve lai  -> sua mau roi xem ngay, khong khoi dong lai
    Esc    thoat

Muc dich la CAN CHINH: mau, khoang cach, co chu. Khong co logic quyet dinh o day;
moi thu hien ra deu la du lieu dung san, dung kieu ma `viewmodel.build_view` tra ve.
"""

from __future__ import annotations

import importlib
from pathlib import Path
import sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PyQt6 import QtCore, QtGui, QtWidgets  # noqa: E402

from src.replay import theme, widgets  # noqa: E402
from src.replay.viewmodel import SlotVM, StripVM, VerdictVM  # noqa: E402


def scenarios() -> list[tuple[str, StripVM, VerdictVM, list[SlotVM]]]:
    """Bon tinh huong that, lay tu ban record 2026-09-16."""
    normal = (
        "3-2 · bình thường",
        StripVM(stage="3-2", level="4", xp="8/10", gold="55", hp="88", streak="-1",
                rerolls_left=2, econ="Còn 2 XP lên cấp 5: 4 vàng (1 lần mua)",
                shared=["cả ba thẻ đều từ bảng tier TFT Academy"]),
        VerdictVM("CHỌN", 1, "Dư Âm Ma Thuật+", 0.08, "điểm tốt nhất vượt ngưỡng chốt"),
        [
            SlotVM(0, "Cảm Thấy May Mắn", tier="A", rarity=2, score=0.55, rank=2,
                   reasons=["lãi tối đa 5 vàng ở 3-2", "HP 88 còn thoải mái"], reroll="available"),
            SlotVM(1, "Dư Âm Ma Thuật+", tier="S", rarity=3, score=0.63, rank=1,
                   reasons=["khớp hệ đang chạy (3 đơn vị)", "hơn #2 chủ yếu nhờ khớp hệ (+0,12)"],
                   reroll="available"),
            SlotVM(2, "Xoay Bài Tự Động", tier="B", rarity=1, score=0.41, rank=3,
                   reasons=["lệch hướng carry AP của board"], reroll="used"),
        ],
    )
    reroll = (
        "2-1 · khuyên đổi thẻ",
        StripVM(stage="2-1", level="3", xp="0/6", gold="1", hp="100", streak="0",
                rerolls_left=3, econ="Chưa đủ vàng để mua XP"),
        VerdictVM("ĐỔI", 2, "Linh Hồn Chuộc Tội", 0.09, "lợi kỳ vọng vượt chi phí làm cạn bậc"),
        [
            SlotVM(0, "Tín Đồ Tiên Hắc Ám", tier="B", rarity=1, score=0.38, rank=3,
                   reasons=["board chưa có đơn vị nào thuộc hệ này"], reroll="available"),
            SlotVM(1, "Nhà Máy Tái Chế", tier="A", rarity=1, score=0.52, rank=1,
                   reasons=["tặng mảnh trang bị, dùng được ngay"], reroll="available"),
            SlotVM(2, "Linh Hồn Chuộc Tội", tier="C", rarity=1, score=0.31, rank=2,
                   reasons=["cần tuyến đầu mới phát huy"], reroll="available"),
        ],
    )
    unread = (
        "4-2 · một ô chưa đọc được",
        StripVM(stage="4-2", level="6", xp="0/36", gold="62", hp="78", streak="3",
                rerolls_left=1, warnings=["chưa đọc được ô 2"]),
        VerdictVM("CHỌN", 2, "Túi Đồ Cỡ Đại", 0.05),
        [
            SlotVM(0, "Cứu Hồi Phục II", tier="A", rarity=2, score=0.54, rank=2,
                   reasons=["HP 78 — cần sức mạnh ngay"], reroll="used"),
            SlotVM(1, "chưa đọc được", unread=True,
                   raw_text="OCR đọc: 'Hào Quang Nhân Vt Chính' — không khớp tên nào",
                   reroll="available"),
            SlotVM(2, "Túi Đồ Cỡ Đại", tier="S", rarity=3, score=0.59, rank=1,
                   reasons=["tặng 3 mảnh + búa rèn", "đang lẻ đúng 1 mảnh, ghép được ngay"],
                   reroll="available", ambiguous=True),
        ],
    )
    stale = (
        "4-2 · HUD bị che (Team Planner)",
        StripVM(stage="4-2", level="?", xp="?/?", gold="?", hp="73", streak="?",
                rerolls_left=None, unknown=["gold", "level", "xp", "streak"],
                warnings=["số chưa đọc được: gold, level, xp, streak",
                          "dữ liệu cũ hơn patch hiện tại (2 bảng)"]),
        VerdictVM("CHỌN", 0, "Tiếp Tế Trang Bị I", 0.02),
        [
            SlotVM(0, "Tiếp Tế Trang Bị I", tier="B", rarity=1, score=0.47, rank=1,
                   reasons=["tặng trang bị hoàn chỉnh"], reroll="available", low_confidence=True),
            SlotVM(1, "Tinh Linh Hoàn Tiền+", tier="B", rarity=2, score=0.45, rank=2,
                   reasons=["giá trị kinh tế 2/3 ở 4-2 — còn 2 màn để sinh lời"], reroll="used"),
            SlotVM(2, "Phân Phối Tướng++", tier="C", rarity=1, score=0.39, rank=3,
                   reasons=["chưa có data/tier list chính xác"], reroll="used"),
        ],
    )
    return [normal, reroll, unread, stale]


class Prototype(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Prototype giao diện replay — 1..4 đổi tình huống, F5 nạp lại màu")
        self.resize(1180, 820)
        self.index = 0

        root = QtWidgets.QWidget()
        self.setCentralWidget(root)
        layout = QtWidgets.QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.hint = QtWidgets.QLabel()
        layout.addWidget(self.hint)

        self.strip = widgets.StateStrip()
        layout.addWidget(self.strip)
        self.verdict = widgets.VerdictBar()
        layout.addWidget(self.verdict)

        columns = QtWidgets.QHBoxLayout()
        columns.setSpacing(12)
        self.columns = [widgets.SlotColumn() for _ in range(3)]
        for column in self.columns:
            columns.addWidget(column, stretch=1)
        layout.addLayout(columns)

        self.video = QtWidgets.QFrame()
        self.video.setObjectName("card")
        self.video.setMinimumHeight(180)
        video_layout = QtWidgets.QVBoxLayout(self.video)
        self.video_label = QtWidgets.QLabel("video (thu gọn được)")
        self.video_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        video_layout.addWidget(self.video_label)
        layout.addWidget(self.video, stretch=1)

        controls = QtWidgets.QHBoxLayout()
        controls.setSpacing(8)
        self.offer_label = QtWidgets.QLabel("offer 2/4")
        for text in ("‹", "›"):
            btn = QtWidgets.QPushButton(text)
            btn.setFixedWidth(40)
            controls.addWidget(btn)
        controls.addWidget(self.offer_label)
        controls.addStretch()
        self.legend = QtWidgets.QLabel("● vòng chọn lõi     ▲ lần reroll")
        controls.addWidget(self.legend)
        layout.addLayout(controls)

        self.timeline = widgets.Timeline()
        self.timeline.set_data(2141, [111, 627, 1091], [132, 135, 138, 636, 645, 1099, 1100, 1101])
        self.timeline.set_position(627)
        self.timeline.seek.connect(self.timeline.set_position)
        layout.addWidget(self.timeline)

        self.apply_theme()
        self.show_scenario(0)

    def apply_theme(self) -> None:
        # CHI nap lai `theme`. Nap lai `widgets` se thay lop QWidget trong khi cac
        # widget cu van song -> Qt sap ngay (da dinh mot lan).
        active = theme.ACTIVE
        importlib.reload(theme)
        theme.apply(active)
        self.restyle()

    def restyle(self) -> None:
        self.setStyleSheet(theme.qss())
        self.verdict.restyle()
        for label, color, size in (
            (self.hint, theme.TEXT_MUTED, theme.SIZES["sm"]),
            (self.video_label, theme.TEXT_FAINT, theme.SIZES["md"]),
            (self.offer_label, theme.TEXT_2, theme.SIZES["md"]),
            (self.legend, theme.TEXT_MUTED, theme.SIZES["sm"]),
        ):
            label.setStyleSheet(f"color: {color}; font-size: {size}px; background: transparent;")

    def show_scenario(self, index: int) -> None:
        self.index = index % len(scenarios())
        name, strip, verdict, slots = scenarios()[self.index]
        self.hint.setText(
            f"Tình huống {self.index + 1}/4 — {name}   ·   bảng màu: {theme.ACTIVE}"
            "   ·   1..4 đổi tình huống · T đổi bảng màu · F5 nạp lại"
        )
        self.strip.set_data(strip)
        self.verdict.set_data(verdict)
        for column, slot in zip(self.columns, slots):
            slot.recommended = verdict.slot == slot.slot
            column.set_data(slot)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:   # noqa: N802
        key = event.key()
        if QtCore.Qt.Key.Key_1 <= key <= QtCore.Qt.Key.Key_4:
            self.show_scenario(key - QtCore.Qt.Key.Key_1)
        elif key == QtCore.Qt.Key.Key_T:
            theme.toggle()
            self.restyle()
            self.show_scenario(self.index)
        elif key == QtCore.Qt.Key.Key_F5:
            self.apply_theme()
            self.show_scenario(self.index)
        elif key in (QtCore.Qt.Key.Key_Escape, QtCore.Qt.Key.Key_Q):
            self.close()


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    window = Prototype()
    window.show()
    window.raise_()
    window.activateWindow()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
