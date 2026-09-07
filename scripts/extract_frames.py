"""Trich frame tai cac su kien da tim duoc -> kho anh de gan nhan (SPEC 12.1).

    python scripts/extract_frames.py --video "<vod>"
    python scripts/extract_frames.py --video "<vod>" --types augment_select --per-event 5
    python scripts/extract_frames.py --video "<vod>" --dry-run

Doc `data/vod_index/<id>/timeline.json` do `scripts/scan_vod.py --detect` sinh ra.

GHI PNG CHU KHONG PHAI JPG

Nguon da la ban nen mat mat (YouTube, 3,74 Mbps cho 1080p60). Ghi tiep ra JPG
la nen mat mat LAN HAI, va lan hai roi dung vao chu nho - dung cho ma OCR phai
doc. Sai so do se di thang vao con so SPEC 12.1 ma khong ai truy ra duoc.
PNG ton dia hon nhung dia thi re, con mot bo so danh gia sai thi khong mua lai
duoc.

TEN FILE PHAI TRUY NGUOC DUOC VE GIAY TRONG VIDEO

`Scenario.frame_ref` la thu noi mot ban ghi voi khoanh khac sinh ra no. Dat ten
theo dau thoi gian video (khong phai gio he thong) co ba cai loi: chay lai cho
ra dung ten cu, sap xep theo ten la dung thu tu thoi gian, va nguoi cham do an
dan duoc tu ten file toi dung giay trong video goc.

CAT ROI LA TUY CHON, KHONG PHAI MAC DINH

Anh day du la thu duy nhat gan nhan tay duoc. ROI cat san chi de dua vao model
cho re token. Vi the ROI ghi ra thu muc rieng va khong bao gio thay the anh day
du - neu sau nay phat hien ROI khoanh sai thi van con anh goc de cat lai.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from src.capture.regions import ScreenRegions  # noqa: E402
from src.capture.video_source import VideoFrameSource, VideoSourceError  # noqa: E402

DEFAULT_INDEX_DIR = ROOT / "data" / "vod_index"
DEFAULT_FRAME_DIR = ROOT / "data" / "frames"
DEFAULT_REGIONS = ROOT / "config" / "screen_regions.yaml"


def _hhmmss(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600:02d}{(s % 3600) // 60:02d}{s % 60:02d}"


def _rel(path: Path) -> str:
    """Duong dan tuong doi so voi goc repo, hoac tuyet doi neu nam ngoai.

    `Path.relative_to` NEM khi duong dan khong nam duoi goc - va `--out-dir`
    tro ra o dia khac la chuyen binh thuong. Mot manifest ghi duong tuyet doi
    van dung duoc; mot script chet giua chung thi khong.
    """
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _sample_times(
    t_start: float, t_end: float, count: int, sample_from: float = 0.0
) -> list[float]:
    """Chon `count` moc trong mot lan xuat hien.

    `sample_from` bo qua phan dau cua khoang. Man chon augment mat vai giay lat
    bai: lay o giua khoang thi trung dung luc ba the bai con up, va anh do
    khong gan nhan duoc. Do thay tren VOD nay: 2 trong 6 su kien dau tien roi
    vao dung pha lat bai. Dat 0.5 la chi lay nua sau, luc bai da ngua.
    """
    span = t_end - t_start
    if span <= 0:
        return [t_start] * max(1, count)
    lo = t_start + span * max(0.0, min(sample_from, 0.95))
    window = t_end - lo
    if count <= 1:
        return [lo + window / 2]
    step = window / (count + 1)
    return [lo + step * (i + 1) for i in range(count)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True)
    parser.add_argument("--index-dir", default=None)
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--regions", default=str(DEFAULT_REGIONS))
    parser.add_argument("--types", default=None,
                        help="loc theo loai su kien, ngan cach bang dau phay")
    parser.add_argument("--per-event", type=int, default=1,
                        help="so frame lay tren moi lan xuat hien")
    parser.add_argument("--sample-from", type=float, default=0.0, metavar="TI_LE",
                        help="bo qua ti le dau cua moi khoang (0.5 = chi lay nua sau)")
    parser.add_argument("--rois", default=None,
                        help="cat them cac vung nay (vd: gold,stage,traits)")
    parser.add_argument("--screen", default="hud")
    parser.add_argument("--dry-run", action="store_true", help="chi in ra se lam gi")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    if args.per_event < 1:
        parser.error("--per-event phai >= 1")
    if not 0.0 <= args.sample_from < 1.0:
        parser.error("--sample-from phai trong khoang [0, 1)")

    import cv2

    try:
        src = VideoFrameSource(args.video)
        _ = src.meta
    except VideoSourceError as exc:
        print(f"loi doc video: {exc}")
        return 1

    index_dir = Path(args.index_dir) if args.index_dir else DEFAULT_INDEX_DIR / src.video_id
    timeline_path = index_dir / "timeline.json"
    if not timeline_path.is_file():
        raise SystemExit(
            f"chua co {timeline_path}. Chay `python scripts/scan_vod.py "
            f"--video ... --thumbs --detect --exemplar ...` truoc."
        )

    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    events = timeline.get("events", [])
    if args.types:
        wanted = {t.strip() for t in args.types.split(",") if t.strip()}
        events = [e for e in events if e.get("type") in wanted]
    if not events:
        print("khong co su kien nao khop. Xem lai --types hoac timeline.json.")
        return 1

    regions = None
    roi_names: list[str] = []
    if args.rois:
        if not Path(args.regions).is_file():
            raise SystemExit(f"can {args.regions} de cat ROI - chay tools/calibrate.py")
        regions = ScreenRegions.load(args.regions)
        roi_names = [r.strip() for r in args.rois.split(",") if r.strip()]
        for name in roi_names:
            regions.region(args.screen, name)      # nem som neu ten sai

    out_dir = Path(args.out_dir) if args.out_dir else DEFAULT_FRAME_DIR / src.video_id
    planned = sum(args.per_event for _ in events)
    print(f"{len(events)} su kien x {args.per_event} frame = {planned} anh -> {out_dir}")
    if roi_names:
        print(f"cat them ROI: {', '.join(roi_names)}")

    if args.dry_run:
        for e in events:
            for t in _sample_times(e["t_start"], e["t_end"], args.per_event,
                                   args.sample_from):
                print(f"  [dry-run] {e['type']:16s} {t:9.2f}s")
        return 0

    records: list[dict[str, object]] = []
    written = skipped = 0
    per_type: dict[str, int] = {}

    for event in events:
        etype = str(event.get("type", "unknown"))
        for t in _sample_times(event["t_start"], event["t_end"], args.per_event,
                               args.sample_from):
            per_type[etype] = per_type.get(etype, 0) + 1
            name = f"{etype}_{per_type[etype]:03d}_{_hhmmss(t)}.png"
            target = out_dir / etype / name

            if target.exists() and not args.overwrite:
                skipped += 1
                continue

            frame = src.grab(t)
            if frame is None:
                print(f"  CANH BAO: khong lay duoc frame o {t:.2f}s")
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            if not cv2.imwrite(str(target), frame.image):
                print(f"  CANH BAO: khong ghi duoc {target} - bo qua khung nay")
                continue
            written += 1

            record: dict[str, object] = {
                "frame_ref": frame.ref,
                "path": _rel(target),
                "event_type": etype,
                "t": round(t, 3),
                "t_start": event["t_start"],
                "t_end": event["t_end"],
            }

            if regions is not None and roi_names:
                crops: dict[str, str] = {}
                for roi in roi_names:
                    piece = regions.crop(frame.image, args.screen, roi)
                    roi_path = out_dir / "roi" / roi / name
                    roi_path.parent.mkdir(parents=True, exist_ok=True)
                    if not cv2.imwrite(str(roi_path), piece):
                        print(f"  CANH BAO: khong ghi duoc ROI {roi_path}")
                        continue
                    crops[roi] = _rel(roi_path)
                record["rois"] = crops

            records.append(record)

    manifest = {
        "meta": {
            "video_id": src.video_id,
            "source": str(src.path),
            # Ke thua tu timeline: VOD nay la tap PHAT TRIEN. Con so SPEC 12.1
            # phai do tren ban ghi tu quay - xem scan_vod.py.
            "role": timeline.get("meta", {}).get("role", "development"),
            "timeline": _rel(timeline_path),
            "regions": args.regions if roi_names else None,
            "per_event": args.per_event,
            "sample_from": args.sample_from,
            "format": "png",
            "n_frames": len(records),
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "generated_by": "scripts/extract_frames.py",
        },
        "frames": records,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"
    with io.open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print(f"\nda ghi {written} anh, bo qua {skipped} anh da co")
    for etype, n in sorted(per_type.items()):
        print(f"  {etype:16s} {n}")
    print(f"manifest -> {manifest_path}")
    print("\nLuu y: data/frames/ nam trong .gitignore - anh KHONG vao repo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
