"""Test MetaTFT client va parsing logic - chay hoan toan OFFLINE.

Khong test nao cham mang that. Dung mock requests.Session de kiem thu:
  - Phan tich payload tier list thanh cac bac S/A/B/C/D
  - Bat loi khi payload sai hoac thieu tierList
  - Xuat format raw text va format payload JSON tuong thich ExpertTierListProvider
  - Thu tu uu tien CompositeProvider: CSV -> TFT Academy -> MetaTFT -> Null
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.knowledge.metatft import (
    MetaTFTClient,
    MetaTFTError,
    build_tierlist_payload,
    format_raw_text,
    parse_tierlist_augments,
)
from src.knowledge.stats_provider import (
    AugmentStats,
    ExpertTierListProvider,
    NullProvider,
    default_provider,
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


SAMPLE_METATFT_PAYLOAD = {
    "tft_set": "TFTSet18",
    "content": {
        "author": {
            "platform": "NA1",
            "gameName": "META Spencer",
            "tagLine": "TFT",
        },
        "content": {
            "tierList": [
                {
                    "label": "S",
                    "content": [
                        {"id": "DA_Meta_S1", "type": "augment"},
                        {"id": "DA_Meta_S2", "type": "augment"},
                    ],
                },
                {
                    "label": "A",
                    "content": [
                        {"id": "DA_Meta_A1", "type": "augment"},
                    ],
                },
                {
                    "label": "B",
                    "content": [
                        {"id": "DA_Meta_B1", "type": "augment"},
                    ],
                },
                {
                    "label": "C",
                    "content": [],
                },
            ],
            "tierListType": "scaling",
        },
        "updated_at": "2026-09-08T14:43:24.477Z",
    },
}


def test_parse_tierlist_augments_standard_payload() -> None:
    tiers = parse_tierlist_augments(SAMPLE_METATFT_PAYLOAD)
    assert "S" in tiers
    assert "A" in tiers
    assert "B" in tiers
    assert "C" not in tiers  # Rong thi khong giu
    assert "D" not in tiers

    assert tiers["S"] == ["DA_Meta_S1", "DA_Meta_S2"]
    assert tiers["A"] == ["DA_Meta_A1"]
    assert tiers["B"] == ["DA_Meta_B1"]


def test_parse_tierlist_augments_direct_tierlist() -> None:
    direct_payload = {
        "tierList": [
            {"label": "S", "content": [{"id": "DA_Direct_S"}]},
            {"label": "D", "content": ["DA_Direct_D"]},
        ]
    }
    tiers = parse_tierlist_augments(direct_payload)
    assert tiers["S"] == ["DA_Direct_S"]
    assert tiers["D"] == ["DA_Direct_D"]


def test_parse_tierlist_rejects_empty_or_malformed() -> None:
    with pytest.raises(MetaTFTError):
        parse_tierlist_augments({})

    with pytest.raises(MetaTFTError):
        parse_tierlist_augments({"content": {}})

    with pytest.raises(MetaTFTError):
        parse_tierlist_augments({"tierList": "not-a-list"})


def test_format_raw_text() -> None:
    tiers = {"S": ["DA_S1", "DA_S2"], "B": ["DA_B1"]}
    meta = {"patch": "18.1d", "rated_by": "MetaTFT (META Spencer)"}
    text = format_raw_text(tiers, meta)
    assert "# patch: 18.1d" in text
    assert "# rated_by: MetaTFT (META Spencer)" in text
    assert "S: DA_S1, DA_S2" in text
    assert "B: DA_B1" in text

    # Kiem tra tuong thich parse_tier_file
    from scripts.import_augment_tiers import parse_tier_file

    parsed = parse_tier_file(text)
    assert parsed == {"S": ["DA_S1", "DA_S2"], "B": ["DA_B1"]}


def test_build_tierlist_payload_and_provider_load(tmp_path: Path) -> None:
    tiers = {"S": ["DA_18_MetaTop"], "A": ["DA_18_MetaMid"]}
    meta = {
        "rated_by": "MetaTFT (META Spencer)",
        "patch": "18.1d",
    }
    payload = build_tierlist_payload(tiers, meta)
    assert payload["meta"]["rated_by"] == "MetaTFT (META Spencer)"
    assert payload["meta"]["patch"] == "18.1d"
    assert payload["meta"]["total_augments"] == 2
    assert payload["meta"]["is_backup"] is True
    assert payload["tiers"] == tiers

    out_file = tmp_path / "tiers_metatft.json"
    out_file.write_text(json.dumps(payload), encoding="utf-8")

    provider = ExpertTierListProvider.load(out_file)
    assert len(provider) == 2
    top = provider.get("DA_18_MetaTop")
    assert top is not None
    assert top.tier == "S"
    assert top.is_ordinal is True
    assert top.sample_n == 0
    assert "MetaTFT (META Spencer)" in top.source
    assert "18.1d" in top.source


def test_client_get_augments_tierlist_success() -> None:
    session = FakeSession({
        "https://api-hc.metatft.com/tft-stat-api/augments_tiers": FakeResponse(
            200, SAMPLE_METATFT_PAYLOAD
        )
    })
    client = MetaTFTClient(session=session)
    res = client.get_augments_tierlist(18)
    assert res == SAMPLE_METATFT_PAYLOAD
    assert any("tft_set=TFTSet18" in call for call in session.calls)


def test_client_get_augments_tierlist_http_error() -> None:
    session = FakeSession({
        "https://api-hc.metatft.com/tft-stat-api/augments_tiers": FakeResponse(
            500, text="Server Error"
        )
    })
    client = MetaTFTClient(session=session)
    with pytest.raises(MetaTFTError) as exc:
        client.get_augments_tierlist(18)
    assert "500" in str(exc.value)


def test_client_get_patch_info() -> None:
    games_payload = {
        "games": [
            {"day": 0, "patch": ["18.1", "d"], "count": 1000},
        ]
    }
    session = FakeSession({
        "https://api-hc.metatft.com/tft-stat-api/games": FakeResponse(200, games_payload)
    })
    client = MetaTFTClient(session=session)
    info = client.get_patch_info()
    assert info.get("patch") == "18.1d"


def test_composite_priority_csv_over_tftacademy_over_metatft(tmp_path: Path) -> None:
    # 1. Tao CSV co 1 augment do duoc
    csv_file = tmp_path / "stats.csv"
    csv_file.write_text(
        "api_name,avg_place,sample_n,source\n"
        "DA_Measured,4.10,500,riot_match_v1\n",
        encoding="utf-8",
    )

    # 2. Tao TFT Academy (nguon chuyen gia chinh)
    tftacad_file = tmp_path / "tftacademy.json"
    tftacad_payload = {
        "meta": {"rated_by": "TFT Academy (Dishsoap)", "patch": "18.1d"},
        "tiers": {
            "S": ["DA_Measured", "DA_InBoth"],  # DA_Measured trung voi CSV, DA_InBoth trung voi MetaTFT
            "A": ["DA_AcademyOnly"],
        },
    }
    tftacad_file.write_text(json.dumps(tftacad_payload), encoding="utf-8")

    # 3. Tao MetaTFT (nguon du phong)
    metatft_file = tmp_path / "metatft.json"
    metatft_payload = {
        "meta": {"rated_by": "MetaTFT (META Spencer)", "patch": "18.1d"},
        "tiers": {
            "B": ["DA_InBoth"],         # TFT Academy xep S, MetaTFT xep B -> TFT Academy phai thang
            "S": ["DA_MetaTFTBackup"],   # Chi co o MetaTFT -> MetaTFT phai thang lam backup
        },
    }
    metatft_file.write_text(json.dumps(metatft_payload), encoding="utf-8")

    provider = default_provider(
        csv_path=csv_file,
        tiers_path=tftacad_file,
        backup_tiers_path=metatft_file,
    )

    # Bat bien 1: So do CSV thang ca 2 bang tier
    res_measured = provider.get("DA_Measured")
    assert res_measured is not None
    assert res_measured.source == "riot_match_v1"
    assert res_measured.is_ordinal is False
    assert res_measured.sample_n == 500

    # Bat bien 2: Khi ca TFT Academy va MetaTFT deu co -> TFT Academy thang (khong bi trung binh hoa)
    res_in_both = provider.get("DA_InBoth")
    assert res_in_both is not None
    assert res_in_both.tier == "S"  # TFT Academy rated S, MetaTFT rated B
    assert "TFT Academy" in res_in_both.source
    assert res_in_both.is_ordinal is True

    # Bat bien 3: Khi TFT Academy thieu -> MetaTFT dong vai tro backup
    res_backup = provider.get("DA_MetaTFTBackup")
    assert res_backup is not None
    assert res_backup.tier == "S"
    assert "MetaTFT" in res_backup.source
    assert res_backup.is_ordinal is True

    # Bat bien 4: Khong nguon nao co -> tra None (NullProvider)
    assert provider.get("DA_CompletelyUnknown") is None
