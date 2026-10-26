"""Test AugmentCatalog - khoa lai moi con so da do o research/vision-stack/augments.md.

Muc dich cua file nay khac cac file test thong thuong: no bien ket qua nghien cuu
thanh REGRESSION SUITE CHAY DUOC. Moi con so trich trong bao cao do an deu duoc
mot test o day dan xuat lai tu du lieu that.

Neu Riot doi du lieu o ban patch sau, cac test nay do len va chi dung cho ta
biet chinh xac cai gi da doi - thay vi de advisor am tham dua ra tu van sai.
"""

from __future__ import annotations

import json
import io
from pathlib import Path

import pytest

from src.knowledge.augment_catalog import (
    TIER_OVERRIDES_PATH,
    AugmentCatalog,
    load_tier_overrides,
    diacritic_collisions,
    normalize,
    resolve_tier,
    roman_family,
    strip_tier_token,
    variant_base_api,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cdragon"
DATATFT_SNAPSHOT = Path(__file__).parent.parent / "data" / "augment_rounds.datatft.json"


def _load(name: str) -> dict:
    return json.load(io.open(FIXTURES / name, encoding="utf-8"))


@pytest.fixture(scope="module")
def en() -> AugmentCatalog:
    return AugmentCatalog(_load("en_us.trimmed.json"))


@pytest.fixture(scope="module")
def vi() -> AugmentCatalog:
    return AugmentCatalog(_load("vi_vn.trimmed.json"))


# --- kich thuoc catalog ----------------------------------------------------


def test_catalog_size(en: AugmentCatalog, vi: AugmentCatalog) -> None:
    """Set 18 co dung 254 augment (apiName bat dau DA_, isAugment=true)."""
    assert len(en) == 254
    assert len(vi) == 254


# --- ladder giai tier ------------------------------------------------------


def test_tier_ladder_reproduces_measured_counts(en: AugmentCatalog) -> None:
    """Giai het 254/254 voi dung phan bo nguon tier da do 2026-10-06.

    Ba nguon dau la ladder icon cua resolve_tier, hai nguon ke do buoc
    catalog ghi (quy tac A va B cua nguoi dung), nguon cuoi la file override.
    """
    counts = en.tier_source_counts()
    assert counts == {
        "missing-tN": 38,
        "icon roman": 149,
        "icon digit": 26,
        "variant-of-base": 33,
        "roman-order": 1,
        "user-override": 7,
    }
    assert sum(counts.values()) == 254
    assert "UNRESOLVED" not in counts


def test_tier_distribution(en: AugmentCatalog, vi: AugmentCatalog) -> None:
    """70 / 115 / 69 sau khi sua tier 2026-10-06 (truoc do 62 / 132 / 60).

    Chi voi quy tac A + B (khong override) la 68 / 117 / 69.
    """
    for cat in (en, vi):
        by_tier = {t: sum(1 for a in cat.augments if a.tier == t) for t in (1, 2, 3)}
        assert by_tier == {1: 70, 2: 115, 3: 69}
    rules_only = AugmentCatalog(_load("en_us.trimmed.json"), tier_overrides={})
    by_tier = {t: sum(1 for a in rules_only.augments if a.tier == t) for t in (1, 2, 3)}
    assert by_tier == {1: 68, 2: 117, 3: 69}


def test_every_augment_has_valid_tier(en: AugmentCatalog) -> None:
    assert all(1 <= a.tier <= 3 for a in en.augments)


def test_name_suffix_is_not_an_absolute_tier() -> None:
    """Plus / PlusPlus / so la ma trong ten KHONG con quyet dinh tier tuyet doi."""
    assert resolve_tier("DA_XPlusPlus", "X++", "a/b/x_i.tex") == (1, "icon roman")
    assert resolve_tier("DA_XPlus", "X+", "a/b/x_iii.tex") == (3, "icon roman")
    assert resolve_tier("DA_XII", "X II", "a/b/x_iii.tex") == (3, "icon roman")
    assert resolve_tier("DA_XI", "X I", "a/b/missing-t2.tex") == (2, "missing-tN")


def test_plus_variants_share_the_base_tier(en: AugmentCatalog) -> None:
    """Quy tac A: `+` / `++` la cung augment chao muon hon -> cung tier ban goc."""
    checked = 0
    for a in en.augments:
        base_api = variant_base_api(a.api_name)
        if base_api is None or en.get(base_api) is None:
            continue
        assert a.tier == en.get(base_api).tier, a.api_name
        assert a.tier_source == "variant-of-base"
        checked += 1
    assert checked == 33

    # Vi du tung bi gan nguoc: ban "bac" ++ la tier 3, ban "kim cuong" + la tier 2.
    assert en.get("DA_SilverDestinyPlusPlus").tier == 1
    assert en.get("DA_PrismaticDestinyPlus").tier == 3
    # Ho vua co so la ma vua co `+`: bien the theo ban goc DA_BandOfThievesII.
    assert variant_base_api("DA_BandOfThievesIIPlus") == "DA_BandOfThievesII"
    assert {
        en.get(api).tier
        for api in ("DA_BandOfThievesII", "DA_BandOfThievesIIPlus", "DA_BandOfThievesIIPlusPlus")
    } == {3}
    # `Plus` nam giua apiName.
    assert variant_base_api("DA_18_PrimalAugmentPlus_Sivir") == "DA_18_PrimalAugment_Sivir"
    assert variant_base_api("DA_HedgeFund") is None


def test_variants_without_base_are_reported_not_guessed(en: AugmentCatalog) -> None:
    """7 bien the khong co ban goc trong catalog: giu tier icon va bao cao."""
    gaps = dict(en.tier_rule_gaps)
    assert set(gaps) == {
        "DA_NestingDollsPlus",
        "DA_NestingDollsPlusPlus",
        "DA_18_WispRebatePlus",
        "DA_18_WispRebatePlusPlus",
        "DA_InvestedPlus",
        "DA_InvestedPlusPlus",
        "DA_MoneyHungryPlus",
    }
    assert all(reason.startswith("variant-of-base") for reason in gaps.values())
    for api in gaps:
        a = en.get(api)
        assert a.tier == resolve_tier(a.api_name, a.name, a.icon)[0]


def test_roman_numeral_is_rank_within_family_not_absolute(en: AugmentCatalog) -> None:
    """Quy tac B: so la ma chi cho THU TU. "I" co the da la gold -> "II" la prismatic."""
    bronze_i = en.get("DA_BronzeForLifeI")
    bronze_ii = en.get("DA_BronzeForLifeII")
    assert (bronze_i.tier, bronze_ii.tier) == (2, 3)
    assert bronze_ii.tier_source == "icon roman"  # icon bronzeforlife_iii.tex

    # Moi ho la ma trong catalog deu tang ngat theo so.
    families: dict[str, list[tuple[int, int]]] = {}
    for a in en.augments:
        fam = roman_family(a.api_name, a.name)
        if fam and variant_base_api(a.api_name) is None:
            families.setdefault(fam[0], []).append((fam[1], a.tier))
    multi = {k: sorted(v) for k, v in families.items() if len(v) > 1}
    assert len(multi) >= 10
    for key, members in multi.items():
        tiers = [t for _, t in members]
        assert tiers == sorted(set(tiers)), key


def test_roman_order_overrides_a_reused_icon(en: AugmentCatalog) -> None:
    """Cho duy nhat icon vi pham thu tu: hai "Tons of Stats!" dung chung icon _ii.

    Ban I la tier 2 theo icon -> ban II phai cao hon -> 3, nguon "roman-order".
    Day la augment DUY NHAT ma quy tac A + B lam khac icon cua chinh no (quy
    tac cu: 30); 7 cai con lai trong icon_tier_conflicts la "user-override".
    """
    one = en.get("DA_TonsOfStatsI")
    two = en.get("DA_TonsOfStatsII")
    assert "tons-of-stats-ii" in one.icon.lower() and "tons-of-stats-ii" in two.icon.lower()
    assert (one.tier, one.tier_source) == (2, "icon roman")
    assert (two.tier, two.tier_source) == (3, "roman-order")
    by_source: dict[str, list[str]] = {}
    for a in en.icon_tier_conflicts():
        by_source.setdefault(a.tier_source, []).append(a.api_name)
    assert by_source["roman-order"] == ["DA_TonsOfStatsII"]
    assert sorted(by_source["user-override"]) == sorted(load_tier_overrides())
    assert set(by_source) == {"roman-order", "user-override"}


def test_roman_order_never_exceeds_tier_3() -> None:
    """Ho khong the thoa (I da la 3) -> giu nguyen va bao cao, khong doan."""
    def item(api: str, name: str, icon: str) -> dict:
        return {"apiName": api, "name": name, "icon": icon, "isAugment": True}

    cat = AugmentCatalog(
        {"items": [item("DA_ZedI", "Zed I", "a/zed_iii.tex"), item("DA_ZedII", "Zed II", "a/zed_iii.tex")]},
        tier_overrides={},
    )
    assert cat.get("DA_ZedII").tier == 3
    assert cat.get("DA_ZedII").tier_source == "icon roman"
    assert [api for api, _ in cat.tier_rule_gaps] == ["DA_ZedII"]


GROUP_C = {
    "DA_PandorasBench": 1,
    "DA_DeadlierBlades": 3,
    "DA_DeadlierCaps": 3,
    "DA_Flexible": 3,
    "DA_ForgeAFriend": 1,
    "DA_ConstructACompanion": 2,
    "DA_WovenMagic": 2,
}


def test_user_overrides_fix_group_c(en: AugmentCatalog) -> None:
    """7 augment icon CDragon sai tier; nguoi dung xac nhan 2026-10-06.

    Khong luat nao suy ra duoc tu CDragon nen chung nam trong FILE DU LIEU
    data/augment_tier_overrides.json. Xem docs/offer-rounds/tier-mismatch.md.
    """
    assert load_tier_overrides() == GROUP_C
    assert json.loads(TIER_OVERRIDES_PATH.read_text(encoding="utf-8"))["meta"]["confirmed_by"]
    for api, tier in GROUP_C.items():
        a = en.get(api)
        assert (a.tier, a.tier_source) == (tier, "user-override")
        assert resolve_tier(a.api_name, a.name, a.icon)[0] != tier  # icon noi khac


def test_overrides_are_optional_and_checked(tmp_path: Path) -> None:
    """Khong co file -> catalog van dung duoc; override sai ten -> dung ngay."""
    assert load_tier_overrides(tmp_path / "khong-co.json") == {}

    locale = _load("en_us.trimmed.json")
    plain = AugmentCatalog(locale, tier_overrides={})
    assert plain.get("DA_PandorasBench").tier == 2  # theo icon pandoras-bench-ii
    assert "user-override" not in plain.tier_source_counts()

    with pytest.raises(ValueError, match="DA_KhongTonTai"):
        AugmentCatalog(locale, tier_overrides={"DA_KhongTonTai": 2})

    bad = tmp_path / "bad.json"
    bad.write_text('{"tiers": {"DA_PandorasBench": 4}}', encoding="utf-8")
    with pytest.raises(ValueError):
        load_tier_overrides(bad)


def test_tiers_agree_with_datatft_lists(en: AugmentCatalog) -> None:
    """Guard: sau A + B + override, tier cua ta == list_index + 1 cua datatft.

    Test nay chi SO SANH. Khong code nao duoc doc list_index LAM tier
    (docs/offer-rounds/source.md): tier van suy tu CDragon + luat + override.
    Do len nghia la CDragon/datatft doi du lieu -> xem lai, dung ep cho khop.
    """
    snapshot = json.loads(DATATFT_SNAPSHOT.read_text(encoding="utf-8"))["augments"]
    compared = [a for a in en.augments if a.api_name in snapshot]
    assert len(compared) == 254
    disagree = {
        a.api_name: (a.tier, snapshot[a.api_name]["list_index"] + 1)
        for a in compared
        if a.tier != snapshot[a.api_name]["list_index"] + 1
    }
    assert disagree == {}


def test_gold_silver_suffix_is_not_a_tier_signal(en: AugmentCatalog) -> None:
    """Hau to _Gold/_Silver KHONG phai tin hieu tier - day la bay thuc su.

    Truc giac cho rang Gold=3, Silver=2. Du lieu bac bo:
    DA_GlassCannon_Gold co ten "Glass Cannon II" (tier 2), va
    DA_GlassCannon_Silver co ten "Glass Cannon I" (tier 1).
    """
    gold = en.get("DA_GlassCannon_Gold")
    silver = en.get("DA_GlassCannon_Silver")
    assert gold is not None and silver is not None
    assert gold.name == "Glass Cannon II" and gold.tier == 2
    assert silver.name == "Glass Cannon I" and silver.tier == 1


def test_icon_separator_both_underscore_and_hyphen() -> None:
    """Hau to tier dung CA _ LAN - . Chi bat _ii. thi bo sot 49/254 (19%)."""
    assert resolve_tier("DA_X", "X", "a/b/thing_ii.tex") == (2, "icon roman")
    assert resolve_tier("DA_X", "X", "a/b/thing-ii.tex") == (2, "icon roman")
    assert resolve_tier("DA_X", "X", "a/b/thing-iii.tex") == (3, "icon roman")


def test_placeholder_encodes_tier() -> None:
    """Nghich ly: placeholder lam template matching bat kha thi lai ma hoa tier."""
    assert resolve_tier("DA_X", "X", "augments/hexcore/missing-t3.tex") == (3, "missing-tN")


# --- chuan hoa & dau tieng Viet --------------------------------------------


def test_normalize_strips_diacritics_and_d_stroke() -> None:
    assert normalize("Tàn Phá") == "tan pha"
    assert normalize("Cự Thạch") == "cu thach"
    assert normalize("Đấu Sĩ") == "dau si"


def test_no_diacritic_collisions_in_vietnamese(vi: AugmentCatalog) -> None:
    """Bo TOAN BO dau van khong gay va cham - do tren du lieu that.

    Day la ly do mot OCR CPU nhe la du: khong can engine nang de giu dau.
    Luu y: cac cap TRUNG TEN san (xem duoi) khong tinh la va cham do mat dau.
    """
    names = [a.name for a in vi.augments]
    collisions = diacritic_collisions(names)
    # Chi con dung cac nhom von da trung ten tu truoc khi bo dau.
    already_dup = {k for k, v in vi.ambiguous_groups.items()}
    genuinely_new = {k for k in collisions if k not in already_dup}
    assert genuinely_new == set()


def test_no_diacritic_collisions_in_traits() -> None:
    """36 trait tieng Viet, 0 va cham sau khi bo dau."""
    data = _load("vi_vn.trimmed.json")
    traits = [t["name"] for t in data["setData"][0]["traits"]]
    assert len(traits) == 36
    assert diacritic_collisions(traits) == {}


def test_strip_tier_token() -> None:
    assert strip_tier_token("Bronze For Life II") == "Bronze For Life"
    assert strip_tier_token("Golden Gamble+") == "Golden Gamble"
    assert strip_tier_token("Nesting Dolls++") == "Nesting Dolls"
    assert strip_tier_token("Hedge Fund") == "Hedge Fund"


# --- gioi han cung: cac cap khong phan biet duoc ---------------------------


def test_ambiguous_group_counts(en: AugmentCatalog, vi: AugmentCatalog) -> None:
    """Sau chuan hoa, ca hai ngon ngu deu co 5 nhom trung ten.

    Nhung EN cuu duoc 1 nhom nho tie-break phan biet hoa thuong, con VI thi
    khong - nen VI thuc su TE HON EN, dung 1 cap.
    """
    assert len(en.ambiguous_groups) == 5
    assert len(vi.ambiguous_groups) == 5


def test_case_tiebreak_rescues_tons_of_stats(en: AugmentCatalog) -> None:
    """Chu HOA la tin hieu duy nhat tach hai augment nay trong tieng Anh.

    Chinh vi vay quy tac "lowercase truoc khi so sanh" phai co ngoai le:
    lowercase de TIM ung vien, roi so lai co phan biet hoa thuong khi con >1.
    """
    r1 = en.match_name("Tons of Stats!")
    r2 = en.match_name("TONS of Stats!")
    assert not r1.ambiguous and r1.resolved is not None
    assert not r2.ambiguous and r2.resolved is not None
    assert r1.resolved.api_name == "DA_TonsOfStatsI"
    assert r2.resolved.api_name == "DA_TonsOfStatsII"
    assert r1.resolved.api_name != r2.resolved.api_name


def test_vietnamese_cannot_rescue_tons_of_stats(vi: AugmentCatalog) -> None:
    """Trong tieng Viet hai ten GIONG HET nhau -> khong tin hieu nao cuu duoc."""
    r = vi.match_name("Cộng Mệt Nghỉ!")
    assert r.ambiguous
    assert len(r.candidates) == 2
    assert r.resolved is None  # KHONG duoc doan bua


def test_truly_ambiguous_pairs_return_both_never_guess(en: AugmentCatalog) -> None:
    """4 cap thuc su khong phan biet duoc trong EN -> luon tra CA HAI."""
    truly_ambiguous = [
        ("Nesting Dolls", {"DA_NestingDollsPlus", "DA_NestingDollsPlusPlus"}),
        ("Consuming Flora", {"DA_18_FloraFatalisAugment", "DA_18_FloraFatalisAugmentPlus"}),
        ("Beast Within", {"DA_18_PrimalAugment_Sivir", "DA_18_PrimalAugment_Nidalee"}),
        ("Beast Within+", {"DA_18_PrimalAugmentPlus_Nidalee", "DA_18_PrimalAugmentPlus_Sivir"}),
    ]
    for name, expected_ids in truly_ambiguous:
        r = en.match_name(name)
        assert r.ambiguous, f"{name} phai duoc danh dau map mo"
        assert r.resolved is None, f"{name} khong duoc doan ra mot ket qua"
        assert {a.api_name for a in r.candidates} == expected_ids


def test_ambiguous_pairs_break_down_by_cause(en: AugmentCatalog, vi: AugmentCatalog) -> None:
    """Phan loai chinh xac 5 nhom map mo theo NGUYEN NHAN.

    Ban dau bao cao ghi "3 trong 4 cap chi khac nhau o tier". Test nay bac bo
    dieu do tren du lieu that. Sau khi sua tier 2026-10-06 (bien the `+`/`++`
    cung tier voi ban goc) KHONG cap mat nao con khac tier: "Nesting Dolls"
    + / ++ deu la 3, hai cap "Beast Within" khac nhau o TUONG gan voi augment
    (Sivir vs Nidalee), "Consuming Flora" cung tier. Nhom duy nhat khac tier
    la "Tons of Stats!" (2 va 3). Van la gioi han that, nhung khong ve tier.
    """
    by_tier = {
        k for k, g in en.ambiguous_groups.items() if len({a.tier for a in g}) > 1
    }
    assert by_tier == {"tons of stats!"}

    # "tons of stats!" duoc cuu bang tie-break hoa thuong -> khong tinh la mat.
    truly_lost_en = {
        k for k, g in en.ambiguous_groups.items()
        if en.match_name(g[0].name).ambiguous
    }
    assert len(truly_lost_en) == 4
    assert "tons of stats!" not in truly_lost_en

    # Trong 4 cap that su mat, khong cap nao khac tier.
    assert truly_lost_en & by_tier == set()

    # Tieng Viet mat ca 5 - cap mat THEM chinh la cap khac tier duy nhat.
    truly_lost_vi = {
        k for k, g in vi.ambiguous_groups.items()
        if vi.match_name(g[0].name).ambiguous
    }
    assert len(truly_lost_vi) == 5


# --- khop ten thong thuong -------------------------------------------------


def test_match_unknown_name_returns_empty(en: AugmentCatalog) -> None:
    r = en.match_name("Khong Ton Tai Dau")
    assert r.candidates == []
    assert not r.ambiguous


def test_match_is_diacritic_insensitive(vi: AugmentCatalog) -> None:
    """OCR mat dau van phai khop duoc - mien la normalize CA HAI PHIA."""
    target = next(a for a in vi.augments if "ố" in a.name or "ộ" in a.name)
    assert vi.match_name(normalize(target.name)).candidates
