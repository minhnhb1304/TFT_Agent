"""Probe nhanh co timeout - chay khi game dang mo.

    .venv\\Scripts\\python tools/probe_quick.py

Kiem tra:
  1. windows-capture co import duoc khong
  2. Cua so TFT co tim thay khong (liet ke visible windows)
  3. Thu mss grab voi timeout 10s
"""
from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

report: dict = {}

# --- 1. windows-capture ---
try:
    from windows_capture import WindowsCapture  # noqa: F401
    report["wgc_importable"] = True
except ImportError as e:
    report["wgc_importable"] = False
    report["wgc_error"] = repr(e)

# --- 2. Tim cua so ---
try:
    # Dung chung bo do cua so voi probe_environment de hai script khong lech
    # danh sach ung vien.
    from tools.probe_environment import probe_window

    window = probe_window()
    report["window_found"] = window["found"]
    if window["found"]:
        report["window_title"] = window["title"]
        report["window_class"] = window["class"]
        report["client_rect"] = window["client_rect"]
    else:
        for key in ("error", "skipped_small", "visible_windows"):
            if key in window:
                report[key] = window[key]

except Exception as e:
    report["window_error"] = repr(e)

# --- 3. mss grab voi timeout ---
if report.get("window_found") and report.get("client_rect"):
    result: dict = {}
    rect = report["client_rect"]

    def _try_grab():
        try:
            import mss
            import numpy as np
            box = {"left": rect["x"], "top": rect["y"],
                   "width": rect["w"], "height": rect["h"]}
            with mss.mss() as sct:
                t0 = time.perf_counter()
                shot = np.array(sct.grab(box))[:, :, :3]
                result["ok"] = True
                result["elapsed_s"] = round(time.perf_counter() - t0, 3)
                result["shape"] = list(shot.shape)
                result["mean"] = round(float(shot.mean()), 2)
        except Exception as e:
            result["error"] = repr(e)

    t = threading.Thread(target=_try_grab, daemon=True)
    t0 = time.perf_counter()
    t.start()
    t.join(timeout=10)
    if t.is_alive():
        result["error"] = "MSS TREO - join timeout 10s"
    result["total_elapsed_s"] = round(time.perf_counter() - t0, 3)
    report["mss_grab"] = result

print(json.dumps(report, ensure_ascii=False, indent=2))
