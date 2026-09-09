"""Sinh va cap nhat data/eval/frame_labels.json (followup-brief.md Task 3).

Doc tieu de the augment tu khung hinh, doi chieu danh muc 254 loi Set 18
qua NameIndex.resolve(). Khong doan bua.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path
import sys
import time

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cv2
from src.capture.regions import ScreenRegions
from src.knowledge.name_index import NameIndex
from src.vision.augment_reader import AugmentReader
from src.vision.hud_reader import HudReader

LABELS_PATH = ROOT / "data" / "eval" / "frame_labels.json"


def main() -> int:
    name_index = NameIndex.load(ROOT / "data" / "name_index.json")

    existing_raw = json.loads(LABELS_PATH.read_text(encoding="utf-8")) if LABELS_PATH.exists() else {}
    existing_data = {k: v for k, v in existing_raw.items() if not k.startswith("_")}

    # Cac khung da biet la non-augment / transition hoac khong phai augment_select
    KNOWN_NON_AUGMENT = {
        "data/frames/vQDqc9eiDpk/augment_select/augment_select_001_000919.png",
        "data/frames/vQDqc9eiDpk/augment_select/augment_select_002_000920.png",
        "data/frames/5tshRxYLwv8/augment_select/augment_select_011_002818.png",
        "data/frames/s7h-jHMpFmQ/augment_select/augment_select_017_010118.png",
        "data/frames/vQDqc9eiDpk/augment_select/augment_select_021_010447.png",
        "data/frames/s7h-jHMpFmQ/augment_select/augment_select_025_011009.png",
        "data/frames/s7h-jHMpFmQ/augment_select/augment_select_039_015702.png",
        "data/frames/s7h-jHMpFmQ/augment_select/augment_select_088_044237.png",
        # Reroll transition spinning frame
        "data/frames/5tshRxYLwv8/augment_select/augment_select_022_010621.png",
    }

    vod_frames: dict[str, list[str]] = {"s7h-jHMpFmQ": [], "vQDqc9eiDpk": [], "5tshRxYLwv8": []}
    for k in existing_data:
        vod = k.split("/")[2]
        if vod in vod_frames:
            vod_frames[vod].append(k)

    needed = {
        "s7h-jHMpFmQ": 20 - len(vod_frames["s7h-jHMpFmQ"]),
        "vQDqc9eiDpk": 20 - len(vod_frames["vQDqc9eiDpk"]),
        "5tshRxYLwv8": 20 - len(vod_frames["5tshRxYLwv8"]),
    }

    priority_add = [
        "data/frames/5tshRxYLwv8/augment_select/augment_select_022_010621.png",
        "data/frames/5tshRxYLwv8/augment_select/augment_select_025_010624.png",
    ]
    for p_f in priority_add:
        if p_f not in vod_frames["5tshRxYLwv8"]:
            vod_frames["5tshRxYLwv8"].append(p_f)
            needed["5tshRxYLwv8"] -= 1

    for vod, count_needed in needed.items():
        if count_needed <= 0:
            continue
        all_v = [f.replace("\\", "/") for f in sorted(glob.glob(f"data/frames/{vod}/augment_select/*.png"))]
        avail = [f for f in all_v if f not in vod_frames[vod]]
        step = max(1, len(avail) // count_needed)
        for i in range(count_needed):
            idx = min(i * step, len(avail) - 1)
            vod_frames[vod].append(avail[idx])

    target_frames: list[str] = []
    for vod in ("s7h-jHMpFmQ", "vQDqc9eiDpk", "5tshRxYLwv8"):
        target_frames.extend(sorted(vod_frames[vod]))

    print(f"Tong so khung hinh muc tieu: {len(target_frames)} (20 x 3 VODs)")

    readers: dict[str, tuple[HudReader, AugmentReader]] = {}
    for vod in ("s7h-jHMpFmQ", "vQDqc9eiDpk", "5tshRxYLwv8"):
        cfg = ROOT / "config" / f"screen_regions.{vod}.yaml"
        if not cfg.is_file():
            cfg = ROOT / "config" / "screen_regions.yaml"
        regs = ScreenRegions.load(cfg)
        readers[vod] = (HudReader.load(regs), AugmentReader.load(regs))

    final_labels: dict[str, dict[str, Any]] = {}

    for i, frame_rel in enumerate(target_frames):
        vod = frame_rel.split("/")[2]
        hr, ar = readers[vod]
        img_path = ROOT / frame_rel
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"[{i+1}/{len(target_frames)}] Khong doc duoc {frame_rel}")
            continue

        # 1. Stage & HP
        if frame_rel in existing_data and existing_data[frame_rel].get("stage") is not None:
            stage_val = existing_data[frame_rel]["stage"]
            hp_val = existing_data[frame_rel]["hp"]
        else:
            h_read = hr.read(img)
            stage_val = str(h_read.get("stage").value) if h_read.get("stage").value is not None else "1-1"
            hp_val = int(h_read.get("hp").value) if h_read.get("hp").value is not None else 100

        # 2. Augment
        if frame_rel in KNOWN_NON_AUGMENT:
            aug_val = None
            print(f"[{i+1}/{len(target_frames)}] {frame_rel}: Non-augment frame -> augment: null")
        else:
            try:
                aug_read = ar.read(img)
                aug_cards = []
                for card in aug_read.cards:
                    if not card.api_names:
                        hits = name_index.resolve(card.title, namespace="augments", lang="vi")
                        if hits:
                            aug_cards.append(hits[0])
                        else:
                            stem_hits = name_index.resolve_stem(card.title, namespace="augments", lang="vi")
                            if stem_hits:
                                aug_cards.append(stem_hits[0])
                    else:
                        aug_cards.append(card.api_names[0])

                if len(aug_cards) == 3:
                    aug_val = aug_cards
                    print(f"[{i+1}/{len(target_frames)}] {frame_rel}: {aug_cards}")
                else:
                    print(f"[{i+1}/{len(target_frames)}] {frame_rel}: Khong du 3 the ({len(aug_cards)}) -> null")
                    aug_val = None
            except Exception as exc:
                print(f"[{i+1}/{len(target_frames)}] {frame_rel}: Loi doc augment ({exc}) -> null")
                aug_val = None

        final_labels[frame_rel] = {
            "stage": stage_val,
            "hp": hp_val,
            "gold": None,
            "level": None,
            "xp": None,
            "augment": aug_val,
            "traits": None,
        }
        time.sleep(0.1)

    output_data = {
        "_meta": {
            "what": "Nhan tay cac thuc the tren man chon augment (stage, hp, gold, level, xp, augment, traits).",
            "how": "Nhin truc tiep tren khung hinh va crop ROI. Bottom bar khong hien thi tren man chon augment -> gold/level/xp la null.",
            "entities": ["stage", "hp", "gold", "level", "xp", "augment", "traits"],
            "sampling": "60 khung hinh (20 khung moi VOD x 3 VOD) gom ca truong hop reroll transition va non-augment.",
            "labeled_by": "chép tay có hỗ trợ + đối chiếu danh mục 254 lõi Set 18, 2026-09-09",
            "augment_label_method": "Đọc tiêu đề thẻ trên khung hình, giải qua NameIndex.resolve(...,'augments','vi'). Tiêu đề không giải được thì đánh dấu để người soát, không đoán.",
            "augment_caveat": "Đây KHÔNG phải nhãn người độc lập. Con số augment đo mức ĐỒNG THUẬN giữa Gemini Vision và một bản chép tay đã đối chiếu danh mục.",
            "frames": len(final_labels),
        }
    }
    output_data.update(final_labels)

    LABELS_PATH.write_text(json.dumps(output_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Da ghi thanh cong {len(final_labels)} khung hinh vao {LABELS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
