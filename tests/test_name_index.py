"""Test bang anh xa ten -> apiName (feedback #6/#7).

Bat bien quan trong nhat o day khong phai "tra dung ket qua" ma la
`resolve()` TRA VE DANH SACH. Tieng Viet co 5 nhom augment trung ten, tieng
Anh co 4 sau tie-break hoa thuong. Neu mot ngay nao do ai do "don dep" API
nay thanh tra ve mot gia tri, do la luc he thong bat dau DOAN BUA ma khong
ai biet - va SPEC 3.5.4 cam dieu do.

Cac con so trong file nay do duoc tren locale day du 2026-09-01 va trung
khop voi research/vision-stack/augments.md.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import pytest

from src.knowledge.name_index import LANGUAGES, NAMESPACES, NameIndex

COMMITTED = Path("data/name_index.json")

needs_index = pytest.mark.skipif(
    not COMMITTED.exists(), reason="chua chay scripts/build_name_index.py"
)


@pytest.fixture
def index() -> NameIndex:
    return NameIndex.load(COMMITTED)


# --- Trang thai rong la HOP LE ---------------------------------------------


def test_missing_file_is_not_an_error() -> None:
    """Track A chay duoc khi chua co index - tang vision moi la ben can no."""
    ix = NameIndex.load("data/khong_ton_tai.json")
    assert ix.is_empty
    assert ix.resolve("bat ky") == []
    assert ix.resolve_stem("bat ky") == []
    assert ix.display_name("DA_X") == ""


def test_empty_index_returns_empty_list_not_none() -> None:
    """[] va None la hai y nghia khac nhau - goi ben phai lap duoc ket qua."""
    assert NameIndex.empty().resolve("x") == []


# --- Cau truc file da commit ----------------------------------------------


@needs_index
def test_covers_all_three_namespaces(index: NameIndex) -> None:
    for ns in NAMESPACES:
        for lang in LANGUAGES:
            assert index.by_norm[ns][lang], f"{ns}/{lang} rong"


@needs_index
def test_counts_match_the_measured_set18_numbers(index: NameIndex) -> None:
    """254 augment / 36 trait / 65 champion - xem research/set-data.md."""
    counts = index.meta["counts"]
    assert counts["augments"] == {"vi": 254, "en": 254}
    assert counts["traits"] == {"vi": 36, "en": 36}
    assert counts["champions"] == {"vi": 65, "en": 65}


@needs_index
def test_every_value_is_a_list(index: NameIndex) -> None:
    """Hop dong kieu du lieu: mot ten LUON tro toi mot danh sach apiName."""
    raw = json.loads(COMMITTED.read_text(encoding="utf-8"))
    for ns in NAMESPACES:
        for lang in LANGUAGES:
            for key, value in raw["by_norm"][ns][lang].items():
                assert isinstance(value, list), f"{ns}/{lang}/{key}"
                assert value


# --- Map mo: gioi han du lieu, phai lo ra chu khong duoc giau -------------


@needs_index
def test_vietnamese_loses_one_more_pair_than_english(index: NameIndex) -> None:
    """VI te hon EN dung mot cap - do duoc, khong phai uoc luong.

    Ca hai deu co 5 nhom trung sau khi normalize; EN cuu duoc mot nhom bang
    tie-break phan biet hoa thuong ("Tons of Stats!" vs "TONS of Stats!"),
    tieng Viet dich ca hai thanh cung mot chuoi nen khong cuu duoc.
    """
    assert len(index.ambiguous_groups("augments", "vi")) == 5
    assert len(index.ambiguous_groups("augments", "en")) == 5


@needs_index
def test_traits_and_champions_have_no_collisions(index: NameIndex) -> None:
    """Chi augment moi bi trung ten. Trait/champion tra ve duy nhat duoc."""
    for ns in ("traits", "champions"):
        for lang in LANGUAGES:
            assert index.ambiguous_groups(ns, lang) == {}


@needs_index
def test_ambiguous_pair_resolves_to_both_never_one(index: NameIndex) -> None:
    """Cap khong tach duoc phai tra CA HAI. Day la bat bien cua ca file nay."""
    vi_name = index.display_name("DA_18_PrimalAugment_Sivir", "augments", "vi")
    hits = index.resolve(vi_name, "augments", "vi")
    assert set(hits) == {
        "DA_18_PrimalAugment_Sivir",
        "DA_18_PrimalAugment_Nidalee",
    }


@needs_index
def test_case_sensitive_tiebreak_rescues_tons_of_stats_in_english(
    index: NameIndex,
) -> None:
    """Chu hoa la tin hieu DUY NHAT tach duoc cap nay - lowercase se xoa mat no."""
    assert index.resolve("Tons of Stats!", "augments", "en") == ["DA_TonsOfStatsI"]
    assert index.resolve("TONS of Stats!", "augments", "en") == ["DA_TonsOfStatsII"]


@needs_index
def test_vietnamese_cannot_rescue_the_same_pair(index: NameIndex) -> None:
    """Ban dich tieng Viet giong het nhau -> tra ca hai, khong doan."""
    vi_name = index.display_name("DA_TonsOfStatsI", "augments", "vi")
    assert index.display_name("DA_TonsOfStatsII", "augments", "vi") == vi_name
    assert len(index.resolve(vi_name, "augments", "vi")) == 2


# --- Tra cuu thong thuong --------------------------------------------------


@needs_index
def test_diacritics_are_stripped_on_both_sides(index: NameIndex) -> None:
    """OCR mat dau van phai khop - da do: 0 collision khi bo het dau.

    Mo phong truong hop xau nhat cua OCR: mat TOAN BO dau (NFD + bo Mn, cong
    them d gach ngang -> d). Ket qua van phai ve dung mot apiName.
    """
    n_checked = 0
    for api in ("DA_FocusedFire", "DA_18_BigGrabBag", "DA_GoldenGamble"):
        vi_name = index.display_name(api, "augments", "vi")
        if not vi_name:
            continue
        assert index.resolve(vi_name, "augments", "vi") == [api]

        stripped = "".join(
            c
            for c in unicodedata.normalize("NFD", vi_name)
            if unicodedata.category(c) != "Mn"
        ).translate({ord("đ"): "d", ord("Đ"): "D"})
        assert index.resolve(stripped, "augments", "vi") == [api], vi_name
        n_checked += 1

    assert n_checked, "khong augment nao duoc kiem tra - ten VI bi rong?"


@needs_index
def test_unknown_text_returns_empty_not_a_guess(index: NameIndex) -> None:
    assert index.resolve("chuoi khong ton tai o dau ca", "augments", "vi") == []


@needs_index
def test_stem_match_returns_the_whole_tier_family(index: NameIndex) -> None:
    """OCR nuot hau to tier -> tra ca cum, de goi ben biet la CHUA doc duoc tier.

    Do la thong tin dung. Tra ve mot phan tu o day moi la sai: no giau di
    viec tier chua duoc xac dinh.
    """
    hits = index.resolve_stem("Golden Gamble", "augments", "en")
    assert set(hits) >= {
        "DA_GoldenGamble",
        "DA_GoldenGamblePlus",
        "DA_GoldenGamblePlusPlus",
    }


@needs_index
def test_four_namespace_join_holds(index: NameIndex) -> None:
    """trait_id -> EN -> VI, khong co quy tac chuoi nao noi chung.

    `DA_18_Slayer` hien la "Ravager" (EN) va "Tan Pha" (VI) - khong suy ra
    duoc cai nay tu cai kia. Xem research/set-data.md.
    """
    assert index.display_name("DA_18_Slayer", "traits", "en") == "Ravager"
    assert index.display_name("DA_18_Slayer", "traits", "vi")
    assert index.resolve("Ravager", "traits", "en") == ["DA_18_Slayer"]


@needs_index
def test_champion_ids_join_with_the_roster_namespace(index: NameIndex) -> None:
    """apiName champion trong locale trung khop character_id cua teamplanner.

    65/65 - neu Riot tach hai khong gian ten nay thi comp matching hong ngay.
    """
    champions = index.display["champions"]
    assert len(champions) == 65
    assert all(api.startswith("DA") for api in champions)
