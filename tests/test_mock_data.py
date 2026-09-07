"""Test du lieu augment gia lap (feedback Tier 1 #1).

⚠️ Chi con AUGMENT la gia lap. data/meta_comps.json da chuyen sang du lieu
THAT (tft-match-v1) va duoc test o tests/test_meta_comps.py - ly do: do
2026-09-01, Riot da go truong `augments` khoi participant Set 18 nen chi
augment moi khong crawl duoc.

Ba bat bien duoc bao ve o day, theo thu tu quan trong:

    1. SO GIA PHAI TU KHAI BAO LA GIA. `source` = "MOCK-NOT-REAL" chay suot
       tu file CSV/JSON len den reason string hien tren overlay. Neu ai do
       doi chuoi nay thanh mot cai gi nghe nhu that, test do.

    2. w1 PHAI THUC SU SONG. Truoc khi co mock, BaseScorer tra 0.5 cho ca
       254 augment -> w1 = 0.30 la hang so, khong doi duoc thu hang, va dong
       ablation "chi w1" (SPEC 12.4) suy bien thanh sap xep alphabet. Do la
       dong quan trong nhat cua do an.

    3. SINH LAI PHAI RA Y HET. Khong dung random, khong dung hash() cua
       Python (doi theo PYTHONHASHSEED). Neu ket qua khong tai lap duoc thi
       moi con so ablation deu vo nghia.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from scripts.build_mock_stats import (
    COLUMNS,
    MOCK_SOURCE,
    SAMPLE_MAX,
    SAMPLE_MIN,
    build,
    unit_hash,
    write_csv,
)
from src.decision.scoring.base import BaseScorer
from src.decision.scoring.types import ScoringConfig
from src.game_state.models import GameState
from src.knowledge.stats_provider import CsvProvider, default_provider

STATS_CSV = Path("data/augment_stats.csv")
FEATURES = Path("data/augment_features.json")

needs_stats = pytest.mark.skipif(
    not STATS_CSV.exists(), reason="chua chay scripts/build_mock_stats.py"
)
def _api_names() -> list[str]:
    """apiName trong file mock, theo dung thu tu ghi."""
    with STATS_CSV.open(encoding="utf-8", newline="") as fh:
        return [r["api_name"] for r in csv.DictReader(fh)]


# --- Deterministic ---------------------------------------------------------


def test_unit_hash_is_stable_across_runs() -> None:
    """sha256 chu khong phai hash() - gia tri phai co dinh, khong theo seed."""
    assert unit_hash("DA_18_BigGrabBag", "place") == unit_hash("DA_18_BigGrabBag", "place")
    assert 0.0 <= unit_hash("DA_X", "n") < 1.0


def test_salts_produce_independent_streams() -> None:
    """avg_place va sample_n khong duoc tuong quan gia tao voi nhau."""
    assert unit_hash("DA_X", "place") != unit_hash("DA_X", "n")


@needs_stats
def test_regenerating_gives_a_byte_identical_file(tmp_path: Path) -> None:
    """Chay lai script phai ra file y het - dieu kien de ablation tai lap duoc."""
    rows = build(FEATURES)
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    write_csv(rows, a)
    write_csv(build(FEATURES), b)
    assert a.read_bytes() == b.read_bytes()
    assert a.read_bytes() == STATS_CSV.read_bytes(), (
        "file da commit khac ban sinh lai - hoac ai do sua tay, hoac "
        "augment_features.json da doi ma quen sinh lai stats"
    )


# --- So gia phai tu khai bao la gia ---------------------------------------


@needs_stats
def test_every_row_declares_itself_as_mock() -> None:
    with STATS_CSV.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows
    assert all(r["source"] == MOCK_SOURCE for r in rows)


@needs_stats
def test_mock_source_reaches_the_overlay_reason_string() -> None:
    """Bat bien quan trong nhat: nguoi dung PHAI nhin thay day la so gia.

    BaseScorer in stats.source nguyen van vao reason. Neu ai do doi sang in
    provider.name ("csv") thi nguon goc gia bi giau di - test nay bat duoc.
    """
    provider = CsvProvider(STATS_CSV)
    scorer = BaseScorer(provider, ScoringConfig.default())
    score = scorer(_api_names()[0], None, GameState())
    assert MOCK_SOURCE in score.reason
    assert score.detail["source"] == MOCK_SOURCE


# --- w1 phai thuc su song lai ---------------------------------------------


@needs_stats
def test_sample_sizes_clear_the_trust_threshold() -> None:
    """sample_n < min_sample_n (200) thi BaseScorer keo diem ve 0.5.

    Toan bo file duoi nguong = w1 chet lan nua, chi la chet mot cach kin dao
    hon truong hop khong co file.
    """
    min_sample_n = ScoringConfig.default().tune("base")["min_sample_n"]
    with STATS_CSV.open(encoding="utf-8", newline="") as fh:
        samples = [int(r["sample_n"]) for r in csv.DictReader(fh)]
    assert samples
    assert min(samples) >= min_sample_n
    assert SAMPLE_MIN <= min(samples) <= max(samples) <= SAMPLE_MAX


@needs_stats
def test_base_component_actually_separates_augments() -> None:
    """w1 phai cho ra diem KHAC NHAU, khong phai hang so 0.5.

    Day chinh la ly do ca hang muc nay ton tai (SPEC 12.4, dong "chi w1").
    """
    provider = CsvProvider(STATS_CSV)
    scorer = BaseScorer(provider, ScoringConfig.default())
    state = GameState()
    scores = {api: scorer(api, None, state).score for api in _api_names()[:50]}
    assert len(set(round(s, 6) for s in scores.values())) > 10
    assert max(scores.values()) - min(scores.values()) > 0.2


@needs_stats
def test_default_provider_refuses_a_self_declared_fake() -> None:
    """Bat bien then chot (2026-09-07): so gia KHONG di qua duong mac dinh.

    Truoc day `default_provider` chi hoi "file co ton tai khong". Vi bo so gia
    lap bia san `sample_n` tren 200 nen `is_evidence` tra True cho no, va vi no
    phu du ca 254 augment nen no CHE HET bang tier chuyen gia: tha mot bang
    tier that vao repo cung khong doi duoc gi, ma khong co gi bao ca.

    Gio moi dong tu khai bao la gia bi bo ngay luc nap; ca file deu gia thi
    nguon do khong duoc tinh la mot nguon.
    """
    provider = default_provider(STATS_CSV)
    assert provider.name == "null"
    assert provider.get("DA_18_BigGrabBag") is None
    assert default_provider("data/khong_ton_tai.csv").name == "null"


@needs_stats
def test_the_fake_is_still_readable_when_asked_for_explicitly() -> None:
    """Cong tat, khong phai xoa file. `build_mock_stats.py` van co ly do ton
    tai: no chung minh duong w1 chay duoc truoc khi co du lieu that."""
    provider = default_provider(STATS_CSV, allow_fabricated=True)
    assert provider.name == "composite"
    assert provider.get("DA_18_BigGrabBag") is not None


@needs_stats
def test_a_fake_csv_no_longer_shadows_an_expert_tier_list(tmp_path) -> None:
    """Hoi quy cho chinh cai bay o tren, do o dung cho no gay hai nhat."""
    import json as _json

    from src.knowledge.stats_provider import ExpertTierListProvider  # noqa: F401

    tiers = tmp_path / "tiers.json"
    tiers.write_text(
        _json.dumps({"meta": {"rated_by": "x"}, "tiers": {"S": ["DA_18_BigGrabBag"]}}),
        encoding="utf-8",
    )
    stats = default_provider(STATS_CSV, tiers).get("DA_18_BigGrabBag")
    assert stats is not None and stats.tier == "S" and stats.is_ordinal is True


# --- Cau truc du lieu ------------------------------------------------------


@needs_stats
def test_csv_header_matches_the_provider_contract() -> None:
    with STATS_CSV.open(encoding="utf-8", newline="") as fh:
        header = next(csv.reader(fh))
    assert tuple(header) == COLUMNS
    for required in CsvProvider.REQUIRED:
        assert required in header


@needs_stats
def test_stats_are_internally_consistent() -> None:
    """top4_rate suy ra TU avg_place - mock vi pham rang buoc do la mock hong."""
    with STATS_CSV.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    ranked = sorted(rows, key=lambda r: float(r["avg_place"]))
    assert float(ranked[0]["top4_rate"]) > float(ranked[-1]["top4_rate"])
    for r in rows:
        assert 3.5 <= float(r["avg_place"]) <= 5.0
        assert 0.0 < float(r["win_rate"]) < float(r["top4_rate"]) < 1.0
