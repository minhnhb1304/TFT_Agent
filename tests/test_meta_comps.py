"""Test data/meta_comps.json - DU LIEU THAT tu tft-match-v1.

⚠️ File nay thay cho phan comp cua tests/test_mock_data.py.

Do 2026-09-01 voi Riot API key that: participant cua tft-match-v1 o Set 18
KHONG con truong `augments`, nen stats augment van phai gia lap. Nhung
`units`, `traits` va `placement` thi con nguyen, nen DOI HINH do that duoc -
va data/meta_comps.json gio la so lieu do duoc, khong phai mock.

Bat bien quan trong nhat o day: PROVENANCE. Mot con so vao duoc bao cao do
an thi phai truy nguoc duoc den nguon, va phai kem co mau. Test nay chan
viec du lieu gia len o vi tri du lieu that ma khong ai nhan ra.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.knowledge.comp_database import CompDatabase, MetaComp

META_COMPS = Path("data/meta_comps.json")

needs_comps = pytest.mark.skipif(
    not META_COMPS.exists(), reason="chua chay scripts/crawl_meta_comps.py"
)


@pytest.fixture
def payload() -> dict:
    return json.loads(META_COMPS.read_text(encoding="utf-8"))


@pytest.fixture
def db() -> CompDatabase:
    return CompDatabase.load(META_COMPS)


# --- Schema ----------------------------------------------------------------


@needs_comps
def test_loads_without_unexpected_keys(payload: dict, db: CompDatabase) -> None:
    """MetaComp(**c) splat thang JSON - thua mot key la TypeError luc nap."""
    allowed = set(MetaComp.__dataclass_fields__)
    for comp in payload["comps"]:
        assert set(comp) <= allowed, set(comp) - allowed
    assert len(db) == payload["meta"]["n"]


@needs_comps
def test_uses_real_set18_identifiers(db: CompDatabase) -> None:
    """Unit/trait/item deu la apiName THAT cua Set 18 (feedback #6/#7)."""
    for comp in db:
        assert comp.core_units
        assert all(u.startswith("DA") for u in comp.core_units), comp.name
        assert all(t.startswith("DA") for t in comp.traits), comp.name
        assert all(i.startswith(("TFT_Item_", "DA_")) for i in comp.core_items), comp.name


# --- Provenance: bat bien quan trong nhat ---------------------------------


@needs_comps
def test_every_comp_names_a_real_source(db: CompDatabase) -> None:
    """Nguon phai la tft-match-v1, KHONG duoc la mock.

    Neu test nay do vi source == MOCK-NOT-REAL thi ai do da de du lieu gia
    len dung cho du lieu that - dung loi nguy hiem nhat cua ca du an.
    """
    assert db.sources
    for source in db.sources:
        assert source.startswith("riot:tft-match-v1/"), source
        assert "MOCK" not in source.upper()


@needs_comps
def test_match_ids_and_sample_sizes_are_recorded(payload: dict) -> None:
    """Truy nguoc duoc den tung tran la diem manh nhat cua nguon nay."""
    summary = payload["meta"]["summary"]
    assert summary["matches_used"] > 0
    assert summary["participants"] >= summary["matches_used"]
    assert payload["meta"]["queue_id"] == 1100
    assert payload["meta"]["set"] == "TFTSet18"


@needs_comps
def test_sample_sizes_are_reported_per_comp(db: CompDatabase) -> None:
    """Khong co co mau thi khong phai bang chung, chi la con so."""
    for comp in db:
        assert comp.sample_n > 0, comp.name


@needs_comps
def test_best_augments_is_empty_never_invented(db: CompDatabase) -> None:
    """Riot khong cap augment o Set 18 -> de rong chu KHONG doan.

    CompSelector coi danh sach rong la "khong co tin hieu". Mot danh sach bia
    con te hon nhieu: no se duoc tin.
    """
    for comp in db:
        assert comp.best_augments == [], comp.name


@needs_comps
def test_the_augment_gap_is_documented_in_the_file(payload: dict) -> None:
    """File tu giai thich vi sao best_augments rong - khong de nguoi doc doan."""
    note = str(payload["meta"].get("note", ""))
    assert "augment" in note.lower()


# --- Tinh hop ly cua so lieu ----------------------------------------------


@needs_comps
def test_statistics_are_internally_consistent(db: CompDatabase) -> None:
    """avg_placement trong [1, 8], va comp tot hon thi top4 cao hon."""
    comps = sorted(db, key=lambda c: c.avg_placement)
    for comp in comps:
        assert 1.0 <= comp.avg_placement <= 8.0, comp.name
        assert 0.0 <= comp.win_rate <= comp.top4_rate <= 1.0, comp.name
        assert 0.0 <= comp.play_rate <= 1.0, comp.name
    if len(comps) >= 2:
        assert comps[0].top4_rate >= comps[-1].top4_rate


@needs_comps
def test_play_rates_do_not_exceed_one_in_total(db: CompDatabase) -> None:
    """play_rate la ti trong tren tong participant - tong khong the vuot 1."""
    assert sum(c.play_rate for c in db) <= 1.0 + 1e-6


@needs_comps
def test_comp_selector_can_actually_rank_these(db: CompDatabase) -> None:
    """Kiem chung dau-cuoi: du lieu that phai chay duoc qua CompSelector."""
    from src.decision.comp_selector import CompSelector
    from src.game_state.models import Champion, GameState

    best = min(db, key=lambda c: c.avg_placement)
    state = GameState(
        board=[Champion(name=u, cost=4) for u in best.core_units[:2]],
        stage="4-1",
    )
    advice = CompSelector(db).select(state)
    assert advice.top
    assert advice.best.total > 0
    # Doi hinh dang co san 2/4 core unit phai duoc xep tren doi hinh khong co gi.
    assert best.name in [c.name for c in advice.top]
