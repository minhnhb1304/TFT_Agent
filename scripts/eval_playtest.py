"""Cham mot cach doc video doi chieu voi nhan playtest da verified (moc M0).

    # Baseline: tai hien dung hanh vi run_replay.py @ d537eb0
    python scripts/eval_playtest.py data/eval/playtest/<id>.json --video <file> --mode baseline

    # Tran tren cua bo doc the: doc MOI giay trong man (bo qua loi kich hoat)
    python scripts/eval_playtest.py data/eval/playtest/<id>.json --video <file> --mode dense

    # Cham lai mot run da luu, khong can video
    python scripts/eval_playtest.py data/eval/playtest/<id>.json --run data/eval/runs/<ts>.jsonl

Hai che do tach hai nguyen nhan cua loi #2:
    baseline thap, dense cao  -> loi o CHO NAO/KHI NAO doc (kich hoat)
    ca hai cung thap          -> loi o chinh bo doc the (OCR / khop ten)

LUU Y `dense` dung thoi diem man tu NHAN de biet quet o dau. Do la chan doan,
khong phai hanh vi san pham - khong bao cao no nhu mot ket qua cua he thong.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.capture.regions import ScreenRegions  # noqa: E402
from src.capture.video_source import VideoFrameSource  # noqa: E402
from src.eval.playtest_labels import load as load_labels  # noqa: E402
from src.eval.playtest_metrics import ReadEvent, evaluate, load_run, save_run  # noqa: E402
from src.game_state.state_tracker import GameStateTracker  # noqa: E402
from src.knowledge.name_index import NameIndex  # noqa: E402
from src.vision.hud_reader import DEFAULT_REGIONS, HudReader  # noqa: E402
from src.vision.reroll_buttons import RerollButtonReader  # noqa: E402

# Hang so cua VideoScannerThread trong run_replay.py @ d537eb0.
BASELINE_STEP_S = 4.0
BASELINE_CLUSTER_GAP_S = 25.0


def _recognizer(regions: ScreenRegions, index: NameIndex):
    # Import dung lop dang duoc do; run_replay.py import PyQt6 nhung khong can QApplication.
    from run_replay import DynamicCardRecognizer

    return DynamicCardRecognizer(regions, index)


def _cards(recognizer, image) -> tuple[tuple[str, ...], ...]:
    return tuple((c["api_name"],) if c["api_name"] else () for c in recognizer.recognize_cards(image))


def run_baseline(src, regions, index, start: float = 0.0, end: float | None = None) -> list[ReadEvent]:
    """Doc MOT lan o hit dau tien moi cum, HUD voi `or 0/1/100` - y nhu run_replay.py."""
    buttons = RerollButtonReader.load(regions)
    hud = HudReader.load(regions)
    tracker = GameStateTracker()
    recognizer = _recognizer(regions, index)

    # Doc NGAY tren khung da phat hien man, nhu seek_and_analyze(time_s) cua run_replay.
    events = []
    last_hit: float | None = None
    for frame in src.frames(start=start, end=end, fps=1.0 / BASELINE_STEP_S):
        if not buttons.read(frame.image).screen_present:
            continue
        first_of_cluster = last_hit is None or frame.t - last_hit > BASELINE_CLUSTER_GAP_S
        last_hit = frame.t
        if not first_of_cluster:
            continue
        tracker.update(hud.read(frame.image))
        st = tracker.state()
        cards = _cards(recognizer, frame.image)
        # run_replay dung gold/level/hp va KHONG dung xp -> ghi None cho xp.
        events.append(ReadEvent(frame.t, cards, {"gold": st.gold or 0, "level": st.level or 1,
                                                 "hp": st.hp or 100, "xp": None, "xp_needed": None}))
        print(f"  baseline đọc @{frame.t:.1f}s: {cards}", flush=True)
    return events


def run_dense(src, regions, index, labels) -> list[ReadEvent]:
    """Doc moi giay trong moi man da gan nhan, HUD lay tu tracker da prime truoc man."""
    buttons = RerollButtonReader.load(regions)
    hud = HudReader.load(regions)
    recognizer = _recognizer(regions, index)

    events = []
    for screen in labels.screens:
        tracker = GameStateTracker()
        for frame in src.frames(start=max(0.0, screen.open_s - 15.0), end=screen.close_s + 0.5, fps=1.0):
            tracker.update(hud.read(frame.image))
            if frame.t < screen.open_s or not buttons.read(frame.image).screen_present:
                continue
            st, unseen = tracker.state(), set(tracker.never_seen)
            hud_values = {k: (None if k in unseen else getattr(st, k)) for k in ("gold", "level", "xp", "xp_needed", "hp")}
            events.append(ReadEvent(frame.t, _cards(recognizer, frame.image), hud_values))
        print(f"  dense {screen.stage} @{screen.open_s:.1f}s xong", flush=True)
    return events


def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    except OSError:
        return "?"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Chấm cách đọc video theo nhãn playtest")
    ap.add_argument("labels")
    ap.add_argument("--video", help="bắt buộc trừ khi dùng --run")
    ap.add_argument("--mode", choices=("baseline", "dense"), default="baseline")
    ap.add_argument("--run", help="chấm lại một run .jsonl đã lưu")
    ap.add_argument("--regions", default=DEFAULT_REGIONS)
    ap.add_argument("--name-index", default="data/name_index.json")
    ap.add_argument("--allow-draft", action="store_true", help="vẫn chạy khi chưa có màn verified")
    ap.add_argument("--start", type=float, default=0.0, help="baseline: chỉ quét từ giây này")
    ap.add_argument("--end", type=float, help="baseline: chỉ quét tới giây này")
    args = ap.parse_args(argv)

    index = NameIndex.load(args.name_index)
    labels = load_labels(args.labels, known_augments=index.display.get("augments", {}).keys())
    if not labels.verified_screens and not args.allow_draft:
        print("Chưa có màn nào status=verified — sửa nhãn nháp trước, hoặc thêm --allow-draft.")
        return 1

    if args.run:
        events, mode = load_run(args.run), f"run:{Path(args.run).name}"
    else:
        if not args.video:
            ap.error("cần --video hoặc --run")
        src = VideoFrameSource(args.video)
        regions = ScreenRegions.load(args.regions)
        events = run_baseline(src, regions, index, args.start, args.end) if args.mode == "baseline" else run_dense(src, regions, index, labels)
        mode = args.mode
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        run_path = ROOT / "data" / "eval" / "runs" / f"{Path(args.labels).stem}_{mode}_{stamp}.jsonl"
        save_run(events, run_path)
        print(f"Run đã lưu: {run_path}")

    report = evaluate(labels, events).to_dict()
    report = {"labels": args.labels, "mode": mode, "commit": _commit(), **report}
    failures = report.pop("failures")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if failures:
        print(f"\n{len(failures)} lỗi (tối đa 30):")
        for f in failures[:30]:
            print(f"  - {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
