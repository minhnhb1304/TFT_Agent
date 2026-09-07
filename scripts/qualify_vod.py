"""Cham diem mot VOD ung vien TRUOC khi bo cong xu ly (SPEC 12).

    python scripts/qualify_vod.py --video "<vod>"
    python scripts/qualify_vod.py --video "<vod>" --samples 40 --json

VI SAO PHAI CO CONG NAY

Mot VOD 5 gio ton ~15 phut quet va ~1 gio cong nguoi. Phat hien no khong dung
duoc SAU khi da gan nhan la mat ca hai. Cac tieu chi duoi day deu rut ra tu do
that tren VOD dau tien (vQDqc9eiDpk, 2026-09-06), khong phai doan.

DIEU BAT NGO NHAT: BITRATE KHONG PHAI RANG BUOC

Do duoc: o 3,74 Mbps / 1080p60 (0,030 bpp), RapidOCR van doc DUNG `gold` va
`xp` truc tiep, va doc dung `stage` sau khi nhi phan hoa Otsu. Cai HONG la
tieng Viet co dau - va no hong CA TREN ANH SACH khong nen: charset cua
PP-OCRv6_rec_small thieu 33/35 ky tu dau chong tang (ắ ễ ộ ừ...) va toan bo
dau hoi/nang. 82% ten augment Set 18 co it nhat mot ky tu nhu vay.

=> Nguong bitrate chi can du cho CHU SO. Ten augment phai di duong Gemini
   Vision (SPEC 9.3) bat ke bitrate bao nhieu.

30 FPS TOT HON 60 FPS

Cung mot bitrate, 30fps cho gap doi so bit moi khung. HUD la chu tinh - ta
khong can 60fps. Khi chon dinh dang, uu tien 30fps.

KHONG DO DUOC THI PHAI TRUOT, KHONG DUOC DAT (sua 2026-09-07)

Ban dau muc "khong vien den" viet la `all(c == want for c in crops if c)`.
Khi ffmpeg khong chay duoc thi moi phan tu deu None, bieu thuc thanh
`all([])` = **True** - tuc la mot may KHONG CO ffmpeg se bao "khong vien den:
DAT". Do la loai im lang te nhat: cong kiem tra bao DAT chinh vi no khong
kiem duoc gi. Gio thieu du lieu la HONG, kem ly do.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from src.capture.video_source import VideoFrameSource, VideoSourceError  # noqa: E402

# Nguong rut ra tu VOD dau tien. Xem docstring de biet vi sao chung o day.
MIN_BPP = 0.025          # vQDqc9eiDpk = 0,0301 va doc duoc chu so -> lay san 0,025
GOOD_BPP = 0.060         # 30fps cung bitrate se roi vao khoang nay
MIN_HEIGHT = 1080
ASPECT = 16 / 9
ASPECT_TOL = 0.02
MAX_FPS = 31             # 30fps cho gap doi bit/khung so voi 60
MIN_DURATION_S = 3600
# Do KHI thanh HUD co hien. Tren VOD dau tien: 57/57 = 100%. Khung khong co
# thanh HUD (vong carousel, dang xem board nguoi khac, man loading) KHONG
# duoc tinh la truot - do la tu ha diem minh mot cach vo nghia.
MIN_HUD_READ_RATE = 0.90
MIN_HUD_PRESENT_RATE = 0.50
# Dem hai dau moi van khi lay mau: bo man loading va man ket tran.
GAME_EDGE_PAD_S = 60.0


@dataclass(frozen=True)
class Check:
    """Mot tieu chi da cham."""

    name: str
    ok: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"ten": self.name, "dat": self.ok, "chi_tiet": self.detail}


def _cropdetect(path: str, at: float, ffmpeg: str = "ffmpeg") -> str | None:
    """Chuoi `crop=...` cuoi cung, hoac None khi khong do duoc.

    None nghia la KHONG BIET, khong phai "khong co vien den" - nguoi goi phai
    phan biet hai cai do (xem docstring dau file).
    """
    try:
        proc = subprocess.run(
            [ffmpeg, "-v", "info", "-ss", f"{max(0.0, at):.0f}", "-i", path,
             "-t", "3", "-vf", "cropdetect=limit=24:round=2:reset=0",
             "-f", "null", "-"],
            capture_output=True,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return None
    hits = [tok for line in proc.stderr.decode("utf-8", "replace").splitlines()
            for tok in line.split() if tok.startswith("crop=")]
    return hits[-1] if hits else None


def container_checks(
    width: int, height: int, fps: float, bit_rate: int, duration: float,
    bit_rate_source: str = "?",
) -> list[Check]:
    """Tieu chi doc duoc tu sieu du lieu container."""
    aspect = width / height if height else 0.0
    checks = [Check(
        "do phan giai",
        height >= MIN_HEIGHT and abs(aspect - ASPECT) <= ASPECT_TOL,
        f"{width}x{height} (ti le {aspect:.3f}) - can cao >= {MIN_HEIGHT} va 16:9. "
        "ROI luu dang ti le nen do phan giai cao hon van dung duoc.",
    )]

    if fps <= 0:
        checks.append(Check("nhip khung", False,
                            "ffprobe khong bao fps - container hong?"))
    else:
        checks.append(Check("nhip khung", fps <= MAX_FPS,
                            f"{fps:.0f} fps - 30 cho gap doi bit/khung so voi 60"))

    if bit_rate <= 0 or fps <= 0 or width <= 0 or height <= 0:
        checks.append(Check(
            "bit tren pixel", False,
            "khong suy ra duoc bitrate (stream, format va size/duration deu trong)",
        ))
    else:
        bpp = bit_rate / (width * height * fps)
        checks.append(Check(
            "bit tren pixel", bpp >= MIN_BPP,
            f"{bpp:.4f} bpp ({bit_rate/1e6:.2f} Mbps @ {fps:.0f}fps, nguon "
            f"'{bit_rate_source}') - san {MIN_BPP}, tot {GOOD_BPP}",
        ))

    checks.append(Check(
        "thoi luong", duration >= MIN_DURATION_S,
        f"{duration/3600:.2f} gio (can >= {MIN_DURATION_S/3600:.0f} gio "
        "de boi duoc vai van)",
    ))
    return checks


def letterbox_check(
    path: str, duration: float, width: int, height: int,
    detector: Callable[[str, float], str | None] = _cropdetect,
) -> Check:
    """Co vien den khong. KHONG DO DUOC = HONG, khong phai mac dinh DAT."""
    if duration <= 0:
        return Check("khong vien den", False, "thoi luong bang 0 - khong lay mau duoc")
    seen = [detector(path, duration * f) for f in (0.2, 0.5, 0.8)]
    found = [c for c in seen if c]
    if not found:
        return Check(
            "khong vien den", False,
            "khong chay duoc cropdetect (ffmpeg co tren PATH khong?) - "
            "coi la HONG chu khong mac dinh la dat",
        )
    want = f"crop={width}:{height}:0:0"
    missing = len(seen) - len(found)
    return Check(
        "khong vien den",
        missing == 0 and all(c == want for c in found),
        f"{sorted(set(found))}"
        + (f" ({missing}/{len(seen)} moc khong do duoc)" if missing else ""),
    )


def sample_spans(
    duration: float, games: Sequence[tuple[float, float]], pad: float = GAME_EDGE_PAD_S
) -> tuple[list[tuple[float, float]], str]:
    """Cac khoang de lay mau, kem mo ta de in ra.

    Van ngan hon 2*pad thi lay nguyen ca van thay vi tra ve khoang lon nguoc
    (lo > hi): `uniform` KHONG nem o do, no lang le lay mau nguoc lai.
    """
    spans: list[tuple[float, float]] = []
    for a, b in games:
        lo, hi = a + pad, b - pad
        if hi <= lo:
            lo, hi = a, b
        if hi > lo:
            spans.append((lo, hi))
    if spans:
        return spans, f"chi trong {len(games)} van"
    if duration > 0:
        return [(duration * 0.1, duration * 0.9)], "toan bo video (chua co timeline)"
    return [], "khong co khoang nao de lay mau"


def load_games(timeline_path: Path) -> list[tuple[float, float]]:
    """Khoang thoi gian tung van tu timeline.json. Hong hoac thieu -> rong."""
    if not timeline_path.is_file():
        return []
    try:
        tl = json.loads(timeline_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return []
    if not isinstance(tl, dict):
        return []
    out: list[tuple[float, float]] = []
    for e in tl.get("events", []) or []:
        if not isinstance(e, dict) or e.get("type") != "game":
            continue
        try:
            out.append((float(e["t_start"]), float(e["t_end"])))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def hud_checks(src: VideoFrameSource, regions_path: Path, samples: int) -> list[Check]:
    """Thu doc that su o `gold` - tieu chi khong suy ra duoc tu container."""
    if not regions_path.is_file():
        return [Check("doc duoc o gold", False,
                      f"bo qua: chua co {regions_path}. Chay tools/calibrate.py truoc")]

    import logging
    logging.disable(logging.WARNING)
    import numpy as np

    from src.capture.regions import RegionError, ScreenRegions
    from src.vision.preprocess import binarize_for_ocr, has_digit, hud_bar_present

    try:
        from rapidocr import RapidOCR
        ocr = RapidOCR()
    except Exception as exc:   # noqa: BLE001 - tai model co the hong vi mang/dia
        return [Check("doc duoc o gold", False,
                      f"khong khoi tao duoc RapidOCR: {exc}")]

    try:
        reg = ScreenRegions.load(regions_path)
        reg.region("hud", "gold")
    except RegionError as exc:
        return [Check("doc duoc o gold", False, f"khong dung duoc ROI: {exc}")]

    spans, scope = sample_spans(
        src.duration,
        load_games(ROOT / "data" / "vod_index" / src.video_id / "timeline.json"),
    )
    if not spans:
        return [Check("doc duoc o gold", False, "khong co khoang nao de lay mau")]

    rng = np.random.default_rng(0)
    tried = present = hits = 0
    for _ in range(samples):
        lo, hi = spans[int(rng.integers(len(spans)))]
        frame = src.grab(float(rng.uniform(lo, hi)))
        if frame is None:
            continue
        tried += 1
        try:
            crop = reg.crop(frame.image, "hud", "gold")
            if not hud_bar_present(crop):
                continue
            present += 1
            if has_digit(ocr(binarize_for_ocr(crop))):
                hits += 1
        except (RegionError, ValueError):
            continue

    present_rate = present / tried if tried else 0.0
    read_rate = hits / present if present else 0.0
    return [
        Check("thanh HUD co hien",
              tried > 0 and present_rate >= MIN_HUD_PRESENT_RATE,
              f"{present}/{tried} khung = {present_rate:.0%} ({scope}); "
              "vong carousel / xem board khac thi khong co - binh thuong"),
        Check("doc duoc o gold",
              present > 0 and read_rate >= MIN_HUD_READ_RATE,
              f"{hits}/{present} khung CO thanh HUD = {read_rate:.0%} "
              f"(can >= {MIN_HUD_READ_RATE:.0%})" if present
              else "khong khung nao co thanh HUD - khong ket luan duoc"),
    ]


def report_dict(src: VideoFrameSource, checks: Sequence[Check]) -> dict[str, Any]:
    """Ban bao cao dang JSON."""
    meta = src.meta
    w, h = src.size
    fps = float(meta["fps"])       # type: ignore[arg-type]
    br = int(meta["bit_rate"])     # type: ignore[arg-type]
    return {
        "video_id": src.video_id,
        "size": [w, h],
        "fps": fps,
        "bit_rate": br,
        "bit_rate_source": meta.get("bit_rate_source"),
        "bpp": round(br / (w * h * fps), 5) if (w and h and fps and br) else None,
        "duration_s": round(src.duration, 1),
        "checks": [c.to_dict() for c in checks],
        "passed": sum(1 for c in checks if c.ok),
        "total": len(checks),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True)
    parser.add_argument("--samples", type=int, default=24,
                        help="so khung lay de thu doc HUD")
    parser.add_argument("--regions", default=str(ROOT / "config" / "screen_regions.yaml"))
    parser.add_argument("--json", action="store_true", help="in ket qua dang JSON")
    args = parser.parse_args(argv)
    if args.samples < 1:
        parser.error("--samples phai >= 1")

    try:
        src = VideoFrameSource(args.video)
        meta = src.meta
    except VideoSourceError as exc:
        print(f"loi doc video: {exc}", file=sys.stderr)
        return 2

    w, h = src.size
    checks = container_checks(
        w, h,
        float(meta["fps"]), int(meta["bit_rate"]), src.duration,   # type: ignore[arg-type]
        str(meta.get("bit_rate_source", "?")),
    )
    checks.append(letterbox_check(str(src.path), src.duration, w, h))
    checks.extend(hud_checks(src, Path(args.regions), args.samples))

    if args.json:
        print(json.dumps(report_dict(src, checks), indent=2, ensure_ascii=False))
    else:
        print(f"\n=== {src.video_id} ===")
        for c in checks:
            print(f"  [{'DAT ' if c.ok else 'HONG'}] {c.name:18s} {c.detail}")
        print(f"\n  {sum(1 for c in checks if c.ok)}/{len(checks)} tieu chi dat")
        print("\n  LUU Y: khong tieu chi nao o day kiem duoc OVERLAY cua streamer.")
        print("  Phai xem mat: chat/webcam co de len HUD khong. Voi VOD dau tien,")
        print("  khung chat rong ~880px va CO che o stage khi tin nhan du dai.")
    return 0 if all(c.ok for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
