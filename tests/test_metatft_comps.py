"""Test MetaTFT Comps client, parsing logic va CompDatabase.load_composite - chay hoan toan OFFLINE.

Khong test nao cham mang that. Dung mock requests.Session de kiem thu:
  - Goi API latest_cluster_info va comp_builds
  - Bat loi HTTP status != 200, loi ket noi, loi parse JSON
  - Parse cluster payload va builds payload thanh list[MetaComp] voi sample_n that
  - Kiem thu co che load_composite: enrich so lieu empirical cua MetaTFT vao
    doi hinh chien thuat co day du best_augments cua TFT Academy
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import requests

from src.knowledge.comp_database import CompDatabase, MetaComp
from src.knowledge.metatft_comps import (
    COMP_BUILDS_URL,
    LATEST_CLUSTER_INFO_URL,
    MetaTFTCompsClient,
    MetaTFTCompsError,
    build_meta_comps_payload,
    parse_metatft_comps,
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


SAMPLE_CLUSTER_PAYLOAD = {
    "cluster_info": {
        "cluster_details": {
            "clusters": [
                {
                    "Cluster": "422000",
                    "name_string": "Malphite Mage",
                    "units_string": "DA_18_Malphite, DA_18_Taric, DA_18_Lux, DA_18_Zoe",
                    "traits_string": "DA_18_Mage_2, DA_18_Bastion_2",
                },
                {
                    "Cluster": "422001",
                    "name_string": "Yorick Solo Carry",
                    "units_string": "DA_18_Yorick, DA_18_Nasus, DA_18_Renekton",
                    "traits_string": "DA_18_Bruiser_2",
                },
            ]
        }
    }
}

SAMPLE_BUILDS_PAYLOAD = {
    "results": {
        "422000": {
            "overall": {"count": 45000, "avg": 4.12},
            "builds": [
                {
                    "buildName": ["TFT_Item_RabadonsDeathcap", "TFT_Item_ArchangelsStaff"],
                    "count": 12000,
                    "avg": 3.95,
                }
            ],
        },
        "422001": {
            "overall": {"count": 15000, "avg": 4.55},
            "builds": [
                {
                    "buildName": ["TFT_Item_WarmogsArmor", "TFT_Item_GargoyleStoneplate"],
                    "count": 8000,
                    "avg": 4.50,
                }
            ],
        },
    }
}


# --- Client Tests ---


def test_client_get_cluster_info_and_builds_success() -> None:
    session = FakeSession(
        {
            LATEST_CLUSTER_INFO_URL: FakeResponse(200, SAMPLE_CLUSTER_PAYLOAD),
            COMP_BUILDS_URL: FakeResponse(200, SAMPLE_BUILDS_PAYLOAD),
        }
    )
    client = MetaTFTCompsClient(session=session)
    c_info = client.get_cluster_info()
    assert "cluster_info" in c_info

    builds = client.get_comp_builds()
    assert "results" in builds
    assert "422000" in builds["results"]


def test_client_http_error_raises() -> None:
    session = FakeSession(
        {
            LATEST_CLUSTER_INFO_URL: FakeResponse(502, text="Bad Gateway"),
        }
    )
    client = MetaTFTCompsClient(session=session)
    with pytest.raises(MetaTFTCompsError, match="status 502"):
        client.get_cluster_info()


def test_client_network_error_raises() -> None:
    class BrokenSession:
        def get(self, *args: Any, **kwargs: Any) -> Any:
            raise requests.ConnectionError("Connection timeout")

    client = MetaTFTCompsClient(session=BrokenSession())
    with pytest.raises(MetaTFTCompsError, match="Loi ket noi"):
        client.get_cluster_info()


# --- Parser Tests ---


def test_parse_invalid_payload_raises() -> None:
    with pytest.raises(MetaTFTCompsError, match="clusters"):
        parse_metatft_comps({}, {})


def test_parse_metatft_comps_success() -> None:
    comps = parse_metatft_comps(
        SAMPLE_CLUSTER_PAYLOAD,
        SAMPLE_BUILDS_PAYLOAD,
        patch="18.1d",
    )
    assert len(comps) == 2

    # Cluster 422000 (avg 4.12 -> Tier S)
    c1 = comps[0]
    assert c1.name == "MetaTFT: Malphite Mage"
    assert c1.tier == "S"
    assert c1.sample_n == 45000
    assert c1.avg_placement == 4.12
    assert c1.core_units == ["DA_18_Malphite", "DA_18_Taric", "DA_18_Lux", "DA_18_Zoe"]
    assert c1.traits == {"DA_18_Mage": 2, "DA_18_Bastion": 2}
    assert c1.core_items == ["TFT_Item_RabadonsDeathcap", "TFT_Item_ArchangelsStaff"]
    assert "metatft:META Spencer/cluster=422000" in c1.source

    # Cluster 422001 (avg 4.55 -> Tier B)
    c2 = comps[1]
    assert c2.name == "MetaTFT: Yorick Solo Carry"
    assert c2.tier == "B"
    assert c2.sample_n == 15000
    assert c2.avg_placement == 4.55
    assert c2.core_units == ["DA_18_Yorick", "DA_18_Nasus", "DA_18_Renekton"]
    assert c2.traits == {"DA_18_Bruiser": 2}


# --- Composite Database Loader Tests ---


def test_load_composite_enriches_and_appends(tmp_path: Path) -> None:
    # 1. Primary comp (TFT Academy): co best_augments nhung sample_n = 0
    p_comp = MetaComp(
        name="Malphite AP Flex",
        tier="S",
        core_units=["DA_18_Malphite", "DA_18_Taric", "DA_18_Lux"],
        flex_units=[],
        core_items=["TFT_Item_RabadonsDeathcap"],
        best_augments=["DA_Augment_AP_Boost"],
        traits={"DA_18_Mage": 2},
        avg_placement=3.95,
        top4_rate=0.60,
        win_rate=0.18,
        play_rate=0.03,
        level_timing={"8": 4},
        early_game=["DA_18_Malphite"],
        positioning_notes="Fast 8 roll",
        source="tftacademy:Dishsoap & Frodan",
        sample_n=0,
    )
    primary_payload = {
        "meta": {"provider": "tftacademy.com"},
        "comps": [p_comp.to_dict()],
    }
    primary_file = tmp_path / "primary.json"
    primary_file.write_text(json.dumps(primary_payload), encoding="utf-8")

    # 2. Backup comps (MetaTFT): 1 comp khop Malphite (co sample_n=45000, avg=4.12)
    #    va 1 comp moi (Yorick) khong co trong primary
    b_comps = parse_metatft_comps(
        SAMPLE_CLUSTER_PAYLOAD,
        SAMPLE_BUILDS_PAYLOAD,
    )
    backup_payload = build_meta_comps_payload(b_comps)
    backup_file = tmp_path / "backup.json"
    backup_file.write_text(json.dumps(backup_payload), encoding="utf-8")

    # 3. Load composite
    db = CompDatabase.load_composite(primary_file, backup_file)
    assert len(db) == 2

    # Malphite AP Flex da duoc enrich so lieu that tu MetaTFT ma van giu best_augments!
    c_malph = db.by_name("Malphite AP Flex")
    assert c_malph is not None
    assert c_malph.sample_n == 45000
    assert c_malph.avg_placement == 4.12
    assert c_malph.best_augments == ["DA_Augment_AP_Boost"]
    assert "tftacademy:" in c_malph.source
    assert "metatft:" in c_malph.source

    # Yorick Solo Carry khong trung duoc them vao lam comp moi
    c_yorick = db.by_name("MetaTFT: Yorick Solo Carry")
    assert c_yorick is not None
    assert c_yorick.sample_n == 15000


def test_load_composite_fallback_when_backup_missing(tmp_path: Path) -> None:
    p_comp = MetaComp(
        name="Solo Primary",
        tier="A",
        core_units=["DA_18_ChampA"],
        flex_units=[],
        core_items=[],
        best_augments=["DA_Aug_A"],
        traits={},
        avg_placement=4.25,
        top4_rate=0.55,
        win_rate=0.12,
        play_rate=0.02,
        level_timing={},
        early_game=[],
        positioning_notes="",
        source="tftacademy",
        sample_n=0,
    )
    p_file = tmp_path / "p.json"
    p_file.write_text(json.dumps({"meta": {}, "comps": [p_comp.to_dict()]}), encoding="utf-8")

    # Backup khong ton tai -> tra ve primary ma khong loi
    db = CompDatabase.load_composite(p_file, tmp_path / "nonexistent.json")
    assert len(db) == 1
    assert db.comps[0].name == "Solo Primary"
