"""Test phan thuan tinh toan cua scripts/directional_baseline.py.

Ba con so nay la BASELINE cua tinh nang directional, tuc chung se duoc trich
vao luan van. README dat ra nguyen tac: moi con so trong bao cao phai co mot
test dan xuat lai duoc. Day la test do.

Hai cho de sai mot cach im lang, va ca hai deu co test rieng duoi day:
  - doc `ranking` thay vi dung lai `total`: `ranking` DA sap xep nen no khong
    con noi duoc hai lua chon hoa nhau hay khong;
  - tinh scenario chi co MOT lua chon la "khong hoa": lam loang ti le theo so
    ban ghi mot the thay vi theo so quyet dinh that.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load() -> object:
    """Nap script nhu mot module - scripts/ khong phai package."""
    spec = importlib.util.spec_from_file_location(
        "directional_baseline", ROOT / "scripts" / "directional_baseline.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


db = _load()


def scenario(totals: dict[str, float]) -> dict:
    """Scenario toi thieu: mot component duy nhat voi trong so 1.0.

    Diem tong bang dung gia tri truyen vao, nen ky vong tinh tay duoc.
    """
    return {
        "weights": {"base": 1.0},
        "component_scores": {api: {"base": v} for api, v in totals.items()},
        "ranking": sorted(totals, key=lambda a: (-totals[a], a)),
    }


def write(tmp_path: Path, *scenarios: dict) -> Path:
    for i, s in enumerate(scenarios):
        (tmp_path / f"{i:03d}.json").write_text(json.dumps(s), encoding="utf-8")
    return tmp_path


# --- hoa diem ---------------------------------------------------------------


def test_exact_tie_is_counted(tmp_path):
    d = write(tmp_path, scenario({"DA_A": 0.5, "DA_B": 0.5, "DA_C": 0.4}))
    stats = db.tie_stats(d)
    assert stats["considered"] == 1
    assert stats["exact_ties"] == 1 and stats["tie_rate"] == 1.0


def test_clear_winner_is_not_a_tie(tmp_path):
    d = write(tmp_path, scenario({"DA_A": 0.9, "DA_B": 0.4, "DA_C": 0.3}))
    stats = db.tie_stats(d)
    assert stats["exact_ties"] == 0 and stats["near_ties"] == 0


def test_tie_lower_down_does_not_count(tmp_path):
    """Chi hoa o DINH moi de alphabet chon ho. Hoa giua #2 va #3 thi khong."""
    d = write(tmp_path, scenario({"DA_A": 0.9, "DA_B": 0.4, "DA_C": 0.4}))
    assert db.tie_stats(d)["exact_ties"] == 0


def test_near_tie_is_wider_than_exact_tie(tmp_path):
    d = write(tmp_path, scenario({"DA_A": 0.505, "DA_B": 0.500}))
    stats = db.tie_stats(d)
    assert stats["exact_ties"] == 0
    assert stats["near_ties"] == 1, "cach 0.005 < 0.01 phai tinh la gan hoa"


def test_single_choice_is_skipped_not_counted_as_no_tie(tmp_path):
    """Mot lua chon thi khong the hoa - phai ra khoi mau, khong lam loang ti le."""
    d = write(tmp_path, scenario({"DA_A": 0.5}), scenario({"DA_B": 0.5, "DA_C": 0.5}))
    stats = db.tie_stats(d)
    assert stats["considered"] == 1 and stats["skipped"] == 1
    assert stats["tie_rate"] == 1.0, "ban ghi mot the khong duoc ha ti le xuong 0.5"


def test_totals_are_recomputed_not_read_from_ranking(tmp_path):
    """`ranking` da sap xep nen no khong the noi ve viec hoa diem.

    Scenario duoi day hoa tuyet doi nhung `ranking` van la mot danh sach co thu
    tu. Doc `ranking` thi thay "co nguoi thang"; dung lai `total` thi thay hoa.
    """
    s = scenario({"DA_A": 0.5, "DA_B": 0.5})
    assert s["ranking"] == ["DA_A", "DA_B"], "ranking van co thu tu"
    assert db.tie_stats(write(tmp_path, s))["exact_ties"] == 1


