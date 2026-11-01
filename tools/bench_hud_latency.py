"""Do do tre doc HUD, chia theo tung truong va tung khau OCR (det / cls / rec).

Probe 2026-10-15 do duoc 15-26 s moi lan doc HUD khi game chay (may ranh ~1,1 s)
nhung chi co tong thoi gian. Script nay tach tong do ra de biet thoi gian don vao dau.

    .venv\\Scripts\\python tools\\bench_hud_latency.py                  # khung probe co thanh HUD
    .venv\\Scripts\\python tools\\bench_hud_latency.py --burn 14        # gia lap CPU ban (game)
    .venv\\Scripts\\python tools\\bench_hud_latency.py --threads 2      # gioi han luong onnxruntime
    .venv\\Scripts\\python tools\\bench_hud_latency.py --variant rec-only

Moi lan doc dung HudReader MOI (cache theo o se lam lan doc thu hai gan nhu 0 ms).
Ket qua ghi vao data/live_probe/bench/<thoi diem>.json.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import platform
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_FRAMES = [
    "data/live_probe/20261015_165242/frame_0.png",
    "data/live_probe/20261015_165627/frame_0.png",
]
OUT_DIR = ROOT / "data" / "live_probe" / "bench"


def _burn(stop) -> None:                                      # noqa: ANN001
    while not stop.is_set():
        sum(i * i for i in range(10_000))


def _make_engine(threads: int | None):
    from rapidocr import RapidOCR

    if threads is None:
        return RapidOCR()
    return RapidOCR(params={
        "EngineConfig.onnxruntime.intra_op_num_threads": threads,
        "EngineConfig.onnxruntime.inter_op_num_threads": 1,
    })


class TimedCall:
    """Boc engine: ghi lai kich thuoc anh, tong thoi gian va elapse det/cls/rec moi lan goi."""

    def __init__(self, eng, variant: str) -> None:            # noqa: ANN001
        self.eng = eng
        self.variant = variant
        self.calls: list[dict] = []

    def __call__(self, img):                                  # noqa: ANN001
        started = time.perf_counter()
        if self.variant == "rec-only":
            result = self.eng(img, use_det=False, use_cls=False)
        else:
            result = self.eng(img)
        wall = time.perf_counter() - started
        parts = getattr(result, "elapse_list", None)
        if self.variant == "rec-only":
            parts = [0.0, 0.0, getattr(result, "elapse", wall) or wall]
        self.calls.append({
            "shape": list(img.shape[:2]),
            "wall_ms": round(wall * 1000, 1),
            "det_ms": round(parts[0] * 1000, 1) if parts else None,
            "cls_ms": round(parts[1] * 1000, 1) if parts else None,
            "rec_ms": round(parts[2] * 1000, 1) if parts else None,
        })
        return result


def bench(frames: list[Path], reps: int, threads: int | None, variant: str) -> dict:
    import cv2

    from src.vision.hud_reader import HudReader

    timed = TimedCall(_make_engine(threads), variant)
    out: dict = {"frames": {}}
    for path in frames:
        frame = cv2.imread(str(path))
        if frame is None:
            raise SystemExit(f"khong doc duoc khung: {path}")
        HudReader.load(call=timed).read(frame)                # lan nap dau, khong tinh
        timed.calls.clear()

        reads, values = [], {}
        for _ in range(reps):
            reader = HudReader.load(call=timed)
            started = time.perf_counter()
            reading = reader.read(frame)
            reads.append(round((time.perf_counter() - started) * 1000, 1))
            values = {f.field: f.value for f in reading.fields}
        calls = list(timed.calls)
        timed.calls.clear()

        per_read = len(calls) // reps if reps else 0
        out["frames"][str(path)] = {
            "read_ms": reads,
            "read_ms_median": statistics.median(reads),
            "ocr_calls_per_read": per_read,
            "det_ms_total": round(sum(c["det_ms"] or 0 for c in calls) / reps, 1),
            "cls_ms_total": round(sum(c["cls_ms"] or 0 for c in calls) / reps, 1),
            "rec_ms_total": round(sum(c["rec_ms"] or 0 for c in calls) / reps, 1),
            "calls_one_read": calls[:per_read],
            "values": values,
        }
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--frames", nargs="*", default=DEFAULT_FRAMES)
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--burn", type=int, default=0, help="so tien trinh dot CPU (gia lap game)")
    ap.add_argument("--threads", type=int, default=None, help="intra_op_num_threads cua onnxruntime")
    ap.add_argument("--variant", choices=["full", "rec-only"], default="full")
    args = ap.parse_args(argv)

    stop = mp.Event()
    burners = [mp.Process(target=_burn, args=(stop,), daemon=True) for _ in range(args.burn)]
    for p in burners:
        p.start()
    try:
        result = bench([ROOT / f for f in args.frames], args.reps, args.threads, args.variant)
    finally:
        stop.set()
        for p in burners:
            p.join(timeout=2)

    result["config"] = {
        "reps": args.reps, "burn": args.burn, "threads": args.threads, "variant": args.variant,
        "cpu_count": os.cpu_count(), "platform": platform.platform(), "python": platform.python_version(),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUT_DIR / f"{stamp}_{args.variant}_b{args.burn}_t{args.threads or 'auto'}.json"
    path.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")

    for name, f in result["frames"].items():
        print(f"{Path(name).parent.name}: doc HUD trung vi {f['read_ms_median']:.0f} ms, "
              f"{f['ocr_calls_per_read']} luot OCR | det {f['det_ms_total']:.0f} · "
              f"cls {f['cls_ms_total']:.0f} · rec {f['rec_ms_total']:.0f} ms | {f['values']}")
    print(f"-> {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
