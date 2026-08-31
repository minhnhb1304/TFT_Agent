"""Test CDragonClient - chay HOAN TOAN offline bang fixture.

Nguyen tac mock-first: khong test nao duoc cham mang. Neu CI khong co internet
thi test van phai xanh.

Test o day khong chi kiem tra duong hanh phuc. Quan trong hon la kiem tra
MOI CAI BAY DEU THUC SU NEM LOI - mot assert khong bao gio kich hoat thi vo dung.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from src.knowledge.cdragon_client import (
    EXPECTED_ROSTER_SIZE,
    EXPECTED_TIER_DISTRIBUTION,
    CDragonClient,
    CDragonError,
    select_set_data,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cdragon"


@pytest.fixture
def client(tmp_path: Path) -> CDragonClient:
    """Client offline, cache tro toi ban sao fixture."""
    cache = tmp_path / "cdragon_cache"
    cache.mkdir()
    for name in ("tftsets.json", "tftchampions-teamplanner.json", "tftsets.json.meta"):
        src = FIXTURES / name
        if src.exists():
            shutil.copy(src, cache / name)
    return CDragonClient(cache_dir=cache, offline=True)


# --- duong hanh phuc ------------------------------------------------------


def test_load_set_info_returns_set18(client: CDragonClient) -> None:
    info = client.load_set_info()
    assert info["SetName"] == "TFTSet18"
    assert info["SetDisplayName"] == "Enchanted Wilds"
    # Bay: ten he thong augment doi o Set 18. Code nao hardcode "Hexcore" se vo.
    assert info["SetAugmentName"] == "Boombox Augment"


def test_load_roster_size_and_tiers(client: CDragonClient) -> None:
    roster = client.load_roster()
    assert len(roster) == EXPECTED_ROSTER_SIZE

    dist: dict[int, int] = {}
    for c in roster:
        dist[c.tier] = dist.get(c.tier, 0) + 1
    assert dist == EXPECTED_TIER_DISTRIBUTION


def test_all_character_ids_start_with_da(client: CDragonClient) -> None:
    """Bay so 4: character_id khong con bat dau bang TFT18_."""
    roster = client.load_roster()
    assert all(c.character_id.startswith("DA") for c in roster)
    # Va khong phai tat ca deu theo mot khuon - co 3 dang khac nhau.
    assert not all(c.character_id.startswith("DA_18_") for c in roster)


def test_icon_url_read_verbatim_not_string_built(client: CDragonClient) -> None:
    """Bay so 5: doc squareIconPath nguyen van, khong ghep tu ten hien thi."""
    roster = client.load_roster()
    gromp = next(c for c in roster if c.display_name == "Gromp")
    url = gromp.icon_url
    assert url.startswith("https://raw.communitydragon.org/latest/")
    assert "/lol-game-data/assets" not in url
    assert url.endswith(".jpg") or url.endswith(".png")
    # Duong dan phai lowercase - casing trong JSON khong nhat quan.
    assert url == url.lower() or "TFT" not in url.split("/")[-1]


def test_trait_icon_tex_to_png() -> None:
    """36/36 trait resolve bang cach doi .tex -> .png, giu nguyen phan con lai."""
    url = CDragonClient.icon_url("assets/ux/traiticons/trait_icon_18_ravager.tex")
    assert url == (
        "https://raw.communitydragon.org/latest/game/"
        "assets/ux/traiticons/trait_icon_18_ravager.png"
    )


# --- cac cai bay PHAI nem loi ---------------------------------------------


def test_vn_vn_locale_is_rejected(client: CDragonClient) -> None:
    """Bay so 1: vn_vn dong bang tu 2023 nhung tra HTTP 200 tren /pbe/."""
    with pytest.raises(CDragonError, match="vn_vn"):
        client.load_locale("vn_vn")


def test_wrong_set_raises(tmp_path: Path) -> None:
    """Neu Riot doi set, PHAI dung lai - khong duoc chay tiep voi ROI cu."""
    cache = tmp_path / "c"
    cache.mkdir()
    data = json.loads((FIXTURES / "tftsets.json").read_text(encoding="utf-8"))
    data["LCTFTModeData"]["mDefaultSet"]["SetName"] = "TFTSet19"
    (cache / "tftsets.json").write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(CDragonError, match="TFTSet19"):
        CDragonClient(cache_dir=cache, offline=True).load_set_info()


def test_short_roster_raises(tmp_path: Path) -> None:
    """Roster thieu tuong -> nem loi, khong am tham chay tiep."""
    cache = tmp_path / "c"
    cache.mkdir()
    data = json.loads(
        (FIXTURES / "tftchampions-teamplanner.json").read_text(encoding="utf-8")
    )
    data["TFTSet18"] = data["TFTSet18"][:10]
    (cache / "tftchampions-teamplanner.json").write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(CDragonError, match="10 tuong"):
        CDragonClient(cache_dir=cache, offline=True).load_roster()


def test_offline_without_cache_raises(tmp_path: Path) -> None:
    """offline=True ma khong co cache -> bao loi ro rang, khong tra dict rong."""
    with pytest.raises(CDragonError, match="offline"):
        CDragonClient(cache_dir=tmp_path / "empty", offline=True).load_set_info()


def test_stale_locale_detection() -> None:
    """Bay so 1 (dang tong quat): header Last-Modified qua cu -> phai bat duoc."""
    old = CDragonClient._age_in_days("Wed, 03 May 2023 20:20:14 GMT")
    assert old is not None and old > 1000  # vn_vn that su dong bang o day

    fresh = CDragonClient._age_in_days("Thu, 27 Aug 2026 22:53:51 GMT")
    assert fresh is not None and fresh < 400

    # Header rac thi tra None chu khong crash.
    assert CDragonClient._age_in_days("khong-phai-ngay") is None


# --- Bay so 6: setData[0] KHONG phai set dang target ----------------------


def test_set_data_is_selected_by_mutator_not_position() -> None:
    """Ban locale DAY DU co 35 khoi setData va khoi dau tien la TFTSet14.

    Do duoc 2026-09-01 tren en_us.json that. Bay nay khong lo ra o fixture
    trimmed vi fixture chi giu dung mot khoi - nghia la mot bug o day se
    xanh het test cho den ngay chay tren du lieu that.

    Lay nham khoi thi hong IM LANG: bang anh xa trait tro thanh cua Set 14,
    trait_affinity rong sach, va BoardFit thanh trung tinh cho moi augment.
    """
    locale = {
        "setData": [
            {"mutator": "TFTSet14", "name": "Set14", "traits": [{"apiName": "X"}]},
            {"mutator": "TFTSet18", "name": "Set10", "traits": [{"apiName": "DA_18_Ravager"}]},
            {"mutator": "TFTSet17", "name": "Set17", "traits": []},
        ]
    }
    block = select_set_data(locale)
    assert block["mutator"] == "TFTSet18"
    assert block["traits"][0]["apiName"] == "DA_18_Ravager"


def test_set_data_never_keys_on_display_name() -> None:
    """Khoi cua Set 18 co `name` la "Set10" - loc theo name cung sai im lang.

    Set 18 dung lai ten asset cua Set 10 (bay so 4, research/set-data.md).
    """
    locale = {
        "setData": [
            {"mutator": "TFTSet10", "name": "Set10", "traits": [{"apiName": "SAI"}]},
            {"mutator": "TFTSet18", "name": "Set10", "traits": [{"apiName": "DUNG"}]},
        ]
    }
    assert select_set_data(locale)["traits"][0]["apiName"] == "DUNG"


def test_missing_target_set_raises_and_lists_what_was_there() -> None:
    """Khong tim thay thi phai nem kem danh sach mutator co san de con debug."""
    locale = {"setData": [{"mutator": "TFTSet14"}, {"mutator": "TFTSet17"}]}
    with pytest.raises(CDragonError, match="TFTSet14"):
        select_set_data(locale)


def test_trimmed_fixture_still_resolves(client: CDragonClient) -> None:
    """Fixture chi co mot khoi - duong nay van phai chay dung."""
    locale = json.loads((FIXTURES / "en_us.trimmed.json").read_text(encoding="utf-8"))
    assert len(select_set_data(locale)["traits"]) == 36
