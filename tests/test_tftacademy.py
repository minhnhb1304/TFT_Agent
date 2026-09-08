"""Test TFT Academy client va parsing logic - chay hoan toan OFFLINE.

Khong test nao cham mang that. Dung mock requests.Session de kiem thu:
  - Phan tich payload tier list thanh cac bac S/A/B/C/D
  - Loc theo stage ("All", "2-1", "3-2", "4-2")
  - Bat loi khi payload sai hoac thieu stage
  - Xuat format raw text va format payload JSON tuong thich ExpertTierListProvider
"""

from __future__ import annotations

from typing import Any

import pytest

from src.knowledge.stats_provider import ExpertTierListProvider
from src.knowledge.tftacademy import (
    TFTAcademyClient,
    TFTAcademyError,
    build_tierlist_payload,
    format_raw_text,
    parse_tierlist_augments,
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


SAMPLE_API_PAYLOAD = {
    "augments_tierlists": [
        {
            "augmenttier": 1,
            "stage": "All",
            "tier": {
                "S": ["DA_Silver_S1", "DA_Silver_S2"],
                "A": ["DA_Silver_A1"],
                "B": ["DA_Silver_B1"],
                "C": [],
            },
        },
        {
            "augmenttier": 2,
            "stage": "All",
            "tier": {
                "S": ["DA_Gold_S1"],
                "A": ["DA_Gold_A1", "DA_Gold_A2"],
                "B": [],
                "C": ["DA_Gold_C1"],
            },
        },
        {
            "augmenttier": 1,
            "stage": "2-1",
            "tier": {
                "S": ["DA_Early_S1"],
                "A": ["DA_Early_A1"],
                "B": [],
                "C": [],
            },
        },
    ]
}


def test_parse_tierlist_augments_all_stages() -> None:
    tiers = parse_tierlist_augments(SAMPLE_API_PAYLOAD, stage="All")
    assert "S" in tiers
    assert "A" in tiers
    assert "B" in tiers
    assert "C" in tiers
    assert "D" not in tiers  # Rong thi loai bo

    assert tiers["S"] == ["DA_Silver_S1", "DA_Silver_S2", "DA_Gold_S1"]
    assert tiers["A"] == ["DA_Silver_A1", "DA_Gold_A1", "DA_Gold_A2"]
    assert tiers["B"] == ["DA_Silver_B1"]
    assert tiers["C"] == ["DA_Gold_C1"]


def test_parse_tierlist_augments_specific_stage() -> None:
    tiers = parse_tierlist_augments(SAMPLE_API_PAYLOAD, stage="2-1")
    assert tiers["S"] == ["DA_Early_S1"]
    assert tiers["A"] == ["DA_Early_A1"]
    assert "B" not in tiers
    assert "C" not in tiers


def test_parse_tierlist_rejects_missing_stage() -> None:
    with pytest.raises(TFTAcademyError) as exc:
        parse_tierlist_augments(SAMPLE_API_PAYLOAD, stage="9-9")
    assert "Khong tim thay stage '9-9'" in str(exc.value)


def test_parse_tierlist_rejects_empty_payload() -> None:
    with pytest.raises(TFTAcademyError):
        parse_tierlist_augments({})


def test_format_raw_text() -> None:
    tiers = {"S": ["DA_S1", "DA_S2"], "A": ["DA_A1"]}
    meta = {"patch": "18.1d", "rated_by": "Dishsoap"}
    text = format_raw_text(tiers, meta)
    assert "# patch: 18.1d" in text
    assert "# rated_by: Dishsoap" in text
    assert "S: DA_S1, DA_S2" in text
    assert "A: DA_A1" in text

    # Kiem tra text nay tuong thich parse_tier_file
    from scripts.import_augment_tiers import parse_tier_file

    parsed = parse_tier_file(text)
    assert parsed == {"S": ["DA_S1", "DA_S2"], "A": ["DA_A1"]}


def test_build_tierlist_payload_and_provider_load(tmp_path) -> None:
    tiers = {"S": ["DA_18_Top"], "A": ["DA_18_Mid"], "B": ["DA_18_Low"]}
    meta = {
        "rated_by": "Test Rater",
        "patch": "18.1d",
        "stage": "All",
    }
    payload = build_tierlist_payload(tiers, meta)
    assert payload["meta"]["rated_by"] == "Test Rater"
    assert payload["meta"]["patch"] == "18.1d"
    assert payload["meta"]["total_augments"] == 3
    assert payload["tiers"] == tiers

    import json

    out_file = tmp_path / "tiers.json"
    out_file.write_text(json.dumps(payload), encoding="utf-8")

    provider = ExpertTierListProvider.load(out_file)
    assert len(provider) == 3
    top = provider.get("DA_18_Top")
    assert top is not None
    assert top.tier == "S"
    assert top.is_ordinal is True
    assert top.sample_n == 0
    assert "Test Rater" in top.source
    assert "18.1d" in top.source


def test_client_get_augments_tierlist_success() -> None:
    session = FakeSession({"https://tftacademy.com/api/tierlist/augments": FakeResponse(200, SAMPLE_API_PAYLOAD)})
    client = TFTAcademyClient(session=session)
    res = client.get_augments_tierlist(18)
    assert res == SAMPLE_API_PAYLOAD
    assert any("set=18" in call for call in session.calls)


def test_client_get_augments_tierlist_http_error() -> None:
    session = FakeSession({"https://tftacademy.com/api/tierlist/augments": FakeResponse(500, text="Server Error")})
    client = TFTAcademyClient(session=session)
    with pytest.raises(TFTAcademyError) as exc:
        client.get_augments_tierlist(18)
    assert "500" in str(exc.value)


def test_client_get_patch_info() -> None:
    svelte_data = {
        "nodes": [
            {"data": [{"patch": 1}, "18.1d", []]},
            {"data": [{"lastUpdated": 1}, None, "2026-09-07 16:48:56.543Z"]},
        ]
    }
    session = FakeSession({"https://tftacademy.com/tierlist/augments/__data.json": FakeResponse(200, svelte_data)})
    client = TFTAcademyClient(session=session)
    info = client.get_patch_info()
    assert info.get("patch") == "18.1d"
    assert "2026-09-07" in info.get("last_updated", "")
