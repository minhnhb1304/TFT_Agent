"""Sinh mau glyph nut doi the -> data/templates/reroll_glyph.png (Nhiem vu 3).

    python scripts/build_reroll_template.py \
        --frame data/frames/s7h-jHMpFmQ/augment_select/augment_select_021_011005.png \
        --slot 1

VI SAO PHAI CO MOT FILE MAU, KHONG PHAI MOT NGUONG MAU SAC

Bo phan loai phai tra loi HAI cau hoi khac nhau: (a) khung nay co dang hien
nut doi khong, (b) nut do sang hay xam. (b) tach duoc bang mau - do tren 509
mau that: `warm` cua nut xam nam trong [-8.4, -2.1], cua nut sang nam trong
[24.3, 49.6], mot khe rong 26 don vi. (a) thi KHONG: dia hinh trong man dau
co ca dam la vang lan lua trai, `warm` cua chung chay khap khoang do (do
duoc: mot mang co chay len tan 54). Chi co HINH DANG cua mui ten vong tron
la khong lap lai o dau khac tren man hinh.

MAU LAY TU MOT KHUNG THAT, KHONG VE LAI

Ve lai mot mui ten vong tron bang cv2.ellipse thi khop voi y niem cua ta ve
cai nut, khong khop voi cai nut. Do lech nho o do day net va bo tron se an
thang vao nguong nhan biet, va no se hong o dung luc dang chay that.

FILE SINH RA, KHONG SUA TAY

Kem `reroll_glyph.json` ghi xuat xu: frame nao, o nao, cat o dau. Doi Set
hoac doi giao dien thi chay lai lenh tren voi mot frame moi.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.capture.regions import ScreenRegions  # noqa: E402
from src.vision.reroll_buttons import GLYPH_BOX, normalize_gray  # noqa: E402

DEFAULT_OUT = ROOT / "data" / "templates" / "reroll_glyph.png"
DEFAULT_REGIONS = ROOT / "config" / "screen_regions.yaml"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--frame", required=True, help="frame man chon augment (PNG/JPG)")
    ap.add_argument("--slot", type=int, default=1, choices=(0, 1, 2),
                    help="o nao de lay mau - phai la o DANG SANG")
    ap.add_argument("--regions", default=str(DEFAULT_REGIONS))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)

    import cv2

    image = cv2.imread(args.frame)
    if image is None:
        print(f"khong doc duoc frame: {args.frame}")
        return 1

    regions = ScreenRegions.load(args.regions)
    box = regions.crop(image, "augment_select", f"reroll_{args.slot}")
    top, left, height, width = GLYPH_BOX
    glyph = normalize_gray(cv2.cvtColor(box, cv2.COLOR_BGR2GRAY))[
        top:top + height, left:left + width
    ]
    if glyph.shape != (height, width):
        print(f"o {args.slot} cat ra {glyph.shape}, can {(height, width)} - "
              f"frame co dung 1920x1080 va dung man chon augment khong?")
        return 1

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(out), glyph):
        print(f"khong ghi duoc {out}")
        return 1

    sidecar = out.with_suffix(".json")
    sidecar.write_text(json.dumps({
        "source_frame": args.frame,
        "slot": args.slot,
        "region": regions.region("augment_select", f"reroll_{args.slot}").to_dict(),
        "glyph_box_in_button": {"top": top, "left": left,
                                "height": height, "width": width},
        "regions_file": args.regions,
        "regions_meta": regions.meta,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generated_by": "scripts/build_reroll_template.py",
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"da ghi mau {glyph.shape[1]}x{glyph.shape[0]} -> {out}")
    print(f"xuat xu -> {sidecar}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