def test_scenario_without_weights_is_skipped(tmp_path):
    """Ban ghi schema cu khong co `weights` -> khong dung lai diem duoc."""
    (tmp_path / "old.json").write_text(json.dumps({"ranking": ["DA_A", "DA_B"]}), encoding="utf-8")
    stats = db.tie_stats(tmp_path)
    assert stats["considered"] == 0 and stats["skipped"] == 1


def test_broken_file_is_skipped_not_fatal(tmp_path):
    (tmp_path / "bad.json").write_text("{khong phai json", encoding="utf-8")
    d = write(tmp_path, scenario({"DA_A": 0.5, "DA_B": 0.5}))
    stats = db.tie_stats(d)
    assert stats["considered"] == 1 and stats["skipped"] == 1


# --- do mu cua EconFit ------------------------------------------------------


def features_file(tmp_path: Path, rows: list[dict]) -> Path:
    p = tmp_path / "features.json"
    p.write_text(json.dumps({"augments": rows}), encoding="utf-8")
    return p


def test_econ_degeneracy_finds_the_largest_tied_group(tmp_path):
    rows = [
        {"api_name": "A", "econ_value": 3, "category": "econ"},
        {"api_name": "B", "econ_value": 3, "category": "econ"},
        {"api_name": "C", "econ_value": 3, "category": "reroll"},
        {"api_name": "D", "econ_value": 1, "category": "econ"},
        {"api_name": "E", "econ_value": 0, "category": "combat"},
    ]
    out = db.econ_degeneracy(features_file(tmp_path, rows))
    assert out["total"] == 5 and out["econ_positive"] == 4
    assert out["largest_group_value"] == 3 and out["largest_group_size"] == 3
    assert out["by_econ_value"] == {1: 1, 3: 3}


def test_econ_degeneracy_reports_category_even_though_no_scorer_reads_it(tmp_path):
    """`category` ton tai voi ca gia tri `reroll`, chi `_pick_demo_augments` doc.

    Bao cao no o day vi no la chung cu cho Giai phap 2: nhanh reroll DA co trong
    du lieu, chi chua ai noi vao scorer.
    """
    rows = [
        {"api_name": "A", "econ_value": 2, "category": "reroll"},
        {"api_name": "B", "econ_value": 2, "category": "econ"},
    ]
    out = db.econ_degeneracy(features_file(tmp_path, rows))
    assert out["by_category"] == {"reroll": 1, "econ": 1}
    assert out["by_category_label"] == {"reroll": 1, "econ": 1}


def test_econ_degeneracy_counts_primary_and_every_label(tmp_path):
    """by_category dem nhan chinh categories[0]; by_category_label dem moi nhan."""
    rows = [
        {"api_name": "A", "econ_value": 2, "category": "econ", "categories": ["econ", "item"]},
        {"api_name": "B", "econ_value": 0, "category": "item", "categories": ["item"]},
        {"api_name": "C", "econ_value": 1, "category": "reroll",
         "categories": ["reroll", "econ", "trait"]},
    ]
    out = db.econ_degeneracy(features_file(tmp_path, rows))
    assert out["by_category"] == {"econ": 1, "item": 1, "reroll": 1}
    assert out["by_category_label"] == {"econ": 2, "item": 2, "reroll": 1, "trait": 1}


def test_report_renders_without_crashing(tmp_path):
    d = write(tmp_path, scenario({"DA_A": 0.5, "DA_B": 0.5}))
    rows = [{"api_name": "A", "econ_value": 3, "category": "econ"}]
    text = db.report(db.tie_stats(d), db.econ_degeneracy(features_file(tmp_path, rows)))
    assert "BASELINE" in text and "100.0%" in text
