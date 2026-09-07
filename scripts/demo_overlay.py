r"""Script demo Overlay ĐTCL trực tiếp trên màn hình (Cách 1).

Chạy:
    .\.venv\Scripts\python scripts/demo_overlay.py

Tính năng:
    - Bật cửa sổ Overlay trong suốt (Frameless, Translucent, Always-on-Top).
    - Hiển thị kết quả cố vấn của Advisor và thuật toán Sequential Reroll Policy.
    - Phím tắt điều khiển:
        [1]: Tình huống Vòng 2-1 (Game 1 - Midfeed APAC Final: Có lõi ngon -> Khuyên CHỌN)
        [2]: Tình huống Vòng 3-2 (3 lõi yếu -> Khuyên ĐỔI ô phế nhất)
        [3]: Tình huống Vòng 4-2 (Chặng cuối -> Khuyên ĐỔI cạn lượt)
        [ESC]: Thoát demo
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PyQt6 import QtCore, QtGui, QtWidgets
from src.decision.advisor import Advisor
from src.decision.reroll_policy import RerollState
from src.game_state.models import Champion, GameState
from src.overlay.widgets.augment_panel import create_panel

# --- Cac tinh huong demo ---
SCENARIOS = {
    "1": {
        "title": "Stage 2-1 (Chung kết Game 1 - Midfeed)",
        "state": GameState(
            gold=3,
            level=4,
            hp=100,
            stage="2-1",
            board=[
                Champion(name="Sói", cost=1, star_level=1, traits=["Quái Rừng"]),
                Champion(name="Varus", cost=1, star_level=1, traits=["Liên Kích", "Hỏa Ngục"]),
                Champion(name="Xayah", cost=1, star_level=1, traits=["Liên Kích"]),
                Champion(name="Kayle", cost=2, star_level=1, traits=["Liên Kích"]),
            ],
            active_traits={"Quái Rừng": 1, "Hỏa Ngục": 1, "Liên Kích": 2},
        ),
        "choices": ["DA_CookingPot", "DA_EarlyLearnings", "DA_18_RiftbeastTraitAugment"],
        "rerolls": RerollState(available=(True, True, True)),
    },
    "2": {
        "title": "Stage 3-2 (3 Lõi yếu, cần Roll)",
        "state": GameState(
            gold=32,
            level=6,
            hp=78,
            stage="3-2",
            board=[
                Champion(name="Shen", cost=2, star_level=2, traits=["Can Trường"]),
                Champion(name="Ahri", cost=3, star_level=1, traits=["Phù Thủy"]),
            ],
            active_traits={"Can Trường": 1, "Phù Thủy": 1},
        ),
        "choices": ["DA_BandOfThieves1", "DA_ComponentBuffet", "DA_18_RiftbeastTraitAugment"],
        "rerolls": RerollState(available=(True, True, True)),
    },
    "3": {
        "title": "Stage 4-2 (Chặng cuối - Roll cạn lượt)",
        "state": GameState(
            gold=40,
            level=8,
            hp=45,
            stage="4-2",
            board=[
                Champion(name="Varus", cost=4, star_level=2, traits=["Liên Kích", "Hỏa Ngục"]),
                Champion(name="Nasus", cost=4, star_level=2, traits=["Hỏa Ngục", "Can Trường"]),
            ],
            active_traits={"Hỏa Ngục": 4, "Liên Kích": 2, "Can Trường": 2},
        ),
        "choices": ["DA_ComponentBuffet", "DA_BandOfThieves1", "DA_18_RiftbeastTraitAugment"],
        "rerolls": RerollState(available=(True, True, True)),
    },
}


class DemoController(QtWidgets.QWidget):
    def __init__(self, advisor: Advisor):
        super().__init__()
        self.advisor = advisor
        self.current_key = "1"

        self.setWindowTitle("TFT Agent - Live Overlay Controller")
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        # Layout chinh
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Help hint banner
        self.help_label = QtWidgets.QLabel()
        self.help_label.setStyleSheet(
            "background-color: rgba(15, 20, 30, 230); color: #88ccff; padding: 6px 12px; font-weight: bold; font-size: 13px; border-radius: 4px; border: 1px solid #335577;"
        )

        # Panel Overlay
        self.panel = create_panel(self)
        self.panel.resize(460, 320)

        layout.addWidget(self.help_label, alignment=QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.panel, alignment=QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignRight)

        self.load_scenario("1")

    def load_scenario(self, key: str):
        if key not in SCENARIOS:
            return
        self.current_key = key
        sc = SCENARIOS[key]

        # Goi Advisor
        bundle = self.advisor.advise(
            state=sc["state"], choices=sc["choices"], rerolls=sc["rerolls"]
        )
        self.panel.set_ranking(bundle.ranking, bundle.reroll)
        self.help_label.setText(
            f"[{key}] {sc['title']}  |  Phím: [1], [2], [3] đổi tình huống  |  [ESC] Thoát"
        )
        self.adjustSize()

    def keyPressEvent(self, event: QtGui.QKeyEvent):  # noqa: N802
        key = event.key()
        if key == QtCore.Qt.Key.Key_Escape:
            QtWidgets.QApplication.quit()
        elif key == QtCore.Qt.Key.Key_1:
            self.load_scenario("1")
        elif key == QtCore.Qt.Key.Key_2:
            self.load_scenario("2")
        elif key == QtCore.Qt.Key.Key_3:
            self.load_scenario("3")


def main():
    app = QtWidgets.QApplication(sys.argv)
    advisor = Advisor()

    # Lay kich thuoc man hinh
    screen = app.primaryScreen().geometry()

    demo = DemoController(advisor)
    # Dat overlay o goc tren ben phai man hinh
    w, h = 480, 380
    demo.setGeometry(screen.width() - w - 25, 35, w, h)
    demo.show()

    print("\n" + "=" * 60)
    print(">>> OVERLAY DEMO DANG CHAY TREN MAN HINH CUA BAN! <<<")
    print(" - Nhin vao goc tren ben phai man hinh may tinh.")
    print(" - Bam phim [1], [2], [3] tren ban phim de chuyen cac tinh huong.")
    print(" - Bam phim [ESC] de dong overlay.")
    print("=" * 60 + "\n")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
