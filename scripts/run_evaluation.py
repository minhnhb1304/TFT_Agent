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

    report["12_1_recognition"] = {
        "skipped": "can 200-500 frame gan nhan tay - xem src/eval/recognition.py"
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
    print("Chua co frame gan nhan. Harness da san sang o src/eval/recognition.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
