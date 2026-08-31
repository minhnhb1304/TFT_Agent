"""Test bang dac trung augment (SPEC 3.4.1).

Test manh nhat trong file nay la `test_committed_table_is_reproducible`: no
sinh lai bang tu fixture va doi chieu tung dong voi file da commit. Do la thu
bien `data/augment_features.json` tu "mot file JSON ai do da tao ra" thanh
"mot ket qua tai lap duoc" - dieu kien toi thieu de mot bang do may sinh ra
duoc dung lam du lieu trong bao cao khoa hoc.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from scripts.build_augment_features import build_tier1, trait_display_map
from src.knowledge.augment_catalog import AugmentCatalog
from src.knowledge.augment_features import (
    CARRY_TYPES,
    CATEGORIES,
    TEMPOS,
    AugmentFeature,
    FeatureTable,
    extract_carry_type,
    extract_deterministic,
    extract_econ_value,
    extract_item_grants,
    extract_trait_affinity,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cdragon"
COMMITTED = Path(__file__).parent.parent / "data" / "augment_features.json"


def _load(name: str) -> dict:
    return json.load(io.open(FIXTURES / name, encoding="utf-8"))


@pytest.fixture(scope="module")
def locale() -> dict:
    return _load("en_us.trimmed.json")


@pytest.fixture(scope="module")
def table(locale) -> FeatureTable:
    return build_tier1(locale)


# --- Quy tac trich xuat ----------------------------------------------------


def test_associated_traits_win_over_text() -> None:
    """associatedTraits (20/254) la nguon CHUAN, van ban chi bo sung."""
    traits = {"Ravager": "DA_18_Ravager"}
    found = extract_trait_affinity("nhac Ravager", "X", ["DA_18_Fae"], traits)
    assert found[0] == "DA_18_Fae"
    assert "DA_18_Ravager" in found


def test_trait_match_requires_word_boundary() -> None:
    """Khong duoc khop 'Fae' trong 'Faerie Dragon' - se sinh trait affinity ma."""
    traits = {"Fae": "DA_18_Fae"}
    assert extract_trait_affinity("gains Faerieness", "X", [], traits) == []


def test_reroll_counts_as_economic_value() -> None:
    """Augment cho reroll khong noi 'gold' nhung van la gia tri kinh te."""
    assert extract_econ_value("Gain 2 free Shop rerolls every round.", "X") >= 2


def test_econ_value_is_zero_without_any_economic_signal() -> None:
    assert extract_econ_value("Your team gains 10% Attack Damage.", "X") == 0


def test_interest_is_the_strongest_economic_signal() -> None:
    assert extract_econ_value("Your max interest is increased to 10.", "X") == 3


def test_incidental_stat_mention_does_not_make_a_carry_type() -> None:
    """'Gain Health whenever you level up' la augment kinh te, khong phai tank."""
    desc = "Buying XP costs 1 less. Gain 20 Health whenever you level up."
    assert extract_carry_type(desc, "X", econ_context=True) == "none"
    assert extract_carry_type(desc, "X", econ_context=False) == "tank"


def test_item_grants_catch_named_and_generic_forms() -> None:
    assert "TearOfTheGoddess" in extract_item_grants("Gain a Tear of the Goddess.", "X")
    assert "AnyComponent" in extract_item_grants("Gain 1 random component.", "X")
    assert "CompletedItem" in extract_item_grants("Gain 1 random completed item.", "X")


def test_confidence_reflects_signals_found_not_self_belief() -> None:
    """Confidence = bao nhieu tin hieu tim duoc, khong phai do tin cua ta."""
    rich = extract_deterministic(
        {"apiName": "A", "name": "A", "desc": "Gain 10 gold and a B.F. Sword.",
         "associatedTraits": ["DA_18_Fae"]},
        {},
    )
    poor = extract_deterministic({"apiName": "B", "name": "B", "desc": "Something happens."}, {})
    assert rich.confidence > poor.confidence


# --- Bang sinh ra tu fixture ----------------------------------------------


def test_table_covers_every_augment(table, locale) -> None:
    assert len(table) == 254
    assert len(table) == len(AugmentCatalog(locale).augments)


def test_every_field_is_in_its_allowed_domain(table) -> None:
    """Scoring engine gia dinh cac mien nay - lech mot cai la diem sai am tham."""
    for feat in table.features.values():
        assert feat.category in CATEGORIES
        assert feat.carry_type in CARRY_TYPES
        assert feat.tempo in TEMPOS
        assert 0 <= feat.econ_value <= 3
        assert 0.0 <= feat.confidence <= 1.0


def test_tier_comes_from_the_catalog_ladder(table, locale) -> None:
    """Tier trong bang phai khop ladder da do - khong tu giai lai theo cach khac."""
    catalog = AugmentCatalog(locale)
    for api, feat in table.features.items():
        assert feat.tier == catalog.get(api).tier


def test_trait_affinity_matches_measured_count(table) -> None:
    """Do duoc: dung 20/254 augment co associatedTraits, va van ban khong them cai nao."""
    assert sum(1 for f in table.features.values() if f.trait_affinity) == 20


def test_extraction_is_deterministic(locale) -> None:
    """Chay hai lan tren cung dau vao phai ra y het - dieu kien de audit duoc."""
    assert build_tier1(locale).to_payload({}) == build_tier1(locale).to_payload({})


def test_trait_display_map_reads_set_data(locale) -> None:
    traits = trait_display_map(locale)
    assert len(traits) == 36
    assert traits["Ravager"].startswith("DA")


# --- File da commit --------------------------------------------------------


@pytest.mark.skipif(not COMMITTED.exists(), reason="chua sinh data/augment_features.json")
def test_committed_table_is_reproducible(table) -> None:
    """File trong repo phai sinh lai duoc tu fixture, khong sai mot dong.

    Neu test nay do len thi hoac fixture da doi, hoac ai do da sua tay file
    ma khong ghi lai cach sinh - ca hai deu phai duoc phat hien ngay.
    """
    committed = json.loads(COMMITTED.read_text(encoding="utf-8"))["augments"]
    generated = table.to_payload({})["augments"]
    assert set(committed) == set(generated)
    for api in committed:
        assert committed[api] == generated[api], f"{api} khac voi ban sinh lai"


@pytest.mark.skipif(not COMMITTED.exists(), reason="chua sinh data/augment_features.json")
def test_loader_round_trips_the_committed_file() -> None:
    loaded = FeatureTable.load(COMMITTED)
    assert len(loaded) == 254
    assert loaded.meta["extractor_version"] == "deterministic-v1"
    assert isinstance(loaded.get("DA_18_BigGrabBag"), AugmentFeature)


def test_missing_augment_returns_none_not_a_fabricated_feature() -> None:
    """Bang thieu mot augment la trang thai HOP LE - khong duoc bia dac trung."""
    assert FeatureTable.empty().get("DA_KhongTonTai") is None
