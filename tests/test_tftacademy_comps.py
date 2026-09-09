"""Test TFT Academy Comps client va parsing logic - chay hoan toan OFFLINE.

Khong test nao cham mang that. Dung mock requests.Session de kiem thu:
  - Goi API lay danh sach doi hinh meta
  - Bat loi HTTP status != 200, loi ket noi, loi parse JSON
  - Parse guides payload thanh list[MetaComp] voi core_units, core_items, best_augments
  - Tinh toan active traits tu traits_map
  - Dong goi payload JSON va load vao CompDatabase
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import requests

from src.knowledge.comp_database import CompDatabase, MetaComp
from src.knowledge.tftacademy_comps import (
    COMPS_API_URL,
    TFTAcademyCompsClient,
    TFTAcademyCompsError,
    build_meta_comps_payload,
    parse_tftacademy_comps,
)


class FakeResponse:
    def __init__(self, status: int, payload: Any = None, text: str = "") -> None:
        self.status_code = status
        self._payload = payload
        self.text = text

    def json(self) -> Any:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeSession:
    def __init__(self, responses: dict[str, FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def get(self, url: str, headers: Any = None, timeout: float = 10.0) -> FakeResponse:
        self.calls.append(url)
        for prefix, resp in self.responses.items():
            if url.startswith(prefix):
                return resp
        return FakeResponse(404, text="Not Found")


SAMPLE_GUIDES_PAYLOAD = {
    "guides": [
        {
            "title": "Malphite AP Flex",
            "tier": "S",
            "style": "Fast 8",
            "difficulty": "Easy",
            "augmentsTip": "Uu tien loi tang AP va kinh te",
            "finalComp": [
                {
                    "apiName": "DA_18_Malphite",
                    "items": ["TFT_Item_RabadonsDeathcap", "TFT_Item_ArchangelsStaff"],
                },
                {
                    "apiName": "DA_18_Taric",
                    "items": ["TFT_Item_WarmogsArmor", "TFT_Item_DragonsClaw"],
                },
                {"apiName": "DA_18_Lux", "items": []},
            ],
            "maxCap": [{"apiName": "DA_18_Sett"}],
            "altBuilds": [{"apiName": "DA_18_Sylas"}],
            "augments": [
                {"apiName": "DA_Augment_AP_Boost", "disabled": False},
                {"apiName": "DA_Augment_Def_Disabled", "disabled": True},
                "DA_Augment_String_Format",
            ],
            "earlyComp": [
                {"apiName": "DA_18_Malphite"},
                {"apiName": "DA_18_Shen"},
            ],
            "tips": [
                {"stage": "2-1", "tip": "Giữ chuỗi thắng nếu có đồ sớm"},
                {"stage": "4-2", "tip": "Lên cấp 8 roll kiếm Malphite 2 sao"},
            ],
        },
        {
            "title": "Rengar Reroll",
            "tier": "A",
            "style": "Reroll",
            "difficulty": "Medium",
            "finalComp": [
                {
                    "apiName": "DA_18_Rengar",
                    "items": ["TFT_Item_InfinityEdge", "TFT_Item_Bloodthirster"],
                },
                {"apiName": "DA_18_KhaZix", "items": []},
            ],
            "augments": [
                {"apiName": "DA_Augment_AD_Reroll", "disabled": False},
            ],
        },
    ]
}

SAMPLE_TRAITS_MAP = {
    "DA_18_Malphite": ["DA_18_Mage", "DA_18_Bastion"],
    "DA_18_Taric": ["DA_18_Bastion", "DA_18_Targon"],
    "DA_18_Lux": ["DA_18_Mage"],
    "DA_18_Rengar": ["DA_18_Assassin"],
    "DA_18_KhaZix": ["DA_18_Assassin"],
}


# --- Client Tests ---


def test_client_get_comps_success() -> None:
    session = FakeSession({COMPS_API_URL: FakeResponse(200, SAMPLE_GUIDES_PAYLOAD)})
    client = TFTAcademyCompsClient(session=session)
    data = client.get_comps(18)
    assert "guides" in data
    assert len(data["guides"]) == 2
    assert session.calls[0] == f"{COMPS_API_URL}?set=18"


def test_client_http_error_raises() -> None:
    session = FakeSession({COMPS_API_URL: FakeResponse(500, text="Internal Server Error")})
    client = TFTAcademyCompsClient(session=session)
    with pytest.raises(TFTAcademyCompsError, match="status 500"):
        client.get_comps(18)


def test_client_invalid_json_raises() -> None:
    session = FakeSession(
        {COMPS_API_URL: FakeResponse(200, payload=ValueError("Expecting value"))}
    )
    client = TFTAcademyCompsClient(session=session)
    with pytest.raises(TFTAcademyCompsError, match="khong phai JSON"):
        client.get_comps(18)


def test_client_network_error_raises() -> None:
    class BrokenSession:
        def get(self, *args: Any, **kwargs: Any) -> Any:
            raise requests.ConnectionError("Connection refused")

    client = TFTAcademyCompsClient(session=BrokenSession())
    with pytest.raises(TFTAcademyCompsError, match="Loi ket noi"):
        client.get_comps(18)


# --- Parser Tests ---


def test_parse_invalid_payload_raises() -> None:
    with pytest.raises(TFTAcademyCompsError, match="guides"):
        parse_tftacademy_comps({})

    with pytest.raises(TFTAcademyCompsError, match="guides"):
        parse_tftacademy_comps({"guides": "not-a-list"})


def test_parse_guides_success() -> None:
    comps = parse_tftacademy_comps(
        SAMPLE_GUIDES_PAYLOAD,
        patch="18.1d",
        traits_map=SAMPLE_TRAITS_MAP,
    )
    assert len(comps) == 2

    # Comp 1: Malphite AP Flex
    c1 = comps[0]
    assert c1.name == "Malphite AP Flex"
    assert c1.tier == "S"
    assert c1.core_units == ["DA_18_Malphite", "DA_18_Taric", "DA_18_Lux"]
    assert c1.core_items == [
        "TFT_Item_RabadonsDeathcap",
        "TFT_Item_ArchangelsStaff",
        "TFT_Item_WarmogsArmor",
        "TFT_Item_DragonsClaw",
    ]
    # Disabled augment is filtered out, string augment preserved
    assert c1.best_augments == ["DA_Augment_AP_Boost", "DA_Augment_String_Format"]
    assert c1.flex_units == ["DA_18_Sett", "DA_18_Sylas"]
    assert c1.early_game == ["DA_18_Malphite", "DA_18_Shen"]
    assert c1.traits == {"DA_18_Mage": 2, "DA_18_Bastion": 2, "DA_18_Targon": 1}
    assert c1.sample_n == 0
    assert "tftacademy:Dishsoap & Frodan" in c1.source
    assert c1.level_timing == {"8": 4}  # Fast 8 style
    assert "Phong cách: Fast 8" in c1.positioning_notes
    assert "Lên cấp 8 roll kiếm Malphite" in c1.positioning_notes

    # Comp 2: Rengar Reroll
    c2 = comps[1]
    assert c2.name == "Rengar Reroll"
    assert c2.tier == "A"
    assert c2.core_units == ["DA_18_Rengar", "DA_18_KhaZix"]
    assert c2.best_augments == ["DA_Augment_AD_Reroll"]
    assert c2.traits == {"DA_18_Assassin": 2}
    assert c2.level_timing == {"6": 3, "7": 4}  # Reroll style


def test_build_payload_and_db_roundtrip(tmp_path: Path) -> None:
    comps = parse_tftacademy_comps(
        SAMPLE_GUIDES_PAYLOAD,
        patch="18.1d",
        traits_map=SAMPLE_TRAITS_MAP,
    )
    payload = build_meta_comps_payload(comps, {"patch": "18.1d"})
    assert payload["meta"]["total_comps"] == 2
    assert payload["meta"]["provider"] == "tftacademy.com"

    target = tmp_path / "test_comps.json"
    target.write_text(json.dumps(payload), encoding="utf-8")

    db = CompDatabase.load(target)
    assert len(db) == 2
    c = db.by_name("Malphite AP Flex")
    assert c is not None
    assert c.tier == "S"
    assert "DA_Augment_AP_Boost" in c.best_augments
