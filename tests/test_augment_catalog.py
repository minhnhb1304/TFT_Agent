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
    AugmentCatalog,
    diacritic_collisions,
    normalize,
    resolve_tier,
    strip_tier_token,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cdragon"


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
    """Ladder phai giai het 254/254 voi dung phan bo da do 2026-08-28."""
    counts = en.tier_source_counts()
    assert counts == {
        "apiName/name token": 75,
        "missing-tN": 28,
        "icon roman": 135,
        "icon digit": 16,
    }
    assert sum(counts.values()) == 254
    assert "UNRESOLVED" not in counts


def test_every_augment_has_valid_tier(en: AugmentCatalog) -> None:
    assert all(1 <= a.tier <= 3 for a in en.augments)


def test_name_beats_icon_on_conflict(en: AugmentCatalog) -> None:
    """Quy tac quan trong nhat: TEN LA CHINH, icon chi la phu.

    19/254 augment co duong dan icon mau thuan voi tier that. Neu dao thu tu
    ladder (dat icon truoc), dung 19 cai nay bi gan sai tier.
    """
    conflicts = en.icon_tier_conflicts()
    assert len(conflicts) == 19

    # Vi du cu the: ten noi tier 2, icon noi tier 3 -> phai theo TEN.
    bronze = en.get("DA_BronzeForLifeII")
    assert bronze is not None
    assert bronze.name == "Bronze For Life II"
    assert "bronzeforlife_iii" in bronze.icon.lower()  # icon noi tier 3
    assert bronze.tier == 2  # ... nhung ta theo ten
    assert bronze.tier_source == "apiName/name token"


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
    dieu do tren du lieu that: chi 1 cap khac tier. Hai cap "Beast Within"
    khac nhau o TUONG gan voi augment (Sivir vs Nidalee), con "Consuming Flora"
    thi cung tier. Van la gioi han that, nhung khong phai gioi han ve tier.
    """
    by_tier = {
        k for k, g in en.ambiguous_groups.items() if len({a.tier for a in g}) > 1
    }
    assert by_tier == {"nesting dolls", "tons of stats!"}

    # "tons of stats!" duoc cuu bang tie-break hoa thuong -> khong tinh la mat.
    truly_lost_en = {
        k for k, g in en.ambiguous_groups.items()
        if en.match_name(g[0].name).ambiguous
    }
    assert len(truly_lost_en) == 4
    assert "tons of stats!" not in truly_lost_en

    # Trong 4 cap that su mat, chi 1 cap khac tier.
    assert len(truly_lost_en & by_tier) == 1

    # Tieng Viet mat ca 5 - va mat THEM mot cap khac tier.
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
