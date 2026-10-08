"""Test crawler luot chao augment cua datatft (scripts/crawl_datatft_augments.py) - OFFLINE.

Fixture la ban cat nho cua trang /database va file h5-data-cn-18 tai ngay
2026-10-06 (tests/fixtures/datatft/). Khong test nao goi mang.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import crawl_datatft_augments as crawl
from src.knowledge.augment_features import OFFER_ROUNDS, load_offer_rounds

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).parent / "fixtures" / "datatft"
SNAPSHOT = ROOT / "data" / "augment_rounds.datatft.json"
FEATURES = ROOT / "data" / "augment_features.json"

CATALOG = [
    "DA_18_InfernoTraitAugment", "DA_18_ResidualMagic", "DA_SilverDestinyPlus",
    "DA_TradeSector", "DA_18_BigGrabBag", "DA_HedgeFund", "DA_NestingDollsPlus",
    "DA_Flexible",
]


@pytest.fixture(scope="module")
def html() -> str:
    return (FIXTURES / "database.trimmed.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def payload() -> dict:
    return json.loads((FIXTURES / "h5-data-cn-18.trimmed.json").read_text(encoding="utf-8"))


# --- tim dia chi file ----------------------------------------------------------


def test_asset_url_is_read_from_the_preload_block(html) -> None:
    assert crawl.find_asset_url(html) == (
        "https://www.datatft.com/assets/h5-data-cn-18-DA3Z5d73.json"
    )
    # Set khac nam cung bang: khong lay nham file Set 18.
    assert crawl.find_asset_url(html, 17).endswith("/assets/h5-data-cn-17-BikBV7Ou.json")


def test_asset_url_follows_a_new_content_hash(html) -> None:
    """Hash doi moi lan ho cap nhat - crawler khong duoc ghi cung."""
    assert crawl.find_asset_url(html.replace("DA3Z5d73", "Zz9_new-")).endswith(
        "h5-data-cn-18-Zz9_new-.json"
    )


@pytest.mark.parametrize(
    "broken",
    [
        "<html><body>khong co khoi preload</body></html>",
        '<script id="h5-data-preload">var other = 1;</script>',
        '<script id="h5-data-preload">var urls = {"17":"/assets/h5-data-cn-17-x.json"};</script>',
        '<script id="h5-data-preload">var urls = {not json};</script>',
    ],
)
def test_asset_url_miss_fails_loudly(broken) -> None:
    with pytest.raises(crawl.DataTFTError):
        crawl.find_asset_url(broken)


# --- doc payload ---------------------------------------------------------------


def test_parse_reads_rounds_types_and_list_index(payload) -> None:
    parsed = crawl.parse_augments(payload)
    assert parsed["DA_HedgeFund"] == {"rounds": ["2-1"], "types": [1], "list_index": 2}
    assert parsed["DA_18_BigGrabBag"]["rounds"] == ["3-2", "4-2"]
    assert parsed["DA_NestingDollsPlus"]["types"] == []      # 2 lose cua nguon khong co `type`
    assert "TFT9_Augment_RollTheDice" in parsed              # loc catalog la viec cua build_snapshot


def test_parse_orders_rounds_and_rejects_unknown_ones() -> None:
    row = {"hexId": "DA_X", "round": ["4-2", "2-1", "4-2"], "type": [1]}
    assert crawl.parse_augments({"hexs18": [[row]]})["DA_X"]["rounds"] == ["2-1", "4-2"]
    with pytest.raises(crawl.DataTFTError, match="luot la"):
        crawl.parse_augments({"hexs18": [[{**row, "round": ["5-2"]}]]})


def test_missing_hexs_fails_loudly() -> None:
    with pytest.raises(crawl.DataTFTError, match="hexs18"):
        crawl.parse_augments({"hexs11": [[]], "databaseUpdateTime": 1})


# --- snapshot ------------------------------------------------------------------


def test_snapshot_shape_keeps_only_catalog_augments(payload) -> None:
    snap = crawl.build_snapshot(payload, CATALOG + ["DA_KhongCo"], {"source": "datatft.com"},
                                min_matched=8)
    assert set(snap) == {"meta", "augments"}
    assert sorted(snap["augments"]) == sorted(CATALOG)       # bo 2 lose ngoai catalog
    assert all(set(r) == {"rounds", "types", "list_index"} for r in snap["augments"].values())
    meta = snap["meta"]
    assert (meta["matched"], meta["n_catalog"], meta["set"]) == (8, 9, "TFTSet18")
    assert meta["missing_from_datatft"] == ["DA_KhongCo"]
    assert meta["database_updated_at"] == "2026-10-04T12:35:31+00:00"
    assert meta["source"] == "datatft.com"


def test_low_match_refuses_to_build(payload) -> None:
    """Fixture chi khop 8 lose: voi nguong mac dinh (250) phai tu choi."""
    with pytest.raises(crawl.DataTFTError, match="chi khop 8/8"):
        crawl.build_snapshot(payload, CATALOG, {})


def _features(tmp_path: Path) -> Path:
    path = tmp_path / "features.json"
    path.write_text(json.dumps({"augments": {a: {} for a in CATALOG}}), encoding="utf-8")
    return path


def test_main_low_match_exits_nonzero_and_keeps_old_snapshot(tmp_path) -> None:
    out = tmp_path / "rounds.json"
    out.write_text('{"meta": {"matched": 254}}', encoding="utf-8")
    code = crawl.main([
        "--from-file", str(FIXTURES / "h5-data-cn-18.trimmed.json"),
        "--features", str(_features(tmp_path)), "--out", str(out), "--overwrite",
    ])
    assert code == 1
    assert out.read_text(encoding="utf-8") == '{"meta": {"matched": 254}}'


def test_main_needs_overwrite_and_writes_a_loadable_snapshot(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(crawl, "MIN_MATCHED", 8)
    out = tmp_path / "rounds.json"
    argv = [
        "--from-file", str(FIXTURES / "h5-data-cn-18.trimmed.json"),
        "--asset-url", "https://www.datatft.com/assets/h5-data-cn-18-DA3Z5d73.json",
        "--crawled-at", "2026-10-06T00:00:00+00:00",
        "--features", str(_features(tmp_path)), "--out", str(out),
    ]
    assert crawl.main(argv) == 0
    first = out.read_text(encoding="utf-8")
    assert crawl.main(argv) == 1                              # da co file, thieu --overwrite
    assert crawl.main([*argv, "--overwrite"]) == 0
    assert out.read_text(encoding="utf-8") == first           # tai lap duoc tu cung file
    meta = json.loads(first)["meta"]
    assert (meta["server"], meta["crawled_at"]) == ("CN", "2026-10-06T00:00:00+00:00")
    assert meta["asset_url"].endswith("h5-data-cn-18-DA3Z5d73.json")
    assert load_offer_rounds(out)["DA_HedgeFund"] == ["2-1"]


def test_live_path_makes_exactly_two_stateless_gets(tmp_path, html, monkeypatch) -> None:
    """Hai GET, khong hon; khong qua requests.Session cua ta, khong cookie."""
    import requests

    calls: list[tuple[str, dict]] = []
    body = (FIXTURES / "h5-data-cn-18.trimmed.json").read_text(encoding="utf-8")

    class Resp:
        def __init__(self, text: str) -> None:
            self.text, self.encoding = text, None

        def raise_for_status(self) -> None:
            return None

    def fake_get(url: str, **kwargs):
        calls.append((url, kwargs))
        return Resp(html if url == crawl.PAGE_URL else body)

    def no_session(*_a, **_k):
        raise AssertionError("crawler khong duoc tao requests.Session")

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(requests, "Session", no_session)
    monkeypatch.setattr(crawl, "MIN_MATCHED", 8)
    out = tmp_path / "rounds.json"
    assert crawl.main(["--features", str(_features(tmp_path)), "--out", str(out)]) == 0

    assert [u for u, _ in calls] == [
        crawl.PAGE_URL, "https://www.datatft.com/assets/h5-data-cn-18-DA3Z5d73.json",
    ]
    for _, kwargs in calls:
        assert set(kwargs) == {"headers", "timeout"}          # khong cookies/auth/session
        assert set(kwargs["headers"]) == {"User-Agent"}
        assert kwargs["headers"]["User-Agent"].startswith("Mozilla/5.0")
    assert json.loads(out.read_text(encoding="utf-8"))["meta"]["asset_url"] == calls[1][0]


def test_page_without_asset_url_never_requests_the_json(tmp_path, monkeypatch) -> None:
    import requests

    calls: list[str] = []

    class Resp:
        text, encoding = "<html>doi giao dien</html>", None

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(requests, "get", lambda url, **_k: calls.append(url) or Resp())
    out = tmp_path / "rounds.json"
    out.write_text("cu", encoding="utf-8")
    code = crawl.main(["--features", str(_features(tmp_path)), "--out", str(out), "--overwrite"])
    assert code == 1 and calls == [crawl.PAGE_URL]
    assert out.read_text(encoding="utf-8") == "cu"


# --- snapshot da commit ----------------------------------------------------------


@pytest.mark.skipif(not SNAPSHOT.exists(), reason="chua crawl data/augment_rounds.datatft.json")
def test_committed_snapshot_covers_the_catalog() -> None:
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    catalog = set(json.loads(FEATURES.read_text(encoding="utf-8"))["augments"])
    assert set(snap["augments"]) <= catalog
    assert snap["meta"]["matched"] == len(snap["augments"]) >= crawl.MIN_MATCHED
    assert (snap["meta"]["server"], snap["meta"]["set"]) == ("CN", "TFTSet18")
    for api, row in snap["augments"].items():
        assert row["rounds"] and set(row["rounds"]) <= set(OFFER_ROUNDS), api
    # Ca chay ra van de: Hedge Fund chi co o 2-1 (docs/offer-rounds/overview.md).
    assert snap["augments"]["DA_HedgeFund"]["rounds"] == ["2-1"]
