"""Sinh NHAN NHAP cho mot ban record playtest (moc M0) - nguoi choi chi viec sua.

    python scripts/draft_playtest_labels.py --video "D:/tft_records/game.mp4"
    python scripts/draft_playtest_labels.py --video "downloads/midfeed_tpc_final [s7h-jHMpFmQ].mkv" \
        --timeline data/vod_index/s7h-jHMpFmQ/timeline.json --regions config/screen_regions.s7h-jHMpFmQ.yaml

Dau ra:
    data/eval/playtest/<video_id>.json         moi man status="draft"
    data/eval/playtest/snapshots/<video_id>/   anh moi offer + anh HUD truoc khi mo man

Nguoi choi mo tung anh, sua `cards` / `rerolled_slot` / `hud` / `stage` / `picked`,
roi doi status thanh "verified". Chi man verified moi duoc cham diem.

`cards` chi la GOI Y (khop chinh xac, theo goc, hoac gan dung nguong 0.85 -
xem `resolve_card_title`). Luon doi chieu voi anh snapshot truoc khi verified.
Offer danh dau "CHƯA ỔN ĐỊNH" = the chua kip dung yen, anh co the dang lat.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from src.capture.regions import ScreenRegions  # noqa: E402
from src.capture.video_source import VideoFrameSource  # noqa: E402
from src.eval.playtest_draft import Sample, group_screens, make_thumb, resolve_card_title, segment_screen  # noqa: E402
from src.eval.playtest_labels import HUD_KEYS, Offer, PlaytestLabels, ScreenLabel, save  # noqa: E402
from src.knowledge.name_index import NameIndex  # noqa: E402
from src.vision.hud_reader import DEFAULT_REGIONS, HudReader  # noqa: E402
from src.vision.ocr_engine import engine  # noqa: E402
from src.vision.preprocess import ocr_texts  # noqa: E402
from src.vision.reroll_buttons import RerollButtonReader  # noqa: E402

SLOTS = 3


def _windows(src: VideoFrameSource, args: argparse.Namespace) -> list[tuple[float, float]]:
    """Khoang can quet thua. Co timeline cua scan_vod thi chi quet quanh cac man da biet."""
    end = args.end if args.end is not None else src.duration
    if not args.timeline:
        return [(args.start, end)]
    events = json.loads(Path(args.timeline).read_text(encoding="utf-8"))["events"]
    spans = [
        (max(args.start, e["t_start"] - args.pad), min(end, e["t_end"] + args.pad))
        for e in events
        if e["type"] == "augment_select" and e["t_end"] >= args.start and e["t_start"] <= end
    ]
    merged: list[tuple[float, float]] = []
    for a, b in sorted(spans):
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def _find_screens(src, buttons, windows, fps, merge_gap_s) -> list[tuple[float, float]]:
    spans: list[tuple[float, float]] = []
    for a, b in windows:
        times, present = [], []
        for frame in src.frames(start=a, end=b, fps=fps):
            times.append(frame.t)
            present.append(buttons.read(frame.image).screen_present)
        spans.extend(group_screens(times, present, gap_s=merge_gap_s))
        print(f"  quét thưa {a:7.1f}–{b:7.1f}s: {len(spans)} màn tới giờ", flush=True)
    return spans


def _hud_before(src, hud: HudReader, open_s: float, lookback: float) -> dict[str, object]:
    """Gia tri moi nhat doc duoc cua moi truong trong `lookback` giay truoc khi mo man."""
    found: dict[str, object] = {}
    for frame in src.frames(start=max(0.0, open_s - lookback), end=open_s, fps=1.0):
        for read in hud.read(frame.image).fields:
            if read.value is not None:
                found[read.field] = read.value
    return found


def _ocr_lines(ocr, crop: np.ndarray) -> list[str]:
    return [t for t in ocr_texts(ocr(crop)) if t.strip()]


def _draft_screen(src, regions, buttons, hud, ocr, index, span, args, snap_dir) -> ScreenLabel | None:
    open_s, close_s = span
    samples: list[Sample] = []
    crops: list[list[np.ndarray]] = []
    jpegs: list[bytes] = []
    for frame in src.frames(start=max(0.0, open_s - 1.0), end=close_s + 2.0, fps=args.fine_fps):
        reading = buttons.read(frame.image)
        present = reading.screen_present
        slot_crops = [regions.crop(frame.image, "augment_select", f"card_text_{i}") for i in range(SLOTS)]
        thumbs = tuple(make_thumb(cv2.cvtColor(c, cv2.COLOR_BGR2GRAY)) for c in slot_crops) if present else ()
        samples.append(Sample(frame.t, present, thumbs, tuple(r.state for r in reading.reads)))
        crops.append([c.copy() for c in slot_crops] if present else [])
        jpegs.append(cv2.imencode(".jpg", frame.image, [cv2.IMWRITE_JPEG_QUALITY, 85])[1].tobytes() if present else b"")

    seg = segment_screen(samples, stable_n=args.stable_n, settle_thr=args.settle_thr, change_thr=args.change_thr)
    if seg is None:
        return None

    hud_values = _hud_before(src, hud, seg.open_s, args.hud_lookback)
    # Stage doc TRONG man: truoc khi mo man HUD van con hien vong truoc (3-1 thay vi 3-2).
    first = cv2.imdecode(np.frombuffer(jpegs[seg.offers[0].sample_index], np.uint8), cv2.IMREAD_COLOR)
    stage_read = hud.read(first).find("stage")
    stage = str(stage_read.value if stage_read and stage_read.value else hud_values.get("stage") or "")
    offers: list[Offer] = []
    for k, d in enumerate(seg.offers):
        cards, raw = [], []
        for i in range(SLOTS):
            lines = _ocr_lines(ocr, crops[d.sample_index][i])
            cards.append(resolve_card_title(lines, index))
            raw.append(f"ô {i + 1}: " + " / ".join(lines))
        if not d.settled:
            raw.insert(0, "CHƯA ỔN ĐỊNH — thẻ chưa kịp đứng yên, kiểm kỹ ảnh")
        if offers and all(c for c in cards) and cards == offers[-1].cards:
            continue                        # OCR y het offer truoc: hieu ung hover, khong phai reroll
        name = f"{int(seg.open_s):05d}_{stage or 'x-x'}_offer{len(offers) + 1}.jpg"
        (snap_dir / name).write_bytes(jpegs[d.sample_index])
        offers.append(Offer(at_s=d.at_s, cards=cards, rerolled_slot=d.rerolled_slot, ocr_raw=raw,
                            snapshot=str((snap_dir / name).relative_to(ROOT)).replace("\\", "/")))

    return ScreenLabel(
        stage=stage,
        open_s=seg.open_s,
        close_s=seg.close_s,
        offers=offers,
        status="draft",
        hud={k: (int(hud_values[k]) if hud_values.get(k) is not None else None) for k in HUD_KEYS},
        notes="nháp tự động — kiểm ảnh snapshot rồi sửa; điền streak, traits, picked",
    )


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Sinh nhãn nháp playtest từ video")
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", help="mặc định data/eval/playtest/<video_id>.json")
    ap.add_argument("--regions", default=DEFAULT_REGIONS)
    ap.add_argument("--name-index", default="data/name_index.json")
    ap.add_argument("--timeline", help="timeline.json của scan_vod để chỉ quét quanh màn đã biết")
    ap.add_argument("--pad", type=float, default=20.0)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float)
    ap.add_argument("--coarse-fps", type=float, default=1.0)
    ap.add_argument("--fine-fps", type=float, default=4.0)
    ap.add_argument("--stable-n", type=int, default=3)
    ap.add_argument("--settle-thr", type=float, default=2.0)
    ap.add_argument("--change-thr", type=float, default=4.0)
    ap.add_argument("--hud-lookback", type=float, default=15.0)
    ap.add_argument("--merge-gap", type=float, default=30.0,
                    help="gộp các lần hiện màn cách nhau ≤ N giây (người chơi ẩn màn để xem bàn cờ)")
    ap.add_argument("--no-sha", action="store_true", help="bỏ tính SHA-256 (VOD nhiều GB)")
    ap.add_argument("--force", action="store_true", help="ghi đè file nhãn đã có")
    args = ap.parse_args(argv)

    src = VideoFrameSource(args.video)
    out = Path(args.out or ROOT / "data" / "eval" / "playtest" / f"{src.video_id}.json")
    if out.exists() and not args.force:
        print(f"{out} đã tồn tại — có thể đã chứa nhãn đã sửa tay. Dùng --force để ghi đè.")
        return 1
    snap_dir = ROOT / "data" / "eval" / "playtest" / "snapshots" / src.video_id
    snap_dir.mkdir(parents=True, exist_ok=True)

    regions = ScreenRegions.load(args.regions)
    buttons = RerollButtonReader.load(regions)
    hud = HudReader.load(regions)
    index = NameIndex.load(args.name_index)
    ocr = engine()

    print(f"{src.path.name}: {src.size[0]}x{src.size[1]}, {src.duration:.0f}s")
    spans = _find_screens(src, buttons, _windows(src, args), args.coarse_fps, args.merge_gap)
    screens: list[ScreenLabel] = []
    for span in spans:
        label = _draft_screen(src, regions, buttons, hud, ocr, index, span, args, snap_dir)
        if label is None:
            continue
        screens.append(label)
        filled = sum(1 for o in label.offers for c in o.cards if c)
        print(f"  màn {label.stage or '?'} @{label.open_s:.1f}s: {len(label.offers)} offer, "
              f"{filled}/{3 * len(label.offers)} ô có gợi ý", flush=True)

    labels = PlaytestLabels(
        video=src.path.name,
        screens=screens,
        size=src.size,
        video_sha256=None if args.no_sha else _sha256(src.path),
    )
    save(labels, out)
    print(f"\nĐã ghi {out} ({len(screens)} màn, tất cả status=draft). Ảnh: {snap_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
