"""Hieu chuan ROI -> config/screen_regions.yaml (SPEC 3.1, 5).

    python tools/calibrate.py --seed --from-video "<vod>" --at 11000
    python tools/calibrate.py --interactive --from-video "<vod>" --at 11000
    python tools/calibrate.py --validate --from-video "<vod>" --overlay out.jpg

VI SAO CONG CU NAY PHAI TON TAI

Bang toa do o SPEC 3.1 thuoc Set 17 (engine Hextech) va chinh SPEC danh dau la
"KHONG song sot qua 2026-08-26". Set 18 chay Unreal. Do lai tren frame that
(2026-09-06) xac nhan: bang panel toc nam o y 258..792 chu khong phai 200..700
nhu bang cu - dung so cu thi ROI an vao overlay chat cua stream.

`config/screen_regions.yaml` la file SINH RA. Khong sua tay, va khong hardcode
toa do vao code doc pixel.

BA CHE DO

    --seed         Ghi bo so da do tay tren frame Set 18 dau tien. Diem xuat
                   phat, khong phai chan ly - luon chay --validate sau do.
    --interactive  cv2.selectROI cho tung vung. Dung khi doi do phan giai,
                   doi HUD scale, hoac khi --validate bao sai.
    --validate     Kiem tra hai thu KHAC NHAU:
                     (1) hinh hoc  - ROI co dam vao vung bi che khong;
                     (2) noi dung  - crop ra co dung thu can doc khong.
                   (2) chi kiem duoc bang mat, nen no ghi ra mot anh overlay.

VUNG BI CHE KHONG PHAI LOI - NHUNG IM LANG DOC XUYEN QUA NO THI LA

`config/settings.yaml` hua `capture.assert_roi_disjoint_from_overlay: true`.
Voi VOD, "overlay" la khung chat va ma QR cua streamer. Do that tren VOD nay:
khung chat CO dam vao `stage` va `board`. Cong cu bao ra thay vi lam ngo -
mot so gold doc trung chu cua nguoi xem con te hon la khong doc duoc.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# Console Windows mac dinh cp1252; ten file yt-dlp chua U+29F8. Khong bat cho
# nay thi mot lenh print lam hong ca phien hieu chuan.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.capture.regions import Region, RegionError, ScreenRegions  # noqa: E402
from src.capture.video_source import VideoFrameSource, VideoSourceError  # noqa: E402

DEFAULT_OUT = ROOT / "config" / "screen_regions.yaml"

# Do tay tren frame Set 18 dau tien co duoc (VOD YBY1 @ t=11000s, 1920x1080),
# roi kiem lai bang cach crop + phong to tung vung. Xem docstring: day la diem
# xuat phat de --interactive tinh chinh, khong phai hang so de dan vao code.
REFERENCE_SIZE = (1920, 1080)

SEED_PIXELS: dict[str, dict[str, tuple[int, int, int, int]]] = {
    "hud": {
        # Da doi chieu bang mat o do phong dai 6x - doc ro "4-6", "18", "Cap 7", "10/60".
        "stage":     (768,   5,  815,   34),
        "gold":      (1022, 882, 1058,  910),
        "level":     (348,  882,  415,  914),
        "xp":        (455,  882,  520,  914),
        "traits":    (0,    258,  238,  792),
        "shop":      (345,  925, 1578, 1080),
        "bench":     (300,  700, 1620,  830),
        # TAM TINH: luoi hex kho khoanh giua luc giao tranh. Doc board thuoc
        # Phase 4 (nhan dien), chua ai dung o buoc tien xu ly nay.
        "board":     (380,  230, 1560,  700),
        "opponents": (1700, 170, 1920,  800),
    },
}

# Khung che cua rieng VOD nay. Streamer khac se khac -> phai do lai.
SEED_BLOCKERS: dict[str, tuple[int, int, int, int]] = {
    "stream_chat": (0,   0,  890,  218),
    "stream_qr":   (0, 875,  170, 1080),
}

# Vung minh BIET la giao voi khung che va da co cach xu ly khac; khong canh
# bao lai moi lan chay. Phai co ly do di kem, khong duoc bo vao cho yen chuyen.
KNOWN_CLASHES = {
    "board":  "doc board thuoc Phase 4; luc do se bo qua frame bi chat che",
    "stage":  "phan doan van dung tuong quan anh thu nho, khong dung OCR stage",
}


def _seed_regions(width: int, height: int, source_ref: str) -> ScreenRegions:
    return ScreenRegions(
        screens={
            screen: {
                name: Region.from_pixels(*px, width, height)
                for name, px in boxes.items()
            }
            for screen, boxes in SEED_PIXELS.items()
        },
        blockers={
            name: Region.from_pixels(*px, width, height)
            for name, px in SEED_BLOCKERS.items()
        },
        meta={
            "set": "TFTSet18",
            "engine": "unreal",
            "reference_size": [width, height],
            "calibrated_from": source_ref,
            "method": "do tay + doi chieu crop phong dai 6x",
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "generated_by": "tools/calibrate.py --seed",
        },
    )


def _interactive(image, regions: ScreenRegions, screen: str) -> ScreenRegions:
    """Khoanh lai tung vung bang cv2.selectROI. ESC/rong = giu nguyen."""
    import cv2

    h, w = image.shape[:2]
    print("Keo chuot de khoanh, ENTER de xac nhan, ESC de giu nguyen vung cu.")
    for name in list(regions.screens.get(screen, {})):
        title = f"[{screen}] {name}"
        box = cv2.selectROI(title, image, showCrosshair=True, fromCenter=False)
        cv2.destroyWindow(title)
        x, y, bw, bh = (int(v) for v in box)
        if bw <= 0 or bh <= 0:
            print(f"  {name:10s} giu nguyen")
            continue
        regions.screens[screen][name] = Region.from_pixels(x, y, x + bw, y + bh, w, h)
        print(f"  {name:10s} -> {x},{y},{x + bw},{y + bh}")
    regions.meta["generated_by"] = "tools/calibrate.py --interactive"
    regions.meta["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return regions


def _draw_overlay(image, regions: ScreenRegions, screen: str, out: Path) -> None:
    """Ve moi ROI len frame de kiem bang mat - (2) trong --validate."""
    import cv2

    canvas = image.copy()
    h, w = canvas.shape[:2]
    for name, box in regions.screens.get(screen, {}).items():
        left, top, right, bottom = box.to_pixels(w, h)
        cv2.rectangle(canvas, (left, top), (right, bottom), (0, 255, 0), 2)
        cv2.putText(canvas, name, (left + 4, max(top + 20, 16)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 255, 0), 2)
    for name, box in regions.blockers.items():
        left, top, right, bottom = box.to_pixels(w, h)
        cv2.rectangle(canvas, (left, top), (right, bottom), (0, 0, 255), 2)
        cv2.putText(canvas, name, (left + 4, max(top + 20, 16)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 0, 255), 2)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(out), canvas, [cv2.IMWRITE_JPEG_QUALITY, 92]):
        print(f"CANH BAO: khong ghi duoc anh kiem tra -> {out}")
        return
    print(f"anh kiem tra -> {out}")


def _validate(regions: ScreenRegions, screen: str) -> int:
    """Kiem tra hinh hoc. Tra ve so van de PHAI xu ly."""
    print(f"\n--- hinh hoc: {screen} ---")
    clashes = regions.check_blockers(screen)
    unexpected = 0
    for name in sorted(regions.screens.get(screen, {})):
        hit = clashes.get(name)
        if not hit:
            print(f"  OK        {name}")
        elif name in KNOWN_CLASHES:
            print(f"  DA BIET   {name} <- {', '.join(hit)}: {KNOWN_CLASHES[name]}")
        else:
            print(f"  VAN DE    {name} <- {', '.join(hit)}")
            unexpected += 1

    if unexpected:
        print(f"\n{unexpected} vung dam vao khung che ma chua co cach xu ly.")
        print("Khoanh lai bang --interactive, hoac ghi ly do vao KNOWN_CLASHES.")
    else:
        print("\nKhong co va cham ngoai du kien.")
    return unexpected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-video", help="duong dan file video de lay frame mau")
    parser.add_argument("--at", type=float, default=11000.0, help="moc giay trong video")
    parser.add_argument("--image", help="dung mot file anh thay vi video")
    parser.add_argument("--screen", default="hud", help="ten man hinh (mac dinh: hud)")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--seed", action="store_true", help="ghi bo so do tay ban dau")
    parser.add_argument("--interactive", action="store_true", help="khoanh lai bang chuot")
    parser.add_argument("--validate", action="store_true", help="kiem tra ROI")
    parser.add_argument("--overlay", help="ghi anh co ve ROI de kiem bang mat")
    parser.add_argument("--overwrite", action="store_true", help="cho phep ghi de file da co")
    args = parser.parse_args(argv)

    if not (args.seed or args.interactive or args.validate):
        parser.error("chon it nhat mot trong --seed / --interactive / --validate")

    # --- lay frame mau ---
    image = None
    source_ref = args.image or "khong ro"
    if args.image:
        import cv2
        image = cv2.imread(args.image)
        if image is None:
            raise SystemExit(f"khong doc duoc anh: {args.image}")
    elif args.from_video:
        try:
            src = VideoFrameSource(args.from_video)
            frame = src.grab(args.at)
        except VideoSourceError as exc:
            print(f"loi doc video: {exc}")
            return 1
        if frame is None:
            print(f"khong lay duoc frame o {args.at}s")
            return 1
        image, source_ref = frame.image, frame.ref

    out = Path(args.out)

    # --- dung / nap bo ROI ---
    if args.seed:
        if image is None:
            parser.error("--seed can --from-video hoac --image de biet kich thuoc goc")
        if out.exists() and not args.overwrite:
            print(f"{out} da ton tai. Them --overwrite neu that su muon ghi de.")
            return 1
        h, w = image.shape[:2]
        if (w, h) != REFERENCE_SIZE:
            print(f"CANH BAO: frame {w}x{h} khac chuan {REFERENCE_SIZE[0]}x"
                  f"{REFERENCE_SIZE[1]}; bo so mau co the lech.")
        regions = _seed_regions(w, h, source_ref)
    else:
        try:
            regions = ScreenRegions.load(out)
        except RegionError as exc:
            print(f"khong nap duoc {out}: {exc}")
            return 1

    if args.interactive:
        if image is None:
            parser.error("--interactive can --from-video hoac --image")
        regions = _interactive(image, regions, args.screen)

    if args.seed or args.interactive:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(regions.to_yaml(), encoding="utf-8")
        print(f"da ghi {len(regions.screens.get(args.screen, {}))} vung -> {out}")

    problems = 0
    if args.validate:
        problems = _validate(regions, args.screen)

    if args.overlay:
        if image is None:
            parser.error("--overlay can --from-video hoac --image")
        _draw_overlay(image, regions, args.screen, Path(args.overlay))

    print(f"\nXuat xu: {regions.meta.get('calibrated_from')}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
