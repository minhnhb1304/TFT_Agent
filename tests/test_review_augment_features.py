"""Test trang duyet tay: luot chao (offer_rounds) va co xem lai tempo.

Chi test ham thuan cua scripts/review_augment_features.py, khong mo server va
khong dung toi file review that cua nguoi dung.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "review_augment_features", ROOT / "scripts" / "review_augment_features.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rv = _load()


def _row(**over) -> dict:
    row = {"api_name": "DA_X", "name": "X", "tier": 2, "category": "econ", "categories": ["econ"],
           "carry_type": "none", "frontline": False, "tempo": "immediate", "econ_value": 3,
           "trait_affinity": [], "item_grants": [], "board_condition": None, "offer_rounds": ["2-1"]}
    row.update(over)
    return row


def _entry(verdict="ok", fix=None, **orig) -> dict:
    e = {"verdict": verdict, "note": "",
         "original": {"categories": ["econ"], "category": "econ", "carry_type": "none", "frontline": False,
                      "tempo": "immediate", "econ_value": 3, "trait_affinity": [], "item_grants": [],
                      "board_condition": None, **orig}}
    if fix is not None:
        e["fix"] = fix
    return e


def test_build_rows_falls_back_to_datatft_when_feature_has_no_rounds(tmp_path):
    features = {"DA_A": {"api_name": "DA_A", "name": "A", "offer_rounds": []},
                "DA_B": {"api_name": "DA_B", "name": "B", "offer_rounds": ["4-2"]},
                "DA_C": {"api_name": "DA_C", "name": "C"}}
    datatft = {"DA_A": {"rounds": ["3-2", "2-1"], "types": [1, 3]}, "DA_B": {"rounds": ["2-1"], "types": [2]}}
    rows = {r["api_name"]: r for r in rv.build_rows(features, {"items": []}, tmp_path / "none.json", datatft)}
    assert rows["DA_A"]["offer_rounds"] == ["2-1", "3-2"]          # sap theo thu tu van dau
    assert rows["DA_A"]["offer_rounds_source"] == "datatft"
    assert rows["DA_A"]["datatft_types"] == [1, 3]                 # ma tho, khong dich
    assert rows["DA_B"]["offer_rounds"] == ["4-2"]                 # bang feature thang snapshot
    assert rows["DA_B"]["offer_rounds_source"] == "feature"
    assert rows["DA_C"]["offer_rounds"] == [] and rows["DA_C"]["offer_rounds_source"] is None


def test_load_datatft_missing_file_is_empty(tmp_path):
    assert rv.load_datatft(tmp_path / "missing.json") == {}
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"meta": {}, "augments": {"DA_A": {"rounds": ["2-1"]}}}), encoding="utf-8")
    assert rv.load_datatft(p) == {"DA_A": {"rounds": ["2-1"]}}


def test_accepted_immediate_on_2_1_only_is_flagged_without_changing_label():
    entry = _entry("ok")
    out = rv.migrate_review(entry, _row())
    assert any(r.startswith("tempo: lõi chỉ xuất hiện ở 2-1") for r in out["recheck"])
    assert out["original"]["tempo"] == "immediate" and "fix" not in out
    assert "recheck" not in entry                                   # ban goc khong bi dung toi


def test_wrong_verdict_that_kept_immediate_is_flagged():
    out = rv.migrate_review(_entry("wrong", fix={"econ_value": 2}), _row())
    assert any(r.startswith("tempo:") for r in out.get("recheck", []))


def test_no_tempo_flag_cases():
    def flagged(entry, row):
        return any(r.startswith("tempo:") for r in rv.migrate_review(entry, row).get("recheck", []))

    assert not flagged(_entry("wrong", fix={"tempo": "scaling"}), _row())       # da sua thanh scaling
    assert not flagged(_entry("unsure"), _row())                                # chua chap nhan gi
    assert not flagged(_entry("ok"), _row(offer_rounds=["2-1", "3-2"]))         # khong chi 2-1
    assert not flagged(_entry("ok"), _row(offer_rounds=[]))                     # chua ro luot
    assert not flagged(_entry("ok", tempo="scaling"), _row(tempo="scaling"))
    assert not flagged(_entry("ok", offer_rounds=["2-1"]), _row())              # duyet khi da thay luot
    assert not flagged(_entry("wrong", fix={"offer_rounds": ["2-1", "4-2"]}), _row())


def test_validate_fix_checks_offer_rounds():
    f = next(iter(rv.FeatureTable.load(ROOT / "data" / "augment_features.json").features.values()))
    row = f.to_dict()
    assert rv.validate_fix(row, {"offer_rounds": ["2-1", "4-2"]}) == []
    assert rv.validate_fix(row, {"offer_rounds": []}) == []                     # rong = chua ro
    assert rv.validate_fix(row, {"offer_rounds": ["5-1"]})
    assert rv.validate_fix(row, {"offer_rounds": ["2-1", "2-1"]})
    assert rv.validate_fix(row, {"offer_rounds": "2-1"})


def test_offer_rounds_is_a_review_label_field():
    assert "offer_rounds" in rv.LABEL_FIELDS
