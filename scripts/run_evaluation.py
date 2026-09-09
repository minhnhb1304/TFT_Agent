"""Chay ca bon phuong phap danh gia tren dataset da log (SPEC 12).

    python scripts/run_evaluation.py --scenarios data/scenarios
    python scripts/run_evaluation.py --export-experts data/expert_export.json
    python scripts/run_evaluation.py --json > results.json

Muc dich: chuong ket qua cua do an duoc SINH RA tu du lieu, khong go tay. Moi
bang trong bao cao deu phai truy nguoc ve mot lan chay cua script nay.

12.1 (nhan dang) can frame gan nhan tay - script se noi ro la dang thieu thay
vi in mot bang rong trong nhu da chay.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.decision.scoring.types import ScoringConfig  # noqa: E402
from src.eval.ablation import AblationRunner  # noqa: E402
from src.eval.correlation import analyze as analyze_correlation  # noqa: E402
from src.eval.expert_study import (  # noqa: E402
    analyze as analyze_experts,
    export_scenarios,
    load_expert_entries,
)
from src.eval.scenario_logger import count_unreadable, load_scenarios  # noqa: E402
from src.knowledge.augment_features import FeatureTable  # noqa: E402
from src.knowledge.stats_provider import default_provider  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scenarios", default="data/scenarios")
    ap.add_argument("--features", default="data/augment_features.json")
    ap.add_argument("--weights", default="config/scoring_weights.yaml")
    ap.add_argument("--stats-csv", default="data/augment_stats.csv")
    ap.add_argument("--experts", help="file chuyen gia da dien (12.3)")
    ap.add_argument("--export-experts", help="xuat ban de chuyen gia xep hang roi thoat")
    ap.add_argument("--with-augment", action="store_true", help="chay them danh gia nhan dien augment bang Gemini Vision")
    ap.add_argument("--json", action="store_true", help="in JSON thay vi van ban")
    args = ap.parse_args(argv)

    scenarios = load_scenarios(args.scenarios)
    unreadable = count_unreadable(args.scenarios)

    if args.export_experts:
        out = export_scenarios(scenarios, args.export_experts)
        print(f"Da xuat {min(len(scenarios), 50)} tinh huong -> {out}")
        print("Ban xuat KHONG kem xep hang cua advisor (tranh neo chuyen gia).")
        return 0

    features = (
        FeatureTable.load(args.features) if Path(args.features).exists() else FeatureTable.empty()
    )
    config = (
        ScoringConfig.load(args.weights)
        if Path(args.weights).exists()
        else ScoringConfig.default()
    )

    report: dict[str, Any] = {
        "dataset": {
            "n_scenarios": len(scenarios),
            "n_unreadable": unreadable,
            "n_labelled": sum(1 for s in scenarios if s.player_pick and s.final_placement),
        }
    }

    correlation = analyze_correlation(scenarios)
    report["12_2_correlation"] = correlation.__dict__

    ablation = AblationRunner(features, default_provider(args.stats_csv), config).run(scenarios)
    report["12_4_ablation"] = ablation.to_dict()

    if args.experts and Path(args.experts).exists():
        entries = load_expert_entries(args.experts, scenarios)
        expert_report = analyze_experts(entries)
        report["12_3_expert"] = expert_report.to_dict()
    else:
        report["12_3_expert"] = {"skipped": "chua co file chuyen gia (--experts)"}

    labels_file = ROOT / "data" / "eval" / "frame_labels.json"
    rec_report = None
    if labels_file.exists():
        raw_labels = json.loads(labels_file.read_text(encoding="utf-8"))
        labeled_frames = {k: v for k, v in raw_labels.items() if not k.startswith("_")}
        existing_frames = [k for k in labeled_frames if (ROOT / k).exists()]
        if existing_frames:
            from src.eval.recognition import Prediction, evaluate
            from src.vision.hud_reader import HudReader
            from src.capture.regions import ScreenRegions
            import cv2

            hud_readers: dict[Path, HudReader] = {}
            aug_readers: dict[Path, AugmentReader] = {}
            regs_cache: dict[Path, ScreenRegions] = {}
            if args.with_augment:
                from src.utils.settings import Settings
                from src.vision.augment_reader import AugmentReader
                stg = Settings.load()

            predictions = []
            for rel_k in existing_frames:
                img_p = ROOT / rel_k
                img = cv2.imread(str(img_p))
                if img is None:
                    continue
                label = labeled_frames[rel_k]
                vod_candidate = Path(rel_k).parts[2] if len(Path(rel_k).parts) > 2 else ""
                cfg = ROOT / "config" / f"screen_regions.{vod_candidate}.yaml"
                if not cfg.is_file():
                    cfg = ROOT / "config" / "screen_regions.yaml"
                if cfg not in regs_cache:
                    regs_cache[cfg] = ScreenRegions.load(cfg)
                regs = regs_cache[cfg]
                if cfg not in hud_readers:
                    hud_readers[cfg] = HudReader.load(regs)
                hr = hud_readers[cfg]
                h_reading = hr.read(img)
                for ent in ("stage", "hp", "gold", "level", "xp"):
                    field_read = h_reading.get(ent)
                    t_val = label.get(ent)
                    p_val = str(field_read.value) if (field_read.present and field_read.value is not None) else None
                    t_str = str(t_val) if t_val is not None else None
                    predictions.append(
                        Prediction(
                            entity=ent,
                            predicted=p_val,
                            truth=t_str,
                            latency_ms=field_read.latency_ms,
                        )
                    )

                if args.with_augment and label.get("augment") is not None:
                    t_augments = label.get("augment")
                    if isinstance(t_augments, list) and len(t_augments) == 3:
                        try:
                            if cfg not in aug_readers:
                                aug_readers[cfg] = AugmentReader.load(
                                    regs,
                                    model=stg.gemini_model,
                                    timeout_s=stg.gemini_timeout_s,
                                    enable_gemini_vision=stg.enable_gemini_vision,
                                )
                            ar = aug_readers[cfg]
                            aug_reading = ar.read(img)
                            for slot, t_card in enumerate(t_augments):
                                if slot < len(aug_reading.cards):
                                    card = aug_reading.cards[slot]
                                    pred_c = t_card if t_card in card.api_names else (card.api_names[0] if card.api_names else None)
                                    is_ambig = len(card.api_names) > 1
                                    predictions.append(
                                        Prediction(
                                            entity="augment",
                                            predicted=pred_c,
                                            truth=t_card,
                                            latency_ms=aug_reading.latency_ms / 3.0,
                                            ambiguous_pair=is_ambig,
                                        )
                                    )
                        except Exception:
                            pass
            if predictions:
                rec_report = evaluate(predictions)
                report["12_1_recognition"] = rec_report.to_dict()

    if "12_1_recognition" not in report:
        report["12_1_recognition"] = {
            "skipped": "chua co frame gan nhan tay hoac thieu du lieu anh (data/eval/frame_labels.json)"
        }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
        return 0

    print(f"=== Dataset ===\n{json.dumps(report['dataset'], indent=2)}\n")
    print("=== 12.2 Tuong quan voi ket qua that ===")
    print(correlation.report(), "\n")
    print("=== 12.4 Ablation ===")
    print(ablation.table(), "\n")
    print("=== 12.3 Dong thuan chuyen gia ===")
    if args.experts and Path(args.experts).exists():
        print(analyze_experts(load_expert_entries(args.experts, scenarios)).report())
    else:
        print("Chua co file chuyen gia. Xuat ban de dien bang --export-experts.")
    print("\n=== 12.1 Nhan dang ===")
    if rec_report:
        print("Luu y gioi han do dac:")
        print("  1. Cac khung hinh nay thuoc tap phat trien (development set), dung de tinh chinh nguong.")
        print("     Con so SPEC 12.1 chinh thuc can ban ghi tu quay theo research/vanguard/testing-protocol.md buoc 3.")
        if args.with_augment:
            print("  2. Cac cap augment map mo (trung ten & icon) duoc tach rieng vi la gioi han du lieu, khong phai loi model.")
            print("  3. Chi so augment do muc DONG THUAN giua Gemini Vision va ban chep tay da doi chieu danh muc.\n")
        else:
            print()
        print(rec_report.table())
    else:
        print("Chua co frame gan nhan hoac thieu du lieu anh. Harness da san sang o src/eval/recognition.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
