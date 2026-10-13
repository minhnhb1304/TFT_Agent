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
    import win32gui

    CANDIDATES = [
        ("League of Legends (TM) Client", "RiotWindowClass"),
        ("Teamfight Tactics", None),
        ("League of Legends", None),
    ]

    hwnd = 0
    matched = None
    for title, cls in CANDIDATES:
        hwnd = win32gui.FindWindow(cls, title) or win32gui.FindWindow(None, title)
        if hwnd:
            matched = title
            break

    if hwnd:
        report["window_found"] = True
        report["window_title"] = win32gui.GetWindowText(hwnd)
        report["window_class"] = win32gui.GetClassName(hwnd)
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        sx, sy = win32gui.ClientToScreen(hwnd, (left, top))
        report["client_rect"] = {"x": sx, "y": sy, "w": right - left, "h": bottom - top}
    else:
        report["window_found"] = False
        visible: list[dict] = []

        def _collect(h, _):
            if win32gui.IsWindowVisible(h):
                t = win32gui.GetWindowText(h)
                if t.strip():
                    visible.append({"title": t, "class": win32gui.GetClassName(h)})

        win32gui.EnumWindows(_collect, None)
        report["visible_windows"] = visible[:60]

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
