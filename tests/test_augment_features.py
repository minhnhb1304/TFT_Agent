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
    carry_llm_judgements,
    keep_manual_audits,
    trait_display_map,
)
from src.knowledge.augment_catalog import AugmentCatalog
from src.knowledge.augment_features import (
    CARRY_TYPES,
    CATEGORIES,
    EXTRACTOR_VERSION,
    MANUAL_AUDITABLE,
    OFFER_ROUNDS,
    TEMPOS,
    TRAIT_COUNT_REWARDS,
    AugmentFeature,
    FeatureTable,
    check_feature,
    compose_categories,
    extract_carry_type,
    extract_categories,
    extract_deterministic,
    extract_econ_value,
    extract_frontline,
    extract_item_grants,
    extract_trait_affinity,
    extract_trait_count_reward,
    load_offer_rounds,
    parse_manual_audit,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cdragon"
COMMITTED = Path(__file__).parent.parent / "data" / "augment_features.json"
# Snapshot luot chao (datatft). Bang da commit phai sinh lai duoc tu CHINH file nay.
ROUNDS = Path(__file__).parent.parent / "data" / "augment_rounds.datatft.json"


def _load(name: str) -> dict:
    return json.load(io.open(FIXTURES / name, encoding="utf-8"))


@pytest.fixture(scope="module")
def locale() -> dict:
    return _load("en_us.trimmed.json")


@pytest.fixture(scope="module")
def table(locale) -> FeatureTable:
    return build_tier1(locale, load_offer_rounds(ROUNDS))


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


def test_items_alone_are_not_economic_value() -> None:
    """econ_value chi do vang/XP/reroll - item thuoc item_grants."""
    assert extract_econ_value("Gain 3 random components and 1 Reforger.", "X") == 0
    assert extract_econ_value("Gain a component anvil when you reach level 5.", "X") == 0


def test_incidental_stat_mention_does_not_make_frontline() -> None:
    """'Gain Health whenever you level up' la augment kinh te, khong phai frontline."""
    desc = "Buying XP costs 1 less. Gain 20 Health whenever you level up."
    assert extract_frontline(desc, "X", econ_context=True) is False
    assert extract_frontline(desc, "X", econ_context=False) is True
    # v2: chong chiu khong con la huong carry o bat ky ngu canh nao.
    assert extract_carry_type(desc, "X", econ_context=False) == "none"


def test_carry_type_never_says_tank() -> None:
    desc = "Your team gains 20 Armor and Magic Resist."
    assert extract_carry_type(desc, "X") == "none"
    assert extract_frontline(desc, "X") is True


def test_ad_and_ap_together_are_both() -> None:
    desc = "Your champions gain 10% Attack Damage and Ability Power."
    assert extract_carry_type(desc, "X") == "both"
    assert extract_carry_type("Your team gains 10% Attack Speed.", "X") == "AD"


def test_durability_tie_keeps_carry_none() -> None:
    """Hoa giua chong chiu va sat thuong la khong ro huong - giu nhu v1."""
    desc = "Your team gains 100 Health and 10% Attack Speed."
    assert extract_carry_type(desc, "X") == "none"
    assert extract_frontline(desc, "X") is False   # nua cong nua thu: khong "chu yeu"


def test_player_health_is_not_durability() -> None:
    assert extract_frontline("Heal 10 Tactician health. Gain 5 player health.", "X") is False


def test_categories_add_mandatory_labels_after_primary() -> None:
    cats = extract_categories(
        "item", 1, ["AnyComponent"], [], "wide", "Gain a component and 2 gold.", "X"
    )
    assert cats == ["item", "econ", "trait"]


def test_utility_never_shares_and_yields_to_mandatory() -> None:
    """XP thuan (econ_value 1) truoc la utility - bat bien buoc nhan econ."""
    assert compose_categories("utility", [], ["combat"]) == ["utility"]
    assert compose_categories("utility", ["econ"]) == ["econ"]


def test_cap_drops_suggestions_not_mandatory() -> None:
    assert compose_categories("combat", ["econ", "item"], ["reroll", "trait"]) == [
        "combat", "econ", "item",
    ]


def test_stats_from_a_granted_item_are_not_combat() -> None:
    desc = "Gain 2 BF Swords. Your BF Swords grant +10% Attack Speed."
    assert "combat" not in extract_categories("item", 0, ["BFSword"], [], None, desc, "X")
    desc = "Gain an Artifact anvil. Your team gains 50 Health for each item equipped."
    assert extract_categories("item", 0, ["Anvil"], [], None, desc, "X") == ["item", "combat"]


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


def test_shared_trait_reward_is_vertical() -> None:
    desc = "Champions gain 2% Attack Damage for each ally that shares a trait with them."
    assert extract_trait_count_reward(desc, "Verticality I") == "vertical"


def test_per_active_trait_reward_is_wide() -> None:
    assert extract_trait_count_reward(
        "Your units gain 1% Attack Damage for each non-unique Trait active across your team.",
        "Stand United",
    ) == "wide"
    assert extract_trait_count_reward(
        "Your team gains 2% Damage Amp for each Bronze-tier trait.", "Bronze For Life I"
    ) == "wide"
    assert extract_trait_count_reward(
        "Gain a random emblem. After fielding @N@ non-unique traits in a player combat, "
        "gain a reward.",
        "Trait Ladder",
    ) == "wide"


def test_emblem_grant_alone_is_not_a_trait_count_reward() -> None:
    """Emblem la NGUON trait (da o item_grants), khong phai phan thuong theo so trait."""
    assert extract_trait_count_reward("Gain 3 random Emblems and 2 gold.", "The Trait Tree") is None
    assert extract_trait_count_reward(
        "Gain 1 random Emblem. Your team gains 30 Health for each Emblem they are holding.",
        "Flexible",
    ) is None


# --- Bang sinh ra tu fixture ----------------------------------------------


def test_table_covers_every_augment(table, locale) -> None:
    assert len(table) == 254
    assert len(table) == len(AugmentCatalog(locale).augments)


def test_every_field_is_in_its_allowed_domain(table) -> None:
    """Scoring engine gia dinh cac mien nay - lech mot cai la diem sai am tham."""
    for feat in table.features.values():
        assert check_feature(feat) == [], feat.api_name
        assert feat.category in CATEGORIES
        assert feat.carry_type in CARRY_TYPES
        assert feat.tempo in TEMPOS
        assert 0 <= feat.econ_value <= 3
        assert feat.trait_count_reward in (None, *TRAIT_COUNT_REWARDS)
        assert 0.0 <= feat.confidence <= 1.0


def test_tier_comes_from_the_catalog_ladder(table, locale) -> None:
    """Tier trong bang phai khop ladder da do - khong tu giai lai theo cach khac."""
    catalog = AugmentCatalog(locale)
    for api, feat in table.features.items():
        assert feat.tier == catalog.get(api).tier


def test_trait_affinity_matches_measured_count(table) -> None:
    """Do duoc: dung 20/254 augment co associatedTraits, va van ban khong them cai nao."""
    assert sum(1 for f in table.features.values() if f.trait_affinity) == 20


def test_trait_count_reward_matches_audited_set(table) -> None:
    """Audit tay 2026-10-05 tren 18 augment MetaTFT gan 'trait' ma trait_affinity
    rong, cong Bronze For Life (luat bat them, doc mo ta thay dung)."""
    got = {a: f.trait_count_reward for a, f in table.features.items() if f.trait_count_reward}
    assert got == {
        "DA_VerticalityI": "vertical",
        "DA_VerticalityII": "vertical",
        "DA_VerticalityIII": "vertical",
        "DA_WeStickTogether": "vertical",
        "DA_StandUnited": "wide",
        "DA_TraitLadder": "wide",
        "DA_BronzeForLifeI": "wide",
        "DA_BronzeForLifeII": "wide",
    }
    # Truong moi khong duoc lam doi nghia trait_affinity: van chi trait cu the.
    assert all(not table.get(a).trait_affinity for a in got)


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
    """File trong repo phai sinh lai duoc, khong sai mot dong.

    File da commit co ca dong tang 2 (LLM), va LLM khong deterministic nen
    gia tri PHAN DOAN cua LLM (LLM_REFINABLE + nhan chinh cu) chi lay lai
    duoc tu chinh file (build --migrate). Moi thu con lai phai tai lap:

        extraction_method == EXTRACTOR_VERSION  ->  sinh lai giong het tu tang 1
        extraction_method bat dau bang "llm:"   ->  chi truong LLM khac tang 1;
                                                    truong suy dien (categories,
                                                    frontline) dung luat
        ca file                                 ->  la diem bat dong cua
                                                    tang 1 + --migrate + audit

    Nho the "ai do sua tay file" van bi bat, "LLM cham vao truong no khong
    duoc cham" cung bi bat, va categories/frontline sua tay ma khong khai
    trong label cung bi bat.
    """
    committed_payload = json.loads(COMMITTED.read_text(encoding="utf-8"))
    committed = committed_payload["augments"]
    generated = table.to_payload({})["augments"]
    assert set(committed) == set(generated)

    rebuilt, _ = carry_llm_judgements(table, committed_payload)
    rebuilt, _ = keep_manual_audits(rebuilt, committed_payload)
    rebuilt_rows = rebuilt.to_payload({})["augments"]
    for api, row in committed.items():
        assert row == rebuilt_rows[api], f"{api} khac voi ban sinh lai (--migrate)"
        assert check_feature(AugmentFeature(**row)) == [], api

    # Truong LLM TUYET DOI khong duoc dong den - chung chua apiName lay tu du
    # lieu co cau truc, khong phai phan doan doc tu van ban.
    immutable = (
        "api_name", "name", "tier", "trait_affinity", "item_grants", "trait_count_reward",
    )
    n_llm = 0
    for api, row in committed.items():
        method = str(row["extraction_method"])
        if method.startswith("llm:"):
            n_llm += 1
            # offer_rounds la du lieu cua snapshot: LLM khong duoc cham (audit tay thi duoc).
            assert row["offer_rounds"] == generated[api]["offer_rounds"], api
        # Dong sua tay ("manual-audit:<truong> (from <nguon cu>)") chiu cung
        # ranh gioi voi LLM: chi duoc sua truong phan doan.
        if method.startswith(("llm:", "manual-audit:")):
            for f in immutable:
                assert row[f] == generated[api][f], f"{api}.{f} bi tang 2 sua"
        # Dong audit goc tang 1: moi truong KHONG ghi trong label phai sinh
        # lai giong het - sua truong nao thi phai khai truong do.
        audit = parse_manual_audit(method)
        if audit and audit[1] == EXTRACTOR_VERSION:
            # categories la truong suy dien: doi theo nhan chinh (category)
            # va nhan bat buoc (econ_value) da audit - da kiem o vong tren.
            fields = set(audit[0]) | {"extraction_method", "categories"}
            for f, v in row.items():
                if f not in fields:
                    assert v == generated[api][f], f"{api}.{f} sua ma khong khai trong label"

    assert n_llm, "khong dong nao do LLM sinh - chay --llm chua?"

    tier1 = {a: r for a, r in committed.items() if r["extraction_method"] == EXTRACTOR_VERSION}
    assert tier1, "khong dong tang 1 nao con lai"
    for api in tier1:
        assert committed[api] == generated[api], f"{api} khac voi ban sinh lai"


@pytest.mark.skipif(not COMMITTED.exists(), reason="chua sinh data/augment_features.json")
def test_item_augments_do_not_score_as_economy() -> None:
    """Audit 2026-10-05 doi chieu MetaTFT: augment chi cho item bi LLM cham
    econ_value toi 3, va EconFit (econ_value / 3) xep chung ngang loi kinh te
    manh nhat. Item thuoc item_grants, khong thuoc econ_value.
    """
    rows = json.loads(COMMITTED.read_text(encoding="utf-8"))["augments"]
    item_only = (
        "DA_BandOfThievesII", "DA_BandOfThievesIIPlus", "DA_BuriedTreasuresIII",
        "DA_CaretakersFavor", "DA_ExtraBuckles", "DA_BeltOverflow",
        "DA_CookingPot", "DA_LuckyGlovesPlus",
    )
    for api in item_only:
        assert rows[api]["econ_value"] == 0, api
    # Item + mot it vang (< 8): chi phan vang duoc tinh -> muc 1.
    small_gold = ("DA_18_BigGrabBag", "DA_LuckyGloves", "DA_GoldenGamble", "DA_IronAssets")
    for api in small_gold:
        assert rows[api]["econ_value"] == 1, api


def test_llm_prompt_defines_econ_value_without_items() -> None:
    """Tang 2 khong co dinh nghia econ_value la nguyen nhan goc cua loi tren."""
    from scripts.build_augment_features import EXTRACT_PROMPT

    assert "econ_value: CHI tinh vang, XP, reroll" in EXTRACT_PROMPT


@pytest.mark.skipif(not COMMITTED.exists(), reason="chua sinh data/augment_features.json")
def test_loader_round_trips_the_committed_file() -> None:
    loaded = FeatureTable.load(COMMITTED)
    assert len(loaded) == 254
    assert loaded.meta["extractor_version"] == EXTRACTOR_VERSION
    assert isinstance(loaded.get("DA_18_BigGrabBag"), AugmentFeature)


@pytest.mark.skipif(not COMMITTED.exists(), reason="chua sinh data/augment_features.json")
def test_committed_tempo_is_measured_in_rounds_not_combat_seconds() -> None:
    """Moc cho dinh nghia tempo ma TempoFit can (audit doi chieu MetaTFT).

    Cong don trong mot tran la immediate: tran ke tiep da co du suc manh.
    Cong don qua cac vong / phan thuong o moc xa la scaling. Comeback Story
    manh nhat khi it mau nen phai la immediate du MetaTFT gan "scaling".
    """
    loaded = FeatureTable.load(COMMITTED)
    for api in ("DA_Ascension", "DA_ClockworkAccelerator", "DA_VerticalityI",
                "DA_BandOfThievesII", "DA_ComebackStory"):
        assert loaded.get(api).tempo == "immediate", api
    for api in ("DA_HeartOfSteel", "DA_EpicRolldown", "DA_NoScoutNoPivot",
                "DA_MoneyMonsoon", "DA_LatentForge",
                # moi stage / moi vong cho den het tran -> scaling, ca bien the +
                "DA_HardCommit", "DA_Epoch", "DA_EpochPlus", "DA_TradeSectorPlus"):
        assert loaded.get(api).tempo == "scaling", api


def test_manual_audit_label_lists_only_judgment_fields() -> None:
    assert parse_manual_audit("deterministic-v1") is None
    assert parse_manual_audit("manual-audit:econ_value,tempo (from llm:m)") == (
        ("econ_value", "tempo"), "llm:m",
    )
    with pytest.raises(ValueError):
        parse_manual_audit("manual-audit:econ-excludes-items")
    with pytest.raises(ValueError):
        parse_manual_audit("manual-audit:trait_affinity (from deterministic-v1)")
    assert "trait_count_reward" not in MANUAL_AUDITABLE


def test_rebuild_keeps_manual_audit_fields_only() -> None:
    """Sinh lai bang khong duoc xoa am tham quyet dinh audit tay."""
    fresh = FeatureTable({"DA_X": _feat(econ_value=3, tempo="scaling", category="econ")})
    old_row = _feat(
        econ_value=0, tempo="immediate", category="item",
        extraction_method="manual-audit:econ_value (from llm:m)",
    ).to_dict()
    kept_table, kept = keep_manual_audits(fresh, {"augments": {"DA_X": old_row}})
    got = kept_table.get("DA_X")
    assert kept == ["DA_X"]
    assert got.econ_value == 0                      # truong da audit: giu
    assert (got.tempo, got.category) == ("scaling", "econ")  # truong khac: bang moi
    assert got.extraction_method == f"manual-audit:econ_value (from {EXTRACTOR_VERSION})"


def test_rebuild_keeps_audited_primary_category() -> None:
    """Audit chi `category` (truoc khi co categories): nhan do giu lam nhan chinh,
    nhan bat buoc van du."""
    fresh = FeatureTable({"DA_X": _feat(category="trait", categories=["trait", "item"])})
    old_row = _feat(
        category="combat", extraction_method="manual-audit:category (from llm:m)",
    ).to_dict()
    got = keep_manual_audits(fresh, {"augments": {"DA_X": old_row}})[0].get("DA_X")
    assert got.categories[0] == "combat"
    assert check_feature(got) == []


def test_migrate_keeps_llm_judgement_and_converts_tank() -> None:
    """--migrate: phan doan LLM giu nguyen, "tank" cu -> none + frontline,
    nhan chinh cu giu, nhan bat buoc + goi y tang 1 them vao."""
    fresh = FeatureTable({"DA_X": _feat(category="reroll", categories=["reroll", "item", "trait"])})
    old = _feat(category="econ", carry_type="none", econ_value=2, tempo="scaling",
                extraction_method="llm:m").to_dict()
    old["carry_type"] = "tank"
    del old["categories"], old["frontline"]          # dong v1 chua co hai truong nay
    got = carry_llm_judgements(fresh, {"augments": {"DA_X": old}})[0].get("DA_X")
    assert (got.carry_type, got.frontline) == ("none", True)
    assert (got.econ_value, got.tempo) == (2, "scaling")
    assert got.categories == ["econ", "item", "trait"]
    assert got.extraction_method == "llm:m"
    # Chay lai tren chinh ket qua: diem bat dong, frontline khong bi mat.
    again = carry_llm_judgements(fresh, {"augments": {"DA_X": got.to_dict()}})[0].get("DA_X")
    assert again == got


# --- offer_rounds: chep tu snapshot datatft, khong suy tu van ban -------------


def test_offer_rounds_come_from_the_snapshot(locale, tmp_path) -> None:
    snap = tmp_path / "rounds.json"
    snap.write_text(json.dumps({"augments": {
        "DA_HedgeFund": {"rounds": ["2-1"], "types": [1], "list_index": 2},
        "DA_18_BigGrabBag": {"rounds": ["4-2", "3-2"], "types": [3], "list_index": 1},
    }}), encoding="utf-8")
    built = build_tier1(locale, load_offer_rounds(snap))
    assert built.get("DA_HedgeFund").offer_rounds == ["2-1"]
    assert built.get("DA_18_BigGrabBag").offer_rounds == ["3-2", "4-2"]   # thu tu OFFER_ROUNDS
    # Lose khong co trong snapshot -> rong = CHUA BIET, coi nhu chao moi luot.
    unknown = built.get("DA_Epoch")
    assert unknown.offer_rounds == [] and all(unknown.offered_at(r) for r in OFFER_ROUNDS)
    assert not built.get("DA_HedgeFund").offered_at("4-2")


def test_missing_snapshot_leaves_offer_rounds_empty(locale, tmp_path) -> None:
    assert load_offer_rounds(tmp_path / "khong-co.json") == {}
    built = build_tier1(locale)
    assert all(f.offer_rounds == [] for f in built.features.values())
    assert all(check_feature(f) == [] for f in built.features.values())


@pytest.mark.skipif(not COMMITTED.exists(), reason="chua sinh data/augment_features.json")
def test_committed_table_has_offer_rounds_for_every_augment() -> None:
    loaded = FeatureTable.load(COMMITTED)
    assert sum(1 for f in loaded.features.values() if f.offer_rounds) == 254
    assert loaded.get("DA_HedgeFund").offer_rounds == ["2-1"]


def test_rebuild_keeps_manually_audited_offer_rounds() -> None:
    """Nguon la may chu CN: sua tay offer_rounds phai song qua lan sinh lai,
    con lose khong audit thi theo snapshot moi."""
    fresh = FeatureTable({"DA_X": _feat(offer_rounds=["2-1"])})
    old_row = _feat(
        offer_rounds=["2-1", "3-2"],
        extraction_method="manual-audit:offer_rounds (from llm:m)",
    ).to_dict()
    got = keep_manual_audits(fresh, {"augments": {"DA_X": old_row}})[0].get("DA_X")
    assert got.offer_rounds == ["2-1", "3-2"]
    assert got.extraction_method == f"manual-audit:offer_rounds (from {EXTRACTOR_VERSION})"

    not_audited = _feat(offer_rounds=["4-2"], tempo="scaling",
                        extraction_method="manual-audit:tempo (from llm:m)").to_dict()
    got = keep_manual_audits(fresh, {"augments": {"DA_X": not_audited}})[0].get("DA_X")
    assert (got.offer_rounds, got.tempo) == (["2-1"], "scaling")


def test_migrate_takes_offer_rounds_from_snapshot_not_from_old_llm_row() -> None:
    fresh = FeatureTable({"DA_X": _feat(offer_rounds=["3-2"])})
    old = _feat(offer_rounds=["2-1"], tempo="scaling", extraction_method="llm:m").to_dict()
    got = carry_llm_judgements(fresh, {"augments": {"DA_X": old}})[0].get("DA_X")
    assert (got.offer_rounds, got.tempo) == (["3-2"], "scaling")


def test_loader_accepts_old_json_without_trait_count_reward(tmp_path) -> None:
    """File sinh truoc khi co truong moi van nap duoc, truong moi ve None."""
    row = _feat().to_dict()
    del row["trait_count_reward"]
    path = tmp_path / "old.json"
    path.write_text(json.dumps({"meta": {}, "augments": {"DA_X": row}}), encoding="utf-8")
    loaded = FeatureTable.load(path).get("DA_X")
    assert loaded is not None and loaded.trait_count_reward is None


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
    merged, diff = _merge(
        _feat(), {"tempo": "scaling", "econ_value": 3, "carry_type": "both"}, "m", TRAITS
    )
    assert (merged.tempo, merged.econ_value, merged.carry_type) == ("scaling", 3, "both")
    assert len(diff) == 3
    assert merged.extraction_method == "llm:m"
    # econ_value > 0 keo theo nhan bat buoc econ; nhan chinh khong doi.
    assert merged.categories[0] == "trait" and "econ" in merged.categories
    assert check_feature(merged) == []


def test_llm_cannot_write_categories_or_frontline() -> None:
    """blind-spots.md §2: LLM ghi de 13/13 nhan reroll. Nhan chi doi bang
    luat tang 1 hoac audit tay - ke ca nhan chinh `category`."""
    base = _feat()
    merged, diff = _merge(
        base,
        {"category": "combat", "categories": ["combat", "econ"], "frontline": True},
        "m", TRAITS,
    )
    assert merged.categories == base.categories
    assert merged.category == base.category
    assert merged.frontline is False
    assert diff == []
    for f in ("category", "categories", "frontline"):
        assert f not in LLM_REFINABLE


def test_llm_legacy_tank_answer_is_out_of_domain() -> None:
    merged, diff = _merge(_feat(), {"carry_type": "tank"}, "m", TRAITS)
    assert merged.carry_type == "none" and merged.frontline is False
    assert diff == []


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


def test_llm_cannot_set_trait_count_reward() -> None:
    """Truong tat dinh - khong nam trong LLM_REFINABLE."""
    merged, diff = _merge(_feat(), {"trait_count_reward": "wide"}, "m", TRAITS)
    assert merged.trait_count_reward is None
    assert diff == []
    assert "trait_count_reward" not in LLM_REFINABLE


def test_llm_cannot_write_offer_rounds() -> None:
    """offer_rounds la du lieu nguon ngoai - LLM khong doc duoc no tu mo ta."""
    base = _feat(offer_rounds=["2-1"])
    merged, diff = _merge(base, {"offer_rounds": ["4-2"], "tempo": "scaling"}, "m", TRAITS)
    assert merged.offer_rounds == ["2-1"]
    assert diff == ["tempo: 'immediate' -> 'scaling'"]
    assert _merge(base, {"offer_rounds": []}, "m", TRAITS)[1] == []
    assert "offer_rounds" not in LLM_REFINABLE


def test_out_of_domain_values_are_ignored() -> None:
    merged, diff = _merge(_feat(), {"tempo": "khong_ton_tai"}, "m", TRAITS)
    assert merged.tempo == "immediate"
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
