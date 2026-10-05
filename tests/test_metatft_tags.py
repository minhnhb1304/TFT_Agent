"""Test loader + phep so cua nhan tag MetaTFT (src/eval/metatft_tags.py) - OFFLINE."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.eval.metatft_tags import (
    SNAPSHOT_NOTE,
    MetaTFTTagError,
    build_snapshot,
    compare,
    format_report,
    load_snapshot,
    parse_tags,
)

ROOT = Path(__file__).resolve().parent.parent

PAYLOAD = {
    "tags": {},
    "tft_set": "TFTSet18",
    "content": {
        "content": {
            "tierList": [],
            "tags": {
                "DA_Gold": "econ",
                "DA_Bag": "items",
                "DA_Ladder": "items,trait,misc",
                "DA_Slow": "combat,scaling",
                "DA_Blank": "",
                "TFT9_NotOurs": "combat",
            },
        }
    },
}

FEATURES = {
    "DA_Gold": {"name": "Gold", "category": "econ", "econ_value": 2, "tempo": "immediate",
                "trait_affinity": [], "item_grants": [], "extraction_method": "det"},
    # item augment ma econ_value > 0 -> FP cua check econ (dung loai loi da thay o data that)
    "DA_Bag": {"name": "Bag", "category": "econ", "econ_value": 3, "tempo": "immediate",
               "trait_affinity": [], "item_grants": ["x"], "extraction_method": "llm"},
    "DA_Ladder": {"name": "Ladder", "category": "econ", "econ_value": 3, "tempo": "scaling",
                  "trait_affinity": [], "item_grants": [], "extraction_method": "llm"},
    "DA_Slow": {"name": "Slow", "category": "combat", "econ_value": 0, "tempo": "immediate",
                "trait_affinity": [], "item_grants": [], "extraction_method": "det"},
    "DA_NoTag": {"name": "NoTag", "category": "combat", "econ_value": 0, "tempo": "immediate",
                 "trait_affinity": [], "item_grants": [], "extraction_method": "det"},
}


def test_parse_tags_reads_nested_map_and_drops_blanks():
    tags = parse_tags(PAYLOAD)
    assert tags["DA_Ladder"] == ["items", "trait", "misc"]  # giu thu tu
    assert tags["DA_Blank"] == []
    assert len(tags) == 6


def test_parse_tags_rejects_unknown_tag_and_missing_map():
    bad = {"content": {"content": {"tags": {"DA_X": "combat,wizardry"}}}}
    with pytest.raises(MetaTFTTagError):
        parse_tags(bad)
    with pytest.raises(MetaTFTTagError):
        parse_tags({"tags": {}, "content": {"content": {"tierList": []}}})


def test_build_snapshot_keeps_only_catalog_and_records_missing():
    snap = build_snapshot(parse_tags(PAYLOAD), list(FEATURES), {"tft_set": "TFTSet18"})
    assert set(snap["tags"]) == {"DA_Gold", "DA_Bag", "DA_Ladder", "DA_Slow"}
    assert snap["meta"]["missing_from_metatft"] == ["DA_NoTag"]
    assert snap["meta"]["note"] == SNAPSHOT_NOTE
    assert (snap["meta"]["n_catalog"], snap["meta"]["n_tagged"]) == (5, 4)


def test_load_snapshot_roundtrip_and_validation(tmp_path):
    snap = build_snapshot(parse_tags(PAYLOAD), list(FEATURES), {})
    path = tmp_path / "tags.json"
    path.write_text(json.dumps(snap), encoding="utf-8")
    assert load_snapshot(path) == snap["tags"]

    path.write_text(json.dumps({"tags": {"DA_X": "econ"}}), encoding="utf-8")
    with pytest.raises(MetaTFTTagError):
        load_snapshot(path)


def test_compare_counts_agreement():
    snap = build_snapshot(parse_tags(PAYLOAD), list(FEATURES), {})
    cmp = compare(FEATURES, snap["tags"])
    assert cmp.n == 4
    assert cmp.missing == ["DA_NoTag"]
    # Gold (econ), Slow (combat) khop; Bag, Ladder bi gan econ nhung MT noi items
    assert cmp.category_in_tags == 2
    assert cmp.category_is_first_tag == 2

    econ = cmp.check("econ_value>0 vs econ")
    assert (econ.tp, econ.fp, econ.fn, econ.tn) == (1, 2, 0, 1)
    assert set(econ.fp_names) == {"DA_Bag", "DA_Ladder"}

    scaling = cmp.check("tempo==scaling vs scaling")
    assert (scaling.tp, scaling.fp, scaling.fn, scaling.tn) == (0, 1, 1, 2)
    assert scaling.agree == pytest.approx(0.5)

    assert {k for k, _, _ in cmp.mismatches} == {"DA_Bag", "DA_Ladder"}
    assert cmp.by_method == {"det": (2, 2), "llm": (0, 2)}
    assert "category in MT tags: 2/4 = 50.0%" in format_report(cmp)


def test_committed_snapshot_matches_catalog():
    """Snapshot da commit phai doc duoc va chi chua apiName co trong catalog."""
    tags = load_snapshot(ROOT / "data" / "augment_tags.metatft.json")
    catalog = json.loads((ROOT / "data" / "augment_features.json").read_text(encoding="utf-8"))
    assert tags
    assert set(tags) <= set(catalog["augments"])
