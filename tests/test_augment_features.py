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

from scripts.build_augment_features import (
    LLM_REFINABLE,
    _merge,
    build_tier1,
    trait_display_map,
)
from src.knowledge.augment_catalog import AugmentCatalog
from src.knowledge.augment_features import (
    CARRY_TYPES,
    CATEGORIES,
    EXTRACTOR_VERSION,
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
    """Phan TANG 1 cua file trong repo phai sinh lai duoc, khong sai mot dong.

    File da commit hien co ca dong tang 2 (LLM), va LLM khong deterministic
    nen KHONG the doi hoi tai lap toan bo. Nhung ranh gioi thi phai giu:

        extraction_method == "deterministic-v1"  ->  sinh lai giong het
        extraction_method bat dau bang "llm:"    ->  chi cac truong LLM
                                                     duoc phep sua moi khac

    Nho the "ai do sua tay file" van bi bat, va "LLM cham vao truong no
    khong duoc cham" cung bi bat.
    """
    committed = json.loads(COMMITTED.read_text(encoding="utf-8"))["augments"]
    generated = table.to_payload({})["augments"]
    assert set(committed) == set(generated)

    # Truong LLM TUYET DOI khong duoc dong den - chung chua apiName lay tu du
    # lieu co cau truc, khong phai phan doan doc tu van ban.
    immutable = ("api_name", "name", "tier", "trait_affinity", "item_grants")
    n_llm = 0
    for api, row in committed.items():
        if str(row["extraction_method"]).startswith("llm:"):
            n_llm += 1
            for f in immutable:
                assert row[f] == generated[api][f], f"{api}.{f} bi tang 2 sua"

    assert n_llm, "khong dong nao do LLM sinh - chay --llm chua?"

    tier1 = {a: r for a, r in committed.items() if r["extraction_method"] == EXTRACTOR_VERSION}
    assert tier1, "khong dong tang 1 nao con lai"
    for api in tier1:
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


# --- Tang 2: LLM chi duoc sua phan PHAN DOAN -------------------------------


def _feat(**kwargs) -> AugmentFeature:
    base = dict(
        api_name="DA_X",
        name="X",
        tier=2,
        category="trait",
        carry_type="none",
        trait_affinity=["DA_Riftbeast18"],
        econ_value=0,
        tempo="immediate",
        item_grants=["BFSword"],
    )
    base.update(kwargs)
    return AugmentFeature(**base)


TRAITS = {"Riftbeast": "DA_Riftbeast18", "Ravager": "DA_18_Slayer"}


def test_llm_may_refine_judgement_fields() -> None:
    """Cac truong doc duoc tu van ban mo ta thi LLM sua duoc."""
    merged, diff = _merge(_feat(), {"category": "combat", "econ_value": 3}, "m", TRAITS)
    assert merged.category == "combat"
    assert merged.econ_value == 3
    assert len(diff) == 2
    assert merged.extraction_method == "llm:m"


def test_llm_cannot_wipe_item_grants() -> None:
    """Regression: do duoc 2026-09-01 tren 8 augment dau.

    Model tra ve ['component','component',...] - chuoi tieng Anh chung chung
    thay cho apiName that. Chap nhan no la XOA du lieu tang 1 von dung, va
    ItemFit se khong con khop duoc component nao.
    """
    merged, diff = _merge(
        _feat(), {"item_grants": ["component", "component"]}, "m", TRAITS
    )
    assert merged.item_grants == ["BFSword"]
    assert diff == []


def test_llm_cannot_wipe_trait_affinity_with_an_empty_list() -> None:
    """Regression: model tra [] cho DA_18_RiftbeastTraitAugment.

    Danh sach rong gan nhu luon la "model khong biet", khong phai "augment
    nay that su khong gan trait nao".
    """
    merged, diff = _merge(_feat(), {"trait_affinity": []}, "m", TRAITS)
    assert merged.trait_affinity == ["DA_Riftbeast18"]
    assert diff == []


def test_trait_names_are_mapped_to_api_names() -> None:
    """Model noi ten hien thi; he thong chi luu apiName (feedback #6/#7)."""
    merged, _ = _merge(_feat(), {"trait_affinity": ["Ravager"]}, "m", TRAITS)
    assert merged.trait_affinity == ["DA_18_Slayer"]


def test_api_names_from_the_model_are_accepted_as_is() -> None:
    merged, _ = _merge(
        _feat(trait_affinity=[]), {"trait_affinity": ["DA_18_Slayer"]}, "m", TRAITS
    )
    assert merged.trait_affinity == ["DA_18_Slayer"]


def test_one_unmappable_trait_rejects_the_whole_list() -> None:
    """trait_affinity dung mot nua con nguy hiem hon rong - BoardFit se tin no."""
    merged, diff = _merge(
        _feat(), {"trait_affinity": ["Ravager", "KhongCoTrait"]}, "m", TRAITS
    )
    assert merged.trait_affinity == ["DA_Riftbeast18"]
    assert diff == []


def test_out_of_domain_values_are_ignored() -> None:
    merged, diff = _merge(_feat(), {"category": "khong_ton_tai"}, "m", TRAITS)
    assert merged.category == "trait"
    assert diff == []


def test_econ_value_is_clamped_to_its_domain() -> None:
    assert _merge(_feat(), {"econ_value": 99}, "m", TRAITS)[0].econ_value == 3
    assert _merge(_feat(), {"econ_value": -5}, "m", TRAITS)[0].econ_value == 0


def test_no_change_means_extraction_method_stays_tier1() -> None:
    """Khong duoc gan nhan gemini len dong ma LLM khong dong gop gi."""
    merged, diff = _merge(_feat(), {"category": "trait"}, "m", TRAITS)
    assert diff == []
    assert merged.extraction_method == EXTRACTOR_VERSION


def test_unknown_keys_from_the_model_are_ignored() -> None:
    merged, diff = _merge(_feat(), {"khong_phai_truong": "gi do"}, "m", TRAITS)
    assert diff == []
    assert merged == _feat()
