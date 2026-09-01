"""Test nguon tactics.tools - chay HOAN TOAN offline.

Khong test nao cham mang. Tang HTTP duoc test bang do gia; hai ham chuyen
doi (`comp_records`, `general_records`) von thuan nen test thang.

BA BAT BIEN DUOC BAO VE, theo thu tu quan trong:

    1. HAI QUY UOC KHONG DUOC TRON. /team-compositions tra `top4` la SO DEM,
       /stats2/general tra `top4` la PHAN TRAM. Tron lai thi top4_rate = 50.0
       thay vi 0.5 va moi augment/doi hinh deu hoan hao - hong hoan toan im
       lang. Day la bug de mac nhat cua module nay.

    2. BAN GHI PHAI VUA KHUON MetaComp. Hai nguon (Riot va tactics.tools) do
       chung mot khuon, nen comp_selector khong phai biet du lieu den tu dau.
       Them mot key la TypeError ngay tai day.

    3. `augment_row_count` == 0 LA MOT KET QUA DO DUOC, khong phai gia dinh.
       Do 2026-09-01: ca bon truong augment cua tactics.tools deu rong tren
       1,75 trieu van. Test nay khoa ca hai chieu - neu mot ngay payload co
       augment that, ham phai dem duoc, va khi do augment_stats.csv co the
       thoi la MOCK-NOT-REAL.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.knowledge.comp_database import MetaComp
from src.knowledge.tactics_tools import (
    RANK_GROUPS,
    SET18_PATCH,
    TacticsToolsClient,
    TacticsToolsError,
    augment_row_count,
    comp_records,
    general_records,
    rank_group_code,
    source_label,
)


# --- Do gia HTTP -----------------------------------------------------------


class FakeResponse:
    def __init__(self, status: int, payload: Any = None, bad_json: bool = False) -> None:
        self.status_code = status
        self._payload = payload
        self._bad_json = bad_json

    def json(self) -> Any:
        if self._bad_json:
            raise ValueError("khong phai JSON")
        return self._payload


def client_with(monkeypatch, response: Any) -> TacticsToolsClient:
    """Client da bi thay `requests.get` - va da tat gian cach cho."""
    import src.knowledge.tactics_tools as mod

    monkeypatch.setattr(mod.requests, "get", lambda *a, **k: response)
    monkeypatch.setattr(mod, "MIN_INTERVAL_S", 0.0)
    return TacticsToolsClient()


# --- Payload mau -----------------------------------------------------------


def group(
    count: int,
    place: float,
    top4: int,
    win: int,
    carry: str = "DA_18_Carry",
    trait: str = "DA_18_Trait",
    **extra: Any,
) -> dict[str, Any]:
    full: dict[str, Any] = {
        "count": count,
        "place": place,
        "top4": top4,
        "win": win,
        "carryUnits": [[carry, 2.5]],
        # [id, tier, count, place]
        "units": [
            [carry, 2, count, place],
            ["DA_18_Second", 2, count, place],
            ["DA_18_Third", 1, count, place],
            ["DA_18_Fourth", 1, count, place],
            ["DA_18_Fifth", 1, count, place],
            ["DA_18_Rare", 1, 1, place],  # duoi nguong DEFINING_SHARE
        ],
        "traits": [[trait, 3, count, place], ["DA_18_Fringe", 1, 1, place]],
        "generalItems": [["DA_ItemA", count, place, top4, win], ["DA_ItemB", count, place, 0, 0]],
        "levels": [[9, 0, count // 4], [8, 0, count]],
        "augmentSingles": [],
        "aug1s": [],
        "aug2s": [],
        "aug3s": [],
    }
    full.update(extra)
    return {"full": full, "children": []}


def comps_payload(*groups: dict[str, Any], total: int = 1000) -> dict[str, Any]:
    return {"groups": list(groups), "count": total, "place": 4.5}


# --- Tham so URL -----------------------------------------------------------


def test_rank_group_names_map_to_the_documented_codes() -> None:
    assert rank_group_code("all") == 3
    assert rank_group_code("gm") == 4
    assert set(RANK_GROUPS) == {"top", "high", "plat", "all", "gm"}


def test_unknown_rank_group_fails_before_any_request() -> None:
    with pytest.raises(TacticsToolsError) as exc:
        rank_group_code("challenger")
    # Thong bao phai liet ke gia tri hop le, khong bat nguoi dung doan.
    assert "all" in str(exc.value)


def test_urls_carry_the_patch_and_rank_group(monkeypatch) -> None:
    seen: list[str] = []

    import src.knowledge.tactics_tools as mod

    def fake_get(url, **kwargs):
        seen.append(url)
        return FakeResponse(200, {})

    monkeypatch.setattr(mod.requests, "get", fake_get)
    monkeypatch.setattr(mod, "MIN_INTERVAL_S", 0.0)

    c = TacticsToolsClient()
    c.team_compositions(3)
    c.general_stats(3)

    assert seen[0].endswith(f"/team-compositions/3/{SET18_PATCH}")
    assert seen[1].endswith(f"/stats2/general/1100/{SET18_PATCH}/3")


def test_non_200_and_bad_json_both_fail_loudly(monkeypatch) -> None:
    c = client_with(monkeypatch, FakeResponse(503))
    with pytest.raises(TacticsToolsError):
        c.team_compositions(3)

    c = client_with(monkeypatch, FakeResponse(200, bad_json=True))
    with pytest.raises(TacticsToolsError):
        c.team_compositions(3)


# --- Bat bien 3: augment van rong -----------------------------------------


def test_augment_rows_are_zero_on_the_shape_measured_in_september() -> None:
    payload = comps_payload(group(500, 4.2, 250, 60), group(400, 4.4, 190, 40))
    assert augment_row_count(payload) == 0


def test_augment_rows_are_counted_if_they_ever_come_back() -> None:
    """Neu Riot/tactics.tools mo lai nguon augment, ham phai DEM duoc.

    Khong co test nay thi `== 0` chi chung minh ham luon tra 0.
    """
    payload = comps_payload(
        group(500, 4.2, 250, 60, augmentSingles=[{"id": "DA_X"}], aug2s=[{"id": "DA_Y"}])
    )
    assert augment_row_count(payload) == 2


# --- Bat bien 1 + 2: chuyen doi doi hinh ----------------------------------


def test_records_fit_the_meta_comp_schema_exactly() -> None:
    records = comp_records(comps_payload(group(500, 4.2, 250, 60)), "src", min_sample_n=1)
    # Thua mot key -> TypeError ngay tai day, khong doi den luc nap file.
    comps = [MetaComp(**r) for r in records]
    assert len(comps) == 1
    assert comps[0].source == "src"


def test_counts_become_rates_not_percentages() -> None:
    """250/500 phai ra 0.5, khong phai 250 va cung khong phai 50.0."""
    records = comp_records(comps_payload(group(500, 4.2, 250, 60)), "src", min_sample_n=1)
    assert records[0]["top4_rate"] == 0.5
    assert records[0]["win_rate"] == 0.12
    assert 0.0 <= records[0]["play_rate"] <= 1.0


def test_the_carry_leads_the_core_and_rare_units_are_dropped() -> None:
    records = comp_records(
        comps_payload(group(500, 4.2, 250, 60, carry="DA_18_Kayle")), "src", min_sample_n=1
    )
    core = records[0]["core_units"]
    assert core[0] == "DA_18_Kayle"
    # Unit chi xuat hien 1/500 van khong dinh nghia doi hinh nao.
    assert "DA_18_Rare" not in core + records[0]["flex_units"]


def test_only_defining_traits_survive() -> None:
    records = comp_records(comps_payload(group(500, 4.2, 250, 60)), "src", min_sample_n=1)
    assert list(records[0]["traits"]) == ["DA_18_Trait"]


def test_best_augments_stay_empty_rather_than_guessed() -> None:
    records = comp_records(comps_payload(group(500, 4.2, 250, 60)), "src", min_sample_n=1)
    assert records[0]["best_augments"] == []


def test_modal_level_wins_over_the_first_one_listed() -> None:
    records = comp_records(comps_payload(group(400, 4.2, 200, 50)), "src", min_sample_n=1)
    # levels = [[9, _, 100], [8, _, 400]] -> 8 pho bien hon du dung sau.
    assert list(records[0]["level_timing"]) == ["8"]


def test_small_groups_are_dropped_before_they_can_mislead() -> None:
    payload = comps_payload(group(500, 4.2, 250, 60), group(10, 3.0, 9, 5))
    records = comp_records(payload, "src", min_sample_n=200)
    assert [r["sample_n"] for r in records] == [500]


def test_groups_are_ranked_by_placement_and_tiered() -> None:
    payload = comps_payload(
        group(500, 4.6, 200, 30, carry="DA_Worse"),
        group(500, 4.0, 300, 80, carry="DA_Better"),
    )
    records = comp_records(payload, "src", min_sample_n=1)
    assert records[0]["core_units"][0] == "DA_Better"
    assert records[0]["tier"] == "S"


def test_empty_payload_yields_no_records_instead_of_crashing() -> None:
    assert comp_records({"groups": [], "count": 0}, "src") == []


def test_source_label_names_the_provider_up_front() -> None:
    """Nguoi doc overlay phai thay ngay day khong phai so tu crawl."""
    label = source_label("team-compositions", "all", SET18_PATCH, 456572)
    assert label.startswith("tactics.tools:")
    assert "n=456572" in label


# --- Bat bien 1: chuyen doi stats general ---------------------------------


def general_payload() -> dict[str, Any]:
    return {
        "totalEntries": 1_752_735,
        "lastUpdated": 1788201839,
        "units": {
            "DA_18_Ahri": {
                "count": 11983,
                "place": 4.49,
                "top4": 50.34,  # PHAN TRAM
                "won": 10.98,
                "topItems": ["DA_StrikersFlail"],
            }
        },
        "traits": {"DA_18_Sprykin__1": {"count": 2856, "place": 4.37, "top4": 51.75, "won": 18.59}},
        "items": [
            {"itemId": "DA_TacticiansCape", "count": 991, "place": 4.08, "top4": 56.91, "won": 17.46}
        ],
    }


def test_percentages_become_rates() -> None:
    rows = general_records(general_payload(), "src")
    assert rows["units"][0]["top4_rate"] == 0.5034
    assert rows["units"][0]["win_rate"] == 0.1098
    assert rows["traits"][0]["top4_rate"] == 0.5175
    assert rows["items"][0]["top4_rate"] == 0.5691


def test_general_records_keep_counts_and_provenance() -> None:
    rows = general_records(general_payload(), "src")
    assert rows["total_entries"] == 1_752_735
    assert rows["units"][0]["count"] == 11983
    assert all(r["source"] == "src" for r in rows["units"] + rows["traits"] + rows["items"])


def test_general_records_survive_a_payload_missing_every_section() -> None:
    rows = general_records({}, "src")
    assert rows["units"] == rows["traits"] == rows["items"] == []
