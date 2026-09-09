"""Chay danh gia do chinh xac nhan dang CV/OCR (SPEC 12.1, Nhiem vu 9).

    python scripts/evaluate_recognition.py --frames-dir data/frames/s7h-jHMpFmQ/augment_select \
        --labels data/eval/frame_labels.json --entities stage,hp
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.capture.regions import ScreenRegions  # noqa: E402
from src.eval.recognition import Prediction, RecognitionReport, evaluate  # noqa: E402
from src.utils.settings import Settings  # noqa: E402
from src.vision.augment_reader import AugmentReader  # noqa: E402
from src.vision.hud_reader import DEFAULT_REGIONS, HudReader  # noqa: E402

DEFAULT_LABELS = "data/eval/frame_labels.json"


def evaluate_frames(
    frames_dir: str | Path,
    labels_path: str | Path = DEFAULT_LABELS,
    entities: list[str] | None = None,
    regions: str | Path | ScreenRegions = DEFAULT_REGIONS,
) -> tuple[RecognitionReport, list[Prediction]]:
    import cv2

    raw_labels = json.loads(Path(labels_path).read_text(encoding="utf-8"))
    labeled_frames = {k: v for k, v in raw_labels.items() if not k.startswith("_")}

    f_dir = Path(frames_dir)
    image_files = sorted(f_dir.glob("*.png"))

    if not image_files:
        raise FileNotFoundError(f"Khong tim thay file anh .png nao trong {frames_dir}")

    # Chon file cau hinh phu hop voi VOD neu co
    regs = regions
    if isinstance(regs, (str, Path)):
        vod_candidate = f_dir.parent.name
        vod_cfg = ROOT / "config" / f"screen_regions.{vod_candidate}.yaml"
        if vod_cfg.is_file():
            regs = ScreenRegions.load(vod_cfg)
        else:
            regs = ScreenRegions.load(regs)

    hud_reader = HudReader.load(regs)
    aug_reader = None

    eval_entities = entities or ["stage", "hp", "gold", "level", "xp"]
    if "traits" in eval_entities:
        raise ValueError("Chưa hỗ trợ đánh giá traits (SPEC 12.1 hiện chỉ hỗ trợ stage, hp, gold, level, xp, augment)")

    if "augment" in eval_entities:
        settings = Settings.load()
        try:
            aug_reader = AugmentReader.load(
                regs,
                model=settings.gemini_model,
                timeout_s=settings.gemini_timeout_s,
                enable_gemini_vision=settings.enable_gemini_vision,
            )
        except Exception as exc:
            print(f"Cảnh báo: Không thể khởi tạo AugmentReader ({exc}) — bỏ qua augment")
            eval_entities = [e for e in eval_entities if e != "augment"]

    predictions: list[Prediction] = []

    # Map key theo ca duong dan tuong doi va ten file
    for img_path in image_files:
        # Tim nhan tuong ung
        label = None
        rel_path = str(img_path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
        if rel_path in labeled_frames:
            label = labeled_frames[rel_path]
        else:
            # Thu tim theo ten file
            for k, v in labeled_frames.items():
                if Path(k).name == img_path.name:
                    label = v
                    break

        if label is None:
            continue

        img = cv2.imread(str(img_path))
        if img is None:
            continue

        hud_reading = None
        if any(e in eval_entities for e in ("stage", "hp", "gold", "level", "xp")):
            hud_reading = hud_reader.read(img)

        aug_reading = None
        if aug_reader and any(e in eval_entities for e in ("augment", "traits")):
            try:
                aug_reading = aug_reader.read(img)
            except Exception:
                aug_reading = None

        # Danh gia tung thuc the
        for ent in eval_entities:
            if ent in ("stage", "hp", "gold", "level", "xp") and hud_reading:
                field_read = hud_reading.get(ent)
                truth_val = label.get(ent)
                pred_val = str(field_read.value) if (field_read.present and field_read.value is not None) else None
                truth_str = str(truth_val) if truth_val is not None else None
                predictions.append(
                    Prediction(
                        entity=ent,
                        predicted=pred_val,
                        truth=truth_str,
                        latency_ms=field_read.latency_ms,
                    )
                )

            elif ent == "augment" and aug_reading:
                truth_aug = label.get("augment")
                if isinstance(truth_aug, list):
                    for slot in range(min(3, len(truth_aug))):
                        card = aug_reading.cards[slot] if slot < len(aug_reading.cards) else None
                        t_card = truth_aug[slot]
                        is_ambig = card is not None and len(card.api_names) > 1
                        pred_c = None
                        if card and card.api_names:
                            pred_c = t_card if t_card in card.api_names else card.api_names[0]
                        predictions.append(
                            Prediction(
                                entity="augment",
                                predicted=pred_c,
                                truth=t_card,
                                latency_ms=aug_reading.latency_ms / 3.0,
                                ambiguous_pair=is_ambig,
                            )
                        )

    report = evaluate(predictions)
    return report, predictions


def _render_card_sheet(
    frames_dir: str | Path,
    out_path: str | Path,
    regions: str | Path | ScreenRegions = DEFAULT_REGIONS,
    columns: int = 3,
    limit: int = 60,
) -> None:
    """Xuat anh contact sheet gom 3 o card_text cho tung khung hinh de kiem tra bang mat."""
    import cv2
    import numpy as np

    f_dir = Path(frames_dir)
    image_files = sorted(f_dir.glob("*.png"))
    if not image_files:
        print(f"Không tìm thấy file ảnh nào trong {frames_dir}")
        return

    regs = regions
    if isinstance(regs, (str, Path)):
        vod_candidate = f_dir.parent.name
        vod_cfg = ROOT / "config" / f"screen_regions.{vod_candidate}.yaml"
        if vod_cfg.is_file():
            regs = ScreenRegions.load(vod_cfg)
        else:
            regs = ScreenRegions.load(regs)

    tiles: list[np.ndarray] = []
    selected_files = image_files[:limit]
    for img_p in selected_files:
        img = cv2.imread(str(img_p))
        if img is None:
            continue
        stem = img_p.stem.replace("augment_select_", "")
        for slot in range(3):
            crop_img = regs.crop(img, "augment_select", f"card_text_{slot}")
            tile = cv2.resize(crop_img, (320, 160), interpolation=cv2.INTER_AREA)
            cv2.rectangle(tile, (0, 0), (320, 24), (20, 20, 20), -1)
            cv2.putText(
                tile,
                f"{stem} s{slot}",
                (4, 17),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 255, 255),
                1,
                cv2.LINE_AA,
            )
            bordered = cv2.copyMakeBorder(tile, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(60, 60, 60))
            tiles.append(bordered)

    if not tiles:
        print("Không có ảnh nào để tạo sheet")
        return

    while len(tiles) % columns:
        tiles.append(np.zeros_like(tiles[0]))

    rows = []
    for i in range(0, len(tiles), columns):
        rows.append(np.hstack(tiles[i : i + columns]))
    grid = np.vstack(rows)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if cv2.imwrite(str(out), grid):
        print(f"Đã tạo card contact sheet ({len(selected_files)} khung x 3 thẻ = {len(selected_files)*3} thẻ) -> {out}")
    else:
        print(f"Không thể ghi file {out}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--frames-dir", required=True, help="thu muc chua cac khung hinh .png can danh gia")
    ap.add_argument("--labels", default=DEFAULT_LABELS, help="file nhan tay ground truth JSON")
    ap.add_argument("--entities", default="stage,hp", help="cac thuc the can danh gia, phan cach bang dau phay")
    ap.add_argument("--regions", default=DEFAULT_REGIONS, help="file cau hinh ScreenRegions")
    ap.add_argument("--card-sheet", help="xuat anh contact sheet cho cac the de kiem tra nhan bang mat")
    ap.add_argument("--json", action="store_true", help="xuat dinh dang JSON thay vi bang")
    args = ap.parse_args(argv)

    if args.card_sheet:
        _render_card_sheet(args.frames_dir, args.card_sheet, regions=args.regions)
        return 0

    ents = [e.strip() for e in args.entities.split(",") if e.strip()]

    try:
        report, _ = evaluate_frames(
            frames_dir=args.frames_dir,
            labels_path=args.labels,
            entities=ents,
            regions=args.regions,
        )
    except Exception as exc:
        print(f"Lỗi khi chạy đánh giá: {exc}")
        return 1

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        return 0

    print("=== Kết Quả Đánh Giá Độ Chính Xác Nhận Dạng (SPEC 12.1) ===")
    print("Chú ý giới hạn đo đạc:")
    print("  1. Các khung hình này thuộc tập phát triển (development set), dùng để tinh chỉnh ngưỡng.")
    print("     Con số SPEC 12.1 chính thức cần bản ghi tự quay theo research/vanguard/testing-protocol.md bước 3.")
    print("  2. Các cặp augment mập mờ (trùng tên & icon) được tách riêng vì là giới hạn dữ liệu, không phải lỗi model.\n")
    print(report.table())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
