"""Quet VOD -> dong thoi gian su kien (tien xu ly cho SPEC 12).

    # Buoc 1: dung kho anh thu nho tu I-frame (~8 phut cho VOD 5 gio)
    python scripts/scan_vod.py --video "<vod>" --thumbs

    # Buoc 2: tim su kien bang tuong quan cheo (vai giay)
    python scripts/scan_vod.py --video "<vod>" --detect \
        --exemplar game_end=12000 --exemplar augment_select=1845

    # Xem thu mot moc co giong mau khong truoc khi tin
    python scripts/scan_vod.py --video "<vod>" --peek 12000 --out-image xem.jpg

VAI TRO CUA VOD NAY: TAP PHAT TRIEN, KHONG PHAI TAP DANH GIA

`research/vanguard/testing-protocol.md` buoc 3 da chot tap danh gia cho SPEC
12.1 la ban ghi TU QUAY tren may cua tac gia. Neu lay chinh VOD nay vua de do
toa do ROI, chinh nguong, va vua de bao cao P/R/F1 thi con so do do "da van
bao nhieu num", khong do do chinh xac nhan dien. Giu ranh gioi do la viec cua
con nguoi, nhung manifest o day ghi san `role: development` de khong ai lo.

VI SAO TUONG QUAN CHEO CHU KHONG PHAI OCR STAGE

Ban dau dinh OCR o hien stage tren toan bo dong thoi gian. Do that tren VOD
cho thay khung chat cua stream nam de len o do (do 2026-09-06: chat toi
x=890, stage o x=768..815) - mot tin nhan dai la doc ra rac, va rac do khong
tu bao la rac.

Anh thu nho 128x72 thi khac: man chon augment co bo cuc CO DINH (nen toi, ba
the bai o vi tri co dinh), nen tuong quan cheo voi mot anh mau bat rat manh
du hinh ve tren the moi lan mot khac. Che khung chat truoc khi tinh la xong.
Toan bo phep tinh chay bang numpy trong tich tac, tren du lieu da cache.

GOP = 1 GIAY, NEN I-FRAME CHINH LA NHIP 1 FPS MIEN PHI

Do 2026-09-06: 600 keyframe / 600 giay. 5 gio video = 18.225 I-frame chu
khong phai 1,09 trieu frame. Vi the khong can bat ky co che ne tranh nhieu
tang nao - quet thang mot luot la xong.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# Console Windows mac dinh cp1252, con ten file yt-dlp chua U+29F8 (dau
# gach thay cho '/'). Khong bat cho nay thi mot lenh print lam hong ca
# luot quet 8 phut - va hong o cuoi, sau khi da giai ma xong.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.capture.regions import ScreenRegions  # noqa: E402
from src.capture.video_source import VideoFrameSource, VideoSourceError  # noqa: E402

DEFAULT_INDEX_DIR = ROOT / "data" / "vod_index"
DEFAULT_REGIONS = ROOT / "config" / "screen_regions.yaml"

# Nguong tuong quan mac dinh. Co y de CAO: bo sot mot su kien thi nguoi doc
# bang dinh se thay thieu, con nhan bua thi lang le lam ban dataset.
DEFAULT_THRESHOLD = 0.80

# Hai su kien cach nhau duoi ngan nay giay thi coi la mot lan xuat hien.
MERGE_GAP_S = 5.0


def _mask_blockers(thumbs: np.ndarray, regions: ScreenRegions | None) -> np.ndarray:
    """Xoa vung khung chat / QR truoc khi so sanh.

    Chat cuon lien tuc nen no la nhieu thuan tuy: de nguyen thi hai frame cung
    mot man hinh van khac nhau chi vi co nguoi vua chat.
    """
    if regions is None or not regions.blockers:
        return thumbs
    out = thumbs.copy()
    h, w = thumbs.shape[1:]
    for box in regions.blockers.values():
        left, top, right, bottom = box.to_pixels(w, h)
        out[:, top:bottom, left:right] = 0
    return out


def _znorm(a: np.ndarray) -> np.ndarray:
    """Chuan hoa ve trung binh 0, do lech 1 - de sang toi khong anh huong."""
    flat = a.reshape(a.shape[0], -1).astype(np.float32)
    flat -= flat.mean(axis=1, keepdims=True)
    flat /= flat.std(axis=1, keepdims=True) + 1e-6
    return flat


def _group_runs(times: np.ndarray, hits: np.ndarray, gap: float) -> list[tuple[float, float]]:
    """Gop cac frame trung lien tiep thanh (bat dau, ket thuc)."""
    idx = np.flatnonzero(hits)
    if idx.size == 0:
        return []
    runs: list[tuple[float, float]] = []
    start = prev = float(times[idx[0]])
    for i in idx[1:]:
        t = float(times[i])
        if t - prev > gap:
            runs.append((start, prev))
            start = t
        prev = t
    runs.append((start, prev))
    return runs


def _derive_games(
    runs: list[tuple[float, float]],
    duration: float,
    min_game_s: float,
    join_gap_s: float,
) -> list[tuple[float, float]]:
    """Suy ra khoang thoi gian tung van tu cac doan KHONG o trong tran.

    VI SAO DI DUONG VONG NAY

    Anh mau chup man ket tran hoa ra khop voi CA man sanh cho: o 128x72 thi ca
    hai deu la "cua so client tren nen desktop", va nen desktop chiem phan lon
    khung hinh. Ban dau tuong la nham, nhung do moi la tin hieu ON DINH hon
    nhieu so voi man ket tran - vi no khong phu thuoc vao hinh ve rieng cua
    tung van.

    Nen dao nguoc lai: doan nao KHONG khop tuc la dang toan man hinh, tuc la
    dang trong tran. Loc theo do dai toi thieu de bo cac doan chuyen canh ngan.
    """
    merged: list[list[float]] = []
    for a, b in sorted(runs):
        if merged and a - merged[-1][1] <= join_gap_s:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])

    games: list[tuple[float, float]] = []
    cursor = 0.0
    for a, b in merged:
        if a - cursor >= min_game_s:
            games.append((cursor, a))
        cursor = max(cursor, b)
    if duration - cursor >= min_game_s:
        games.append((cursor, duration))
    return games


def _cross_check(events: list[dict[str, object]]) -> dict[int, dict[str, int]]:
    """Dem su kien tung loai theo tung van, va NOI ra khi lech.

    SPEC 12 cho rang moi van co 3 lan chon augment. Kiem lai bang du lieu chu
    khong tin vao gia dinh: lech so la dau hieu anh mau chon sai, nguong chua
    hop, hoac van do that su khac thuong (Set 18 co augment cho them). Ca ba
    truong hop deu phai do NGUOI quyet dinh, khong duoc lang le di tiep.
    """
    games = sorted(
        [e for e in events if e.get("type") == "game"],
        key=lambda e: e["t_start"],   # type: ignore[index,arg-type]
    )
    if not games:
        return {}

    tally: dict[int, dict[str, int]] = {}
    for g in games:
        counts: dict[str, int] = {}
        for e in events:
            if e.get("type") in (None, "game"):
                continue
            if g["t_start"] <= e["t_start"] <= g["t_end"]:   # type: ignore[operator,index]
                key = str(e["type"])
                counts[key] = counts.get(key, 0) + 1
        tally[int(g.get("game_index", 0))] = counts

    kinds = sorted({k for c in tally.values() for k in c})
    if kinds:
        print("\n--- doi chieu: so su kien tren tung van ---")
        print("  van  " + "  ".join(f"{k:>16s}" for k in kinds))
        for idx in sorted(tally):
            print(f"  {idx:<5d}" + "  ".join(f"{tally[idx].get(k, 0):>16d}" for k in kinds))
        for k in kinds:
            vals = [tally[i].get(k, 0) for i in sorted(tally)]
            if len(set(vals)) > 1:
                print(f"  CHU Y: '{k}' khong deu giua cac van ({vals}) - kiem tay "
                      "truoc khi dung.")
    return tally

def _hhmmss(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def cmd_thumbs(src: VideoFrameSource, index_dir: Path, overwrite: bool) -> int:
    """Buoc 1: giai ma toan bo I-frame thanh kho anh xam thu nho."""
    index_dir.mkdir(parents=True, exist_ok=True)
    thumbs_path = index_dir / "thumbs.npy"
    if thumbs_path.exists() and not overwrite:
        print(f"{thumbs_path} da co. Them --overwrite de dung lai.")
        return 1

    print(f"dang giai ma I-frame cua {src.video_id} ...")
    print(f"  {src.duration:.0f}s @ {src.meta['fps']}fps, du kien ~{src.duration / 2200:.0f} phut")
    thumbs, times = src.thumbnails()
    if thumbs.size == 0:
        print("khong doc duoc frame nao")
        return 1

    # `thumbnails()` danh so moc theo gia dinh I-frame cach nhau dung 1 giay.
    # Dung voi VOD nay (do duoc: 600 keyframe / 600 giay) nhung KHONG dung noi
    # chung. Doi chieu voi PTS that tu ffprobe roi thay bang so that - lech
    # moc thoi gian la lech ca dong su kien, va lech dan thi khong ai thay.
    print("dang doi chieu moc thoi gian voi PTS that ...")
    real = src.keyframe_times(cache=index_dir / "keyframes.json")
    if len(real) == len(times):
        drift = float(np.abs(np.array(real) - times).max())
        times = np.array(real, np.float64)
        print(f"  {len(real)} keyframe khop; sai lech lon nhat cua gia dinh 1s: {drift:.3f}s")
    else:
        print(f"  CANH BAO: ffprobe dem {len(real)} keyframe nhung giai ma ra "
              f"{len(times)} frame.")
        print("  Giu moc gia dinh 1 giay/frame. Moc thoi gian co the LECH - "
              "kiem lai bang --peek truoc khi tin ket qua.")

    np.save(thumbs_path, thumbs)
    np.save(index_dir / "times.npy", times)
    print(f"da ghi {len(thumbs)} anh thu nho {thumbs.shape[2]}x{thumbs.shape[1]} "
          f"({thumbs.nbytes / 1e6:.0f} MB) -> {thumbs_path}")
    if len(times) > 1:
        print(f"khoang cach trung binh giua hai I-frame: {np.diff(times).mean():.3f}s")
    else:
        print("CANH BAO: chi giai ma duoc 1 khung - video qua ngan hoac hong?")
    return 0


def cmd_detect(
    src: VideoFrameSource,
    index_dir: Path,
    exemplars: dict[str, float],
    regions: ScreenRegions | None,
    threshold: float,
    top: int,
    merge_gap_s: float = MERGE_GAP_S,
    games_from: str | None = None,
    min_game_s: float = 900.0,
    join_gap_s: float = 180.0,
    regions_path: str | None = None,
) -> int:
    """Buoc 2: tuong quan cheo voi anh mau -> danh sach su kien."""
    thumbs_path = index_dir / "thumbs.npy"
    times_path = index_dir / "times.npy"
    for path in (thumbs_path, times_path):
        if not path.is_file():
            print(f"chua co {path}. Chay --thumbs truoc.")
            return 1

    try:
        thumbs = np.load(thumbs_path)
        times = np.load(times_path)
    except (ValueError, OSError) as exc:
        print(f"kho anh thu nho hong ({exc}). Chay lai --thumbs --overwrite.")
        return 1
    if thumbs.ndim != 3 or len(thumbs) == 0:
        print(f"thumbs.npy co hinh dang la {thumbs.shape}. Chay lai --thumbs --overwrite.")
        return 1
    if len(times) != len(thumbs):
        print(f"lech so luong: {len(thumbs)} anh nhung {len(times)} moc thoi gian. "
              "Chay lai --thumbs --overwrite.")
        return 1
    masked = _znorm(_mask_blockers(thumbs, regions))
    print(f"nap {len(thumbs)} anh thu nho, {_hhmmss(float(times[-1]))} tong thoi luong")

    events: list[dict[str, object]] = []
    runs_by_label: dict[str, list[tuple[float, float]]] = {}
    for label, at in exemplars.items():
        i = int(np.argmin(np.abs(times - at)))
        drift = abs(float(times[i]) - at)
        if drift > 2.0:
            print(f"  CANH BAO: '{label}' xin moc {at:.1f}s nhung gan nhat la "
                  f"{times[i]:.1f}s (lech {drift:.1f}s). Moc nam ngoai video?")
        template = masked[i]
        scores = masked @ template / template.size
        runs = _group_runs(times, scores >= threshold, merge_gap_s)

        print(f"\n--- {label} (mau tai {_hhmmss(at)}, nguong {threshold}) ---")
        order = np.argsort(scores)[::-1][:top]
        print(f"  {top} diem cao nhat:")
        for j in order:
            print(f"    {_hhmmss(float(times[j])):>9s}  {scores[j]:.3f}")
        runs_by_label[label] = runs
        print(f"  -> {len(runs)} lan xuat hien sau khi gop:")
        for k, (a, b) in enumerate(runs, 1):
            print(f"    {k:2d}. {_hhmmss(a)} .. {_hhmmss(b)}  ({b - a:.0f}s)")
            events.append({
                "type": label, "t_start": round(a, 3), "t_end": round(b, 3),
                "frame_ref": f"vod:{src.video_id}@{_hhmmss(a)}.000",
            })

    if games_from:
        if games_from not in runs_by_label:
            print(f"\nCANH BAO: khong co nhan '{games_from}' de suy ra van.")
        else:
            games = _derive_games(
                runs_by_label[games_from], src.duration, min_game_s, join_gap_s
            )
            print(f"\n--- suy ra van (nghich dao cua '{games_from}') ---")
            for i, (a, b) in enumerate(games, 1):
                print(f"  van {i}: {_hhmmss(a)} .. {_hhmmss(b)}  ({(b - a) / 60:.1f} phut)")
                events.append({
                    "type": "game", "game_index": i,
                    "t_start": round(a, 3), "t_end": round(b, 3),
                    "frame_ref": f"vod:{src.video_id}@{_hhmmss(a)}.000",
                })
            print(f"  -> {len(games)} van")

    _cross_check(events)

    events.sort(key=lambda e: e["t_start"])   # type: ignore[index,arg-type]
    manifest = {
        "meta": {
            "source": str(src.path),
            "video_id": src.video_id,
            "role": "development",   # xem docstring dau file
            "size": list(src.size),
            "duration_s": round(src.duration, 3),
            "codec": src.meta["codec"],
            "profile": src.meta["profile"],
            "bit_rate": src.meta["bit_rate"],
            "threshold": threshold,
            "merge_gap_s": merge_gap_s,
            "exemplars": {k: round(v, 3) for k, v in exemplars.items()},
            "derive_games_from": games_from,
            "regions": regions_path if regions else None,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "generated_by": "scripts/scan_vod.py --detect",
        },
        "events": events,
    }
    out = index_dir / "timeline.json"
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print(f"\nda ghi {len(events)} su kien -> {out}")
    print("KIEM BANG MAT truoc khi dung: so lan xuat hien co dung nhu mong doi khong?")
    print("Lech so la dau hieu anh mau chon sai hoac nguong chua hop - dung bo qua.")
    return 0


def cmd_peek(src: VideoFrameSource, at: float, out_image: Path) -> int:
    """Ghi mot frame ra anh de nguoi xem chon anh mau."""
    import cv2

    frame = src.grab(at)
    if frame is None:
        print(f"khong lay duoc frame o {at}s")
        return 1
    out_image.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_image), frame.image, [cv2.IMWRITE_JPEG_QUALITY, 92])
    print(f"{frame.ref} -> {out_image}")
    return 0


def _parse_exemplar(raw: str) -> tuple[str, float]:
    label, _, value = raw.partition("=")
    if not label or not value:
        raise argparse.ArgumentTypeError(f"can dang ten=giay, nhan duoc '{raw}'")
    try:
        return label, float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"'{value}' khong phai so giay") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True)
    parser.add_argument("--index-dir", default=None)
    parser.add_argument("--regions", default=str(DEFAULT_REGIONS))
    parser.add_argument("--thumbs", action="store_true", help="buoc 1: dung kho anh thu nho")
    parser.add_argument("--detect", action="store_true", help="buoc 2: tim su kien")
    parser.add_argument("--peek", type=float, help="ghi mot frame ra anh de xem")
    parser.add_argument("--out-image", default="peek.jpg")
    parser.add_argument("--exemplar", action="append", type=_parse_exemplar,
                        default=[], metavar="TEN=GIAY")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--top", type=int, default=25, help="so diem cao nhat in ra")
    parser.add_argument("--derive-games-from", default=None, metavar="NHAN",
                        help="suy ra van bang cach dao nguoc nhan nay "
                             "(vd: client_windowed)")
    parser.add_argument("--merge-gap-s", type=float, default=MERGE_GAP_S,
                        help="hai lan trung cach nhau duoi nay la MOT su kien")
    parser.add_argument("--min-game-s", type=float, default=900.0,
                        help="doan ngan hon nay khong tinh la mot van")
    parser.add_argument("--join-gap-s", type=float, default=180.0,
                        help="hai doan cach nhau duoi nay thi gop lam mot")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    if not (args.thumbs or args.detect or args.peek is not None):
        parser.error("chon --thumbs, --detect hoac --peek")

    try:
        src = VideoFrameSource(args.video)
        _ = src.meta
    except VideoSourceError as exc:
        print(f"loi doc video: {exc}")
        return 1

    index_dir = Path(args.index_dir) if args.index_dir else DEFAULT_INDEX_DIR / src.video_id

    if args.peek is not None:
        return cmd_peek(src, args.peek, Path(args.out_image))

    if args.thumbs:
        code = cmd_thumbs(src, index_dir, args.overwrite)
        if code or not args.detect:
            return code

    if args.detect:
        if not args.exemplar:
            parser.error("--detect can it nhat mot --exemplar TEN=GIAY")
        regions = None
        if Path(args.regions).is_file():
            regions = ScreenRegions.load(args.regions)
        else:
            print(f"CANH BAO: khong co {args.regions} - khong che duoc khung chat, "
                  "tuong quan se nhieu hon.")
        return cmd_detect(src, index_dir, dict(args.exemplar), regions,
                          args.threshold, args.top, args.merge_gap_s,
                          args.derive_games_from,
                          args.min_game_s, args.join_gap_s,
                          regions_path=args.regions if regions else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
