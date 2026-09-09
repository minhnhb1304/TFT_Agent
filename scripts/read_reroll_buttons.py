"""Doc ba nut doi the tu khung hinh -> RerollState (Nhiem vu 3, buoc 2-3).

    # mot khung: in trang thai + vector dua vao Advisor
    python scripts/read_reroll_buttons.py --frame <anh.png>

    # ca thu muc: bang phan bo + JSON de doi chieu
    python scripts/read_reroll_buttons.py --frames-dir data/frames/s7h-jHMpFmQ/augment_select \
        --json-out data/eval/reroll_buttons.json

    # anh contact sheet de KIEM BANG MAT tung nhom - xem ghi chu duoi
    python scripts/read_reroll_buttons.py --frames-dir <dir> --sheet out.png --sheet-state disabled

    # doi chieu voi nhan tay
    python scripts/read_reroll_buttons.py --frames-dir <dir> --labels data/eval/reroll_labels.json

MOT CON SO KHONG CO NGUOI KIEM LA MOT CON SO TU CHAM

Bo phan loai nay chia mau thanh ba cum tach roi nhau. Cum tach roi KHONG
chung minh cum do dung ten: no chi chung minh may phan biet duoc ba thu. Vi
the `--sheet` ton tai - no xep anh cac o cung mot nhom canh nhau de nguoi
nhin mot phat la biet nhom do co dong nhat khong, giong het vai tro cua
`--overlay` trong `tools/calibrate.py`.

`--labels` nhan file JSON dang {"<ten frame>": ["active","disabled",...]}.
Chi cac khung co trong file moi duoc tinh, nen gan nhan mot mau nho roi mo
rong dan la dung cach dung.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.capture.regions import crop  # noqa: E402
from src.vision.reroll_buttons import (  # noqa: E402
    DEFAULT_REGIONS,
    DEFAULT_TEMPLATE,
    RerollButtonReader,
)

STATES = ("active", "disabled", "pressed", "unknown")


def _read_frames(reader: RerollButtonReader, paths: list[Path]) -> list[dict]:
    import cv2

    out = []
    for p in paths:
        image = cv2.imread(str(p))
        if image is None:
            print(f"bo qua (khong doc duoc): {p}")
            continue
        reading = reader.read(image)
        out.append({"frame": p.name, "path": str(p), **reading.to_dict()})
    return out


def _print_one(reading_dict: dict) -> None:
    print(f"man chon augment: {'CO' if reading_dict['screen_present'] else 'KHONG'}"
          f"   nga ngu: {'CO' if reading_dict['settled'] else 'CHUA'}")
    for s in reading_dict["slots"]:
        print(f"  o {s['slot'] + 1}: {s['state']:9s} "
              f"khop={s['glyph_match']:.3f} warm={s['warm']:+7.2f} "
              f"fill={s['fill_value']:6.2f}  {s['reason']}")
    print(f"  vector RerollState.available = {reading_dict['available']}")


def _distribution(rows: list[dict]) -> None:
    counts = Counter(s["state"] for r in rows for s in r["slots"])
    total = sum(counts.values())
    print(f"\n{len(rows)} khung, {total} o:")
    for state in STATES:
        n = counts[state]
        print(f"  {state:9s} {n:5d}  {100.0 * n / total if total else 0.0:5.1f}%")
    for state in STATES:
        vals = [s for r in rows for s in r["slots"] if s["state"] == state]
        if not vals:
            continue
        print(f"\n  {state}: khop {min(v['glyph_match'] for v in vals):.3f}"
              f"..{max(v['glyph_match'] for v in vals):.3f}"
              f" | warm {min(v['warm'] for v in vals):+.1f}"
              f"..{max(v['warm'] for v in vals):+.1f}"
              f" | fill {min(v['fill_value'] for v in vals):.1f}"
              f"..{max(v['fill_value'] for v in vals):.1f}")
    settled = sum(1 for r in rows if r["settled"])
    present = sum(1 for r in rows if r["screen_present"])
    print(f"\nkhung co man chon augment: {present}/{len(rows)}"
          f" | trong do nga ngu ca ba o: {settled}/{present or 1}")


def _sheet(reader: RerollButtonReader, rows: list[dict], state: str,
           out: Path, columns: int = 6, limit: int = 60) -> None:
    import cv2
    import numpy as np

    picks = [(r, s) for r in rows for s in r["slots"] if s["state"] == state]
    if not picks:
        print(f"khong co o nao o trang thai '{state}'")
        return
    # Lay deu tren toan bo dai gia tri khop, khong lay 60 cai dau: ranh gioi
    # moi la cho de sai, va lay dau danh sach thi ranh gioi khong bao gio hien.
    picks.sort(key=lambda ps: ps[1]["glyph_match"])
    idx = np.linspace(0, len(picks) - 1, min(limit, len(picks))).astype(int)

    tiles = []
    for i in idx:
        row, slot = picks[int(i)]
        image = cv2.imread(row["path"])
        box = crop(image, reader.region(slot["slot"]))
        tile = cv2.resize(box, (150, 78), interpolation=cv2.INTER_NEAREST)
        cv2.putText(tile, f"{slot['glyph_match']:.2f} {slot['warm']:+.0f} "
                    f"{slot['fill_value']:.0f}", (3, 72),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.34, (255, 255, 255), 1)
        tiles.append(cv2.copyMakeBorder(tile, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=(0, 0, 0)))
    while len(tiles) % columns:
        tiles.append(np.zeros_like(tiles[0]))
    grid = np.vstack([np.hstack(tiles[i:i + columns])
                      for i in range(0, len(tiles), columns)])
    out.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(out), grid):
        print(f"khong ghi duoc {out}")
        return
    print(f"{len(idx)}/{len(picks)} o '{state}' (lay deu theo do khop) -> {out}")


def _confusion(rows: list[dict], labels_path: Path) -> int:
    """Doi chieu voi nhan tay. Khoa la duong dan hoac ten file cua khung.

    Nhan song trong MOT file cho ca ba VOD, con `--frames-dir` chi tro vao
    mot thu muc. Khoa nao khong co trong thu muc dang doc thi bo qua im lang
    - chay lan luot ba thu muc roi cong lai la cach dung. Chi bao thieu khi
    KHONG khop duoc gi ca.
    """
    truth = {k: v for k, v in json.loads(labels_path.read_text(encoding="utf-8")).items()
             if not k.startswith("_")}
    by_name: dict[str, dict] = {r["frame"]: r for r in rows}

    matrix: Counter = Counter()
    seen = 0
    for key, want in truth.items():
        row = by_name.get(Path(key).name)
        if row is None:
            continue
        seen += 1
        for slot, expected in enumerate(want):
            matrix[(expected, row["slots"][slot]["state"])] += 1
    print(f"\nkhop {seen}/{len(truth)} khung co nhan voi thu muc dang doc")

    total = sum(matrix.values())
    if not total:
        print("khong co o nao doi chieu duoc")
        return 1
    hits = sum(n for (a, b), n in matrix.items() if a == b)
    print(f"\ndoi chieu {total} o co nhan tay:")
    header = "  nhan \\ doc  " + "".join(f"{s:>10s}" for s in STATES)
    print(header)
    for want in STATES:
        line = f"  {want:11s}" + "".join(f"{matrix[(want, got)]:>10d}" for got in STATES)
        print(line)
    print(f"\ndung {hits}/{total} = {100.0 * hits / total:.2f}%")
    for (want, got), n in sorted(matrix.items()):
        if want != got:
            print(f"  SAI: nhan '{want}' -> doc '{got}' ({n} o)")
    return 0 if hits == total else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--frame", help="mot khung hinh")
    ap.add_argument("--frames-dir", help="thu muc chua nhieu khung .png")
    ap.add_argument("--regions", default=DEFAULT_REGIONS)
    ap.add_argument("--template", default=DEFAULT_TEMPLATE)
    ap.add_argument("--json-out", help="ghi ket qua chi tiet ra JSON")
    ap.add_argument("--sheet", help="ghi anh contact sheet de kiem bang mat")
    ap.add_argument("--sheet-state", default="disabled", choices=STATES)
    ap.add_argument("--labels", help="file nhan tay de doi chieu")
    args = ap.parse_args(argv)

    if not (args.frame or args.frames_dir):
        ap.error("can --frame hoac --frames-dir")

    reader = RerollButtonReader.load(args.regions, args.template)

    paths = ([Path(args.frame)] if args.frame
             else sorted(Path(args.frames_dir).glob("*.png")))
    if not paths:
        print("khong tim thay khung hinh nao")
        return 1

    rows = _read_frames(reader, paths)
    if not rows:
        return 1

    if args.frame:
        _print_one(rows[0])
    else:
        _distribution(rows)

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nchi tiet -> {out}")

    if args.sheet:
        _sheet(reader, rows, args.sheet_state, Path(args.sheet))

    if args.labels:
        return _confusion(rows, Path(args.labels))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
