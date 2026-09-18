"""TFT Advisory Agent - trinh xem lai ban record kem co van.

    .venv\\Scripts\\python run_replay.py --video "D:\\tft_records\\van1.mp4"
    .venv\\Scripts\\python run_replay.py --video <file> --card-reader gemini

Tu moc M1 (docs/playtest-fixes/core-session.md), file nay chi con la VO:
toan bo phan quyet dinh nam trong `src/live/LiveSession` - dung lop ma vo live
(overlay trong tran) se dung. Nho the hanh vi tren ban record bang hanh vi
trong tran, va mot lan sua loi doc the co hieu luc cho ca hai.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Xem lại bản record kèm cố vấn lõi")
    ap.add_argument("--video", "-v", help="đường dẫn video (.mp4, .mkv)")
    ap.add_argument("--regions", default="config/screen_regions.yaml")
    ap.add_argument("--card-reader", choices=("ocr", "gemini"), default="ocr")
    ap.add_argument("--analysis-fps", type=float, default=5.0,
                    help="số lần đọc mỗi giây video khi đang phát")
    ap.add_argument("--palette", default="neon",
                    help="bảng màu: neon, ember, citrus, magenta, hextech, geist, linear, semi, teal, violet")
    args = ap.parse_args(argv)

    from PyQt6 import QtWidgets  # noqa: PLC0415 - nap tre de --help khong can Qt

    from src.replay.window import ReplayWindow  # noqa: PLC0415

    app = QtWidgets.QApplication(sys.argv)
    video = args.video
    if not video:
        video, _ = QtWidgets.QFileDialog.getOpenFileName(
            None, "Chọn video trận đấu", str(ROOT), "Video (*.mp4 *.mkv *.avi *.mov)"
        )
        if not video:
            print("Chưa chọn video nào.")
            return 0

    window = ReplayWindow(
        video,
        regions_path=args.regions,
        card_reader=args.card_reader,
        analysis_fps=args.analysis_fps,
        palette=args.palette,
    )
    window.show()
    window.raise_()
    window.activateWindow()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
