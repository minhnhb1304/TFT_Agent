"""Do baseline cho danh gia dinh huong loi (docs/directional-augment/baseline.md).

    .venv\\Scripts\\python scripts/directional_baseline.py

Ba con so o day la "TRUOC" cua tinh nang directional. Chung BIEN MAT ngay khi
scorer doi, nen phai chot lai truoc khi code dong vao - khong co "truoc" thi
"sau" chi con la lap luan.

1. `tie_rate`       - bao nhieu phan tram quyet dinh co top-1 HOA TUYET DOI, tuc
                      thu tu alphabet cua `api_name` chon ho nguoi choi.
                      `augment_advisor.rank()` sort theo `(-total, api_name)`:
                      tat dinh cho test, nhung khong co can cu chien thuat nao.
2. `near_tie_rate`  - top-1 va #2 cach nhau duoi `NEAR`. Day la vung ma mot ly do
                      re nhanh phai len tieng, du xep hang co doi hay khong.
3. `econ_degeneracy`- bao nhieu loi kinh te dung chung MOT gia tri `econ_value`.
                      `EconFit` khong tach duoc XP / reroll / gold, nen ca nhom
                      nay nhan diem va cau giai thich gan nhu y het nhau.

Doc `data/scenarios/*.json` (do ScenarioLogger ghi) va `data/augment_features.json`.
KHONG cham mang, khong can game, khong can Gemini.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
NEAR = 0.01


def totals_of(scenario: dict[str, Any]) -> list[float]:
    """Diem tong cua tung lua chon, dung lai tu component_scores x weights.

    Tinh lai thay vi doc `ranking`: `ranking` da la KET QUA da sap xep nen no
    khong con noi duoc hai lua chon co hoa nhau hay khong - dung cai ta can do.
    """
    comps = scenario.get("component_scores") or {}
    weights = scenario.get("weights") or {}
    if not comps or not weights:
        return []
    return [
        sum(float(weights.get(name, 0.0)) * float(value) for name, value in parts.items())
        for parts in comps.values()
    ]


def tie_stats(scenario_dir: Path, near: float = NEAR) -> dict[str, Any]:
    """Ti le hoa diem o dinh tren toan bo scenario da log."""
    considered = exact = close = 0
    skipped = 0
    for path in sorted(scenario_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            skipped += 1
            continue
        totals = sorted(totals_of(data), reverse=True)
        if len(totals) < 2:
            # Mot lua chon thi khong the hoa. Bo ra khoi mau thay vi tinh la
            # "khong hoa" - neu khong thi ti le loang theo so ban ghi mot the.
            skipped += 1
            continue
        considered += 1
        gap = totals[0] - totals[1]
        if gap < 1e-9:
            exact += 1
        if gap < near:
            close += 1
    return {
        "considered": considered,
        "skipped": skipped,
        "exact_ties": exact,
        "near_ties": close,
        "tie_rate": exact / considered if considered else 0.0,
        "near_tie_rate": close / considered if considered else 0.0,
        "near_threshold": near,
    }


def _categories(row: dict[str, Any]) -> list[str]:
    """categories cua row; row cu chi co `category` thi coi nhu mot nhan."""
    cats = row.get("categories")
    if isinstance(cats, list) and cats:
        return [str(c) for c in cats]
    cat = row.get("category")
    return [str(cat)] if cat is not None else []


def _primary(row: dict[str, Any]) -> str | None:
    cats = _categories(row)
    return cats[0] if cats else None


def econ_degeneracy(features_path: Path) -> dict[str, Any]:
    """Bao nhieu loi kinh te dung chung mot gia tri `econ_value`."""
    raw = json.loads(features_path.read_text(encoding="utf-8"))
    rows = raw.get("augments") or raw.get("features") or raw
    if isinstance(rows, dict):
        rows = list(rows.values())
    econ = [r for r in rows if float(r.get("econ_value") or 0) > 0]
    by_value = collections.Counter(int(r.get("econ_value") or 0) for r in econ)
    top_value, top_count = (by_value.most_common(1) or [(0, 0)])[0]
    return {
        "total": len(rows),
        "econ_positive": len(econ),
        "by_econ_value": dict(sorted(by_value.items())),
        "largest_group_value": top_value,
        "largest_group_size": top_count,
        # Nhan chinh (category = categories[0]) - moi lose dem dung mot lan
        "by_category": dict(collections.Counter(_primary(r) for r in rows)),
        # Moi nhan trong categories (1-3/lose) - tong co the vuot so lose
        "by_category_label": dict(
            collections.Counter(c for r in rows for c in _categories(r))
        ),
    }


def report(stats: dict[str, Any], econ: dict[str, Any]) -> str:
    n = stats["considered"]
    lines = [
        "BASELINE — danh gia dinh huong loi",
        "",
        f"scenario co >= 2 lua chon        : {n}  (bo qua {stats['skipped']})",
        f"top-1 HOA TUYET DOI (alphabet)   : {stats['exact_ties']}"
        f"  = {stats['tie_rate'] * 100:.1f}%",
        f"top-1 vs #2 cach < {stats['near_threshold']}         : {stats['near_ties']}"
        f"  = {stats['near_tie_rate'] * 100:.1f}%",
        "",
        f"augment                          : {econ['total']}",
        f"co econ_value > 0                : {econ['econ_positive']}"
        f"  = {econ['econ_positive'] / econ['total'] * 100:.1f}%",
        f"nhom lon nhat cung econ_value={econ['largest_group_value']} : "
        f"{econ['largest_group_size']}/{econ['econ_positive']}",
        f"phan bo econ_value               : {econ['by_econ_value']}",
        f"category (khong scorer nao doc)  : {econ['by_category']}",
        f"categories (moi nhan)            : {econ['by_category_label']}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Baseline cho danh gia dinh huong loi")
    ap.add_argument("--scenarios", default=str(ROOT / "data" / "scenarios"))
    ap.add_argument("--features", default=str(ROOT / "data" / "augment_features.json"))
    ap.add_argument("--near", type=float, default=NEAR)
    ap.add_argument("--json", action="store_true", help="in JSON thay vi bang")
    args = ap.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        # Console Windows mac dinh cp1252 lam chuoi co dau crash - cung bai hoc
        # voi src/eval/reroll_ablation.py.
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    stats = tie_stats(Path(args.scenarios), args.near)
    econ = econ_degeneracy(Path(args.features))
    if args.json:
        print(json.dumps({"ties": stats, "econ": econ}, indent=2, ensure_ascii=False))
    else:
        print(report(stats, econ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
