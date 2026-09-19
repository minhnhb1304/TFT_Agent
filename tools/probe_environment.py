"""Do moi truong may game TRUOC khi viet module capture (Live Phase 0, viec L0).

    # 1) Chay khi game DONG truoc - buoc 2 cua testing-protocol
    .venv\\Scripts\\python tools/probe_environment.py --closed

    # 2) Roi chay khi dang o trong mot van Normal
    .venv\\Scripts\\python tools/probe_environment.py --seconds 5

Tra loi Q1-Q7 cua docs/live-mode/phase-0-spike.md va ghi ra
`data/live_probe/<timestamp>/` (report.json + toi da 3 khung PNG).

VI SAO PHAI CHAY SOM: client TFT standalone du kien 2026-10-09 co the doi
process name / window class. Bang do o day la ban ghi DUY NHAT ve client hien
tai; khong chup bay gio thi sau nay khong con gi de so.

AN TOAN (SPEC 1.3): chi doc. Tim cua so bang tieu de/lop, khong `OpenProcess`,
khong inject, khong gui input. `tests/test_readonly_invariant.py` quet ca
thu muc `tools/` nen rang buoc nay duoc thi hanh bang test chu khong bang
loi hua. Chi chay trong van Normal, theo research/vanguard/testing-protocol.md.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import platform
import sys
import time
from datetime import datetime
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Ung vien tieu de/lop cua so. Danh sach chu KHONG phai mot hang so: chinh
# viec cai nao khop la mot ket qua can ghi lai, va sau 2026-10-09 danh sach
# nay se phai dai them.
WINDOW_CANDIDATES = (
    ("League of Legends (TM) Client", "RiotWindowClass"),
    ("Teamfight Tactics", None),
    ("League of Legends", None),
)

OUT_ROOT = ROOT / "data" / "live_probe"
BLACK_MEAN = 8.0          # duoi muc nay coi nhu khung den (capture bi chan)


# -- 1. He thong ----------------------------------------------------------

def probe_system() -> dict:
    """Q-nen: build Windows, DWM, DPI. Khong can game mo."""
    out: dict = {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "windows_build": None,
        "build_ok": None,
        "dwm_composition": None,
        "dpi_aware": None,
    }
    if not sys.platform.startswith("win"):
        out["note"] = "khong phai Windows - moi cau hoi WGC bo trong"
        return out

    try:
        version = sys.getwindowsversion()          # type: ignore[attr-defined]
        out["windows_build"] = version.build
        # WGC doi 19041 (20H1). Duoi muc do thi Phase 1 phai di duong mss.
        out["build_ok"] = version.build >= 19041
    except Exception as exc:
        out["windows_build_error"] = repr(exc)

    try:
        enabled = ctypes.c_int(0)
        ctypes.windll.dwmapi.DwmIsCompositionEnabled(ctypes.byref(enabled))
        out["dwm_composition"] = bool(enabled.value)
    except Exception as exc:
        out["dwm_composition_error"] = repr(exc)

    try:
        # PROCESS_PER_MONITOR_DPI_AWARE = 2. Khong bat thi moi toa do doc ra
        # deu bi DPI scale lam lech, va ROI se truot mot cach kho hieu.
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        out["dpi_aware"] = True
    except Exception as exc:
        out["dpi_aware"] = False
        out["dpi_error"] = repr(exc)
    return out


# -- 2-3. Cua so game -----------------------------------------------------

def probe_window(title: str | None = None) -> dict:
    """Q3, Q5, Q6-phu: hwnd, tieu de/lop that, client rect, borderless?

    `title` de ep mot tieu de cu the - can den khi client doi ten (du kien
    2026-10-09) va danh sach ung vien o tren khong con khop.
    """
    candidates = ((title, None),) + WINDOW_CANDIDATES if title else WINDOW_CANDIDATES
    out: dict = {"found": False, "candidates_tried": [t for t, _ in candidates]}
    try:
        import win32api
        import win32con
        import win32gui
    except ImportError as exc:
        out["error"] = f"thieu pywin32 ({exc}) - `pip install pywin32`"
        return out

    hwnd = 0
    for want, cls in candidates:
        hwnd = win32gui.FindWindow(cls, want) or win32gui.FindWindow(None, want)
        if hwnd:
            out["matched_by"] = {"title": want, "class": cls}
            break

    if not hwnd:
        # Khong khop ung vien nao -> liet ke cua so co the nhin thay de nguoi
        # chay tu doc ra tieu de moi. Day chinh la gia tri cua lan chay nay
        # neu client da doi ten.
        visible: list[dict] = []

        def collect(h, _):
            if win32gui.IsWindowVisible(h):
                text = win32gui.GetWindowText(h)
                if text.strip():
                    visible.append({"title": text, "class": win32gui.GetClassName(h)})

        win32gui.EnumWindows(collect, None)
        out["visible_windows"] = visible[:60]
        out["error"] = "khong tim thay cua so game - xem visible_windows"
        return out

    out["found"] = True
    out["hwnd"] = int(hwnd)
    out["title"] = win32gui.GetWindowText(hwnd)
    out["class"] = win32gui.GetClassName(hwnd)

    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    sx, sy = win32gui.ClientToScreen(hwnd, (left, top))
    out["client_rect"] = {"x": sx, "y": sy, "w": right - left, "h": bottom - top}
    out["window_rect"] = list(win32gui.GetWindowRect(hwnd))

    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    out["has_caption"] = bool(style & win32con.WS_CAPTION)

    monitor = win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)
    info = win32api.GetMonitorInfo(monitor)
    mx, my, mr, mb = info["Monitor"]
    out["monitor_rect"] = {"x": mx, "y": my, "w": mr - mx, "h": mb - my}
    # Q5: chenh lech giua window rect va client rect CHINH LA phan chrome phai
    # cat di. Bang 0 o che borderless.
    out["chrome_offset"] = {"x": sx - out["window_rect"][0], "y": sy - out["window_rect"][1]}
    out["borderless"] = (
        not out["has_caption"]
        and out["client_rect"]["w"] == out["monitor_rect"]["w"]
        and out["client_rect"]["h"] == out["monitor_rect"]["h"]
    )
    return out


# -- 4-5. Capture ---------------------------------------------------------

def probe_capture(window: dict, seconds: float, out_dir: Path) -> dict:
    """Q1, Q2, Q4, Q6, Q7: WGC co chay khong, co khung khong, khung co den khong.

    Thu WGC truoc (duong da chon trong SPEC 3.1). `windows-capture` co the
    chua cai - do KHONG phai loi: no chi duoc them vao requirements sau khi
    Q1 dat, dung theo phase-0-spike.md. Truong hop do ta bao ro va roi sang
    mss de it nhat tra loi duoc Q4.
    """
    out: dict = {"backend": None, "frames": 0, "fps": None, "first_frame_s": None}
    if not window.get("found"):
        out["error"] = "chua tim thay cua so - bo qua"
        return out

    try:
        from windows_capture import Frame, InternalCaptureControl, WindowsCapture  # noqa: F401
    except ImportError as exc:
        out["wgc_available"] = False
        out["wgc_import_error"] = repr(exc)
        out["note"] = ("windows-capture chua cai (dung y do: chi them vao requirements "
                       "sau khi Q1 dat). `pip install windows-capture==2.0.1` roi chay lai.")
        return _probe_capture_mss(window, seconds, out_dir, out)

    out["wgc_available"] = True
    out["backend"] = "windows-capture"
    frames: list = []
    started = time.perf_counter()
    first: list[float] = []

    try:
        capture = WindowsCapture(cursor_capture=False, draw_border=False,
                                 window_name=window["title"])

        @capture.event
        def on_frame_arrived(frame, capture_control):          # noqa: ANN001
            if not first:
                first.append(time.perf_counter() - started)
            if len(frames) < 3:
                frames.append(frame.frame_buffer.copy())
            if time.perf_counter() - started >= seconds:
                capture_control.stop()

        @capture.event
        def on_closed():
            pass

        capture.start()                                        # chan den khi stop()
    except Exception as exc:
        out["error"] = repr(exc)
        out["note"] = "WGC that bai - xem loi tren, roi thu duong mss"
        return _probe_capture_mss(window, seconds, out_dir, out)

    elapsed = time.perf_counter() - started
    out["frames"] = len(frames)
    out["elapsed_s"] = round(elapsed, 3)
    out["first_frame_s"] = round(first[0], 3) if first else None
    out["consent_dialog"] = False      # Q1: toi day ma khong hien dialog nao
    return _save_frames(frames, out_dir, out)


def _probe_capture_mss(window: dict, seconds: float, out_dir: Path, out: dict) -> dict:
    """Duong lui: chup theo toa do man hinh. Tra loi duoc Q4, khong duoc Q1/Q2."""
    try:
        import mss
        import numpy as np
    except ImportError as exc:
        out["mss_error"] = repr(exc)
        return out

    rect = window["client_rect"]
    box = {"left": rect["x"], "top": rect["y"], "width": rect["w"], "height": rect["h"]}
    frames: list = []
    count = 0
    started = time.perf_counter()
    with mss.mss() as sct:
        # Dung theo THOI GIAN, khong theo so khung: dung so khung lam moc thi
        # `elapsed` ngan lai va fps bao cao thanh mot con so vo nghia.
        while time.perf_counter() - started < seconds:
            shot = np.array(sct.grab(box))[:, :, :3]       # BGRA -> BGR
            count += 1
            if len(frames) < 3:
                frames.append(shot)
    elapsed = time.perf_counter() - started

    out["backend"] = "mss (du phong - KHONG tra loi duoc Q1/Q2)"
    out["frames"] = count
    out["elapsed_s"] = round(elapsed, 3)
    out["fps"] = round(count / elapsed, 2) if elapsed else None
    return _save_frames(frames, out_dir, out)


def _save_frames(frames: list, out_dir: Path, out: dict) -> dict:
    """Ghi toi da 3 khung + tra loi Q4 (khung co den khong)."""
    if not frames:
        out["black_frames"] = None
        out["error"] = out.get("error") or "khong nhan duoc khung nao"
        return out

    import cv2
    import numpy as np

    if out.get("fps") is None and out.get("elapsed_s"):
        out["fps"] = round(out["frames"] / out["elapsed_s"], 2)

    means = []
    for i, frame in enumerate(frames[:3]):
        arr = np.asarray(frame)
        if arr.ndim == 3 and arr.shape[2] == 4:
            arr = arr[:, :, :3]
        means.append(round(float(arr.mean()), 2))
        cv2.imwrite(str(out_dir / f"frame_{i}.png"), arr)
        out["frame_shape"] = list(arr.shape)

    out["frame_means"] = means
    # Q4: Riot co bat capture protection khong. Khung den nghia la co.
    out["all_black"] = all(m < BLACK_MEAN for m in means)
    return out


# -- 6. ROI co vua man hinh nay khong -------------------------------------

def probe_readers(out_dir: Path) -> dict:
    """Q-bo sung: ROI hieu chuan tren VOD 1920x1080 co dung tren may nay khong.

    Day la tin hieu THAT dau tien ve chuyen do. Khung o day la khung bat ky
    trong van, gan nhu chac chan khong phai man chon augment - nen ket qua
    mong doi la `unknown` ca ba nut. Cai can doc la: co CHAY duoc khong, va
    ROI co roi ra ngoai khung khong.
    """
    out: dict = {}
    frame_path = out_dir / "frame_0.png"
    if not frame_path.is_file():
        out["error"] = "khong co khung nao de thu"
        return out

    import cv2

    frame = cv2.imread(str(frame_path))
    if frame is None:
        out["error"] = "khung khong doc duoc"
        return out

    h, w = frame.shape[:2]
    out["source_size"] = [w, h]
    if (w, h) != (1920, 1080):
        # ROI luu theo ty le nen ve mat ky thuat khong can resize; nhung moi
        # con so hieu chuan deu do o 1920x1080, nen ghi lai de sau con biet.
        frame = cv2.resize(frame, (1920, 1080), interpolation=cv2.INTER_AREA)
        out["resized_to"] = [1920, 1080]

    try:
        from src.vision.reroll_buttons import RerollButtonReader

        reader = RerollButtonReader.load()
        reading = reader.read(frame)
        out["reroll_states"] = [b.state for b in reading.reads]
        out["reroll_screen_present"] = reading.screen_present
    except Exception as exc:
        out["reroll_error"] = repr(exc)

    try:
        from src.vision.hud_reader import HudReader

        started = time.perf_counter()
        reading = HudReader.load().read(frame)
        out["hud"] = {f.field: f.value for f in reading.fields}
        out["hud_bar_visible"] = reading.bar_visible
        # Q6-phu: do TRONG luc game dang chay. Moi con so latency khac trong
        # repo deu do tren may ranh, nen day la lan dau co so that.
        out["hud_latency_s"] = round(time.perf_counter() - started, 3)
    except Exception as exc:
        out["hud_error"] = repr(exc)
    return out


# -- 7. Khoa API ----------------------------------------------------------

def probe_keys() -> dict:
    """Q7-phu: khoa nao dang co mat. CHI True/False, khong bao gio in gia tri."""
    try:
        from src.utils.env import describe, load_env

        load_env()           # khong nap .env thi moi khoa deu bao False oan
        return describe()
    except Exception as exc:
        return {"error": repr(exc)}


# -- ket xuat -------------------------------------------------------------

def summarize(report: dict) -> list[str]:
    """Doc bao cao thanh cau tra loi cho Q1-Q7. Khong doan: thieu thi ghi '?'."""
    system, window = report["system"], report["window"]
    capture, readers = report["capture"], report["readers"]

    def mark(value) -> str:
        return "?" if value is None else ("ĐẠT" if value else "KHÔNG")

    lines = [
        f"Q1 WGC theo tiêu đề, không hộp thoại: {mark(capture.get('wgc_available') and capture.get('frames', 0) > 0)}"
        f"  (backend: {capture.get('backend')})",
        f"Q2 draw_border=False: {'đã đặt' if capture.get('wgc_available') else '?'} — xem mắt thường có viền vàng không",
        f"Q3 tiêu đề/lớp cửa sổ: {window.get('title')!r} / {window.get('class')!r}",
        f"Q4 khung không đen: {mark(None if capture.get('all_black') is None else not capture['all_black'])}"
        f"  (trung bình {capture.get('frame_means')})",
        f"Q5 chrome phải cắt: {window.get('chrome_offset')} · borderless {mark(window.get('borderless'))}",
        f"Q6 fps: {capture.get('fps')} trên {capture.get('elapsed_s')}s"
        f" · khung đầu {capture.get('first_frame_s')}s",
        f"Q7 API windows-capture: {'import được' if capture.get('wgc_available') else 'chưa cài'}",
        f"—  build Windows {system.get('windows_build')} {mark(system.get('build_ok'))}"
        f" · DWM {mark(system.get('dwm_composition'))} · DPI aware {mark(system.get('dpi_aware'))}",
        f"—  ROI trên máy này: nút {readers.get('reroll_states') or readers.get('reroll_error')}",
    ]
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Đo môi trường máy game (Live Phase 0)")
    ap.add_argument("--seconds", type=float, default=5.0, help="thời gian capture")
    ap.add_argument("--title", default=None,
                    help="ép một tiêu đề cửa sổ cụ thể (khi client đổi tên)")
    ap.add_argument("--closed", action="store_true",
                    help="chạy khi game ĐÓNG: chỉ bước 1 và 7 (bước 2 của testing-protocol)")
    args = ap.parse_args(argv)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = OUT_ROOT / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    report: dict = {
        "at": stamp,
        "mode": "closed" if args.closed else "in-game",
        "system": probe_system(),
        "keys": probe_keys(),
        "window": {},
        "capture": {},
        "readers": {},
    }

    if not args.closed:
        report["window"] = probe_window(args.title)
        report["capture"] = probe_capture(report["window"], args.seconds, out_dir)
        report["readers"] = probe_readers(out_dir)

    path = out_dir / "report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not args.closed:
        print("\n== Trả lời Q1–Q7 ==")
        for line in summarize(report):
            print("  " + line)
    print(f"\nĐã ghi: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
