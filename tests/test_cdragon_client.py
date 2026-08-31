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
