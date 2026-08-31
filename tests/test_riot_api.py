"""Test tang Riot API - chay HOAN TOAN offline (feedback Tier 1 #5).

Khong test nao cham mang. Tang HTTP duoc test bang session gia; tang tong
hop (AugmentAggregator) von da thuan nen test thang.

Bat bien duoc bao ve manh nhat: LOC `tft_set_number`. Lich su nguoi choi con
match cua set truoc, va augment set cu lam ban so lieu MOT CACH IM LANG -
khong exception, khong canh bao, chi la nhung con so sai.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.knowledge.riot_api import (
    RANKED_TFT_QUEUE_ID,
    REGIONAL_OF_PLATFORM,
    TARGET_SET_NUMBER,
    AugmentAggregator,
    RateLimiter,
    RiotApiError,
    RiotAuthError,
    CompAggregator,
    RiotClient,
    active_traits,
    is_usable_match,
    main_trait,
)
from src.knowledge.stats_provider import AugmentStatsProvider, RiotApiProvider


# --- Do gia HTTP -----------------------------------------------------------


class FakeResponse:
    def __init__(self, status: int, payload: Any = None, headers: dict | None = None) -> None:
        self.status_code = status
        self._payload = payload
        self.headers = headers or {}
        self.text = str(payload)

    def json(self) -> Any:
        return self._payload


class FakeSession:
    """Session gia - ghi lai request va tra ve cac response da xep san."""

    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, dict]] = []

    def get(self, url: str, headers=None, params=None, timeout=None) -> FakeResponse:
        self.calls.append((url, dict(params or {})))
        return self.responses.pop(0) if self.responses else FakeResponse(200, {})


def fake_limiter() -> RateLimiter:
    """Limiter co dong ho TU CHAY, de test HTTP khong dinh chinh no dieu tiet.

    Dung dong ho dung yen + sleep rong o day se treo that: acquire() ngu roi
    kiem tra lai, nhung thoi gian khong bao gio troi. Dieu tiet duoc test
    rieng o cuoi file, voi dong ho troi theo sleep.
    """
    now = [0.0]

    def sleep(d: float) -> None:
        now[0] += d

    def clock() -> float:
        now[0] += 1.0  # moi lan hoi gio la mot giay troi qua -> khong bao gio ket
        return now[0]

    return RateLimiter(sleep=sleep, clock=clock)


def client(responses: list[FakeResponse], **kwargs: Any) -> RiotClient:
    kwargs.setdefault("platform", "vn2")
    return RiotClient(
        api_key="TEST-KEY",
        session=FakeSession(responses),
        limiter=fake_limiter(),
        **kwargs,
    )


def participant(placement: int, augments: list[str]) -> dict[str, Any]:
    return {"placement": placement, "augments": augments}


def match(
    *participants: dict[str, Any],
    set_number: int = TARGET_SET_NUMBER,
    queue_id: int = RANKED_TFT_QUEUE_ID,
    match_id: str = "VN2_1",
) -> dict[str, Any]:
    return {
        "metadata": {"match_id": match_id},
        "info": {
            "tft_set_number": set_number,
            "queue_id": queue_id,
            "participants": list(participants),
        },
    }


# --- Dinh tuyen ------------------------------------------------------------


def test_vn2_routes_to_sea() -> None:
    """DTCL Viet Nam nam o cum SEA cho match-v1, khong phai asia."""
    assert REGIONAL_OF_PLATFORM["vn2"] == "sea"
    assert client([]).regional == "sea"


def test_explicit_regional_wins_over_the_table() -> None:
    assert client([], regional="asia").regional == "asia"


def test_unknown_platform_fails_loudly_with_the_valid_options() -> None:
    """Go sai ten platform phai bao ngay, kem danh sach hop le."""
    with pytest.raises(RiotApiError, match="regional host"):
        client([], platform="khong_ton_tai")


# --- Xu ly loi HTTP --------------------------------------------------------


def test_401_says_the_personal_key_expired() -> None:
    """Personal Key het han sau 24 gio - do la nguyen nhan gan nhu chac chan.

    Thong bao phai noi dieu do, nếu khong nguoi dung se di tim bug trong code.
    """
    c = client([FakeResponse(401, {})])
    with pytest.raises(RiotAuthError, match="24 gio"):
        c.apex_league("challenger")


def test_403_is_also_treated_as_an_expired_key() -> None:
    c = client([FakeResponse(403, {})])
    with pytest.raises(RiotAuthError):
        c.apex_league("challenger")


def test_429_respects_retry_after_then_succeeds() -> None:
    """Ton trong Retry-After chu khong doan - va khong spam lai."""
    slept: list[float] = []
    limiter = fake_limiter()
    inner = limiter.sleep
    limiter.sleep = lambda d: (slept.append(d), inner(d))[1]  # type: ignore[assignment]
    c = RiotClient(
        api_key="K",
        platform="vn2",
        limiter=limiter,
        session=FakeSession(
            [
                FakeResponse(429, {}, {"Retry-After": "3"}),
                FakeResponse(200, {"entries": []}),
            ]
        ),
    )
    assert c.apex_league("master") == {"entries": []}
    assert slept and slept[0] >= 3.0


def test_server_errors_are_retried_then_give_up() -> None:
    c = client([FakeResponse(500, {}) for _ in range(4)])
    with pytest.raises(RiotApiError, match="het luot thu lai|HTTP 500"):
        c.apex_league("master")


def test_bad_tier_is_rejected_before_any_request() -> None:
    c = client([])
    with pytest.raises(RiotApiError, match="tier"):
        c.apex_league("bac_ii")


# --- Endpoint --------------------------------------------------------------


def test_apex_puuids_reads_puuid_and_dedupes() -> None:
    """Doc thang `puuid`. Riot da go dan cac duong di qua summonerId tu 2025."""
    entries = {"entries": [{"puuid": "a"}, {"puuid": "b"}, {"puuid": "a"}]}
    c = client([FakeResponse(200, entries)])
    assert c.apex_puuids(["challenger"]) == ["a", "b"]


def test_apex_puuids_skips_entries_without_puuid() -> None:
    c = client([FakeResponse(200, {"entries": [{"puuid": "a"}, {"summonerId": "x"}]})])
    assert c.apex_puuids(["master"]) == ["a"]


def test_match_ids_uses_the_regional_host_and_clamps_count() -> None:
    c = client([FakeResponse(200, ["VN2_1"])])
    c.match_ids("puuid-1", count=9999)
    url, params = c.session.calls[0]
    assert "sea.api.riotgames.com" in url
    assert params["count"] == 200


def test_league_uses_the_platform_host() -> None:
    c = client([FakeResponse(200, {"entries": []})])
    c.apex_league("challenger")
    assert "vn2.api.riotgames.com" in c.session.calls[0][0]


# --- Loc match: bat bien quan trong nhat ----------------------------------


def test_matches_from_other_sets_are_rejected() -> None:
    """Match Set 17 trong lich su se lam ban so lieu Set 18 mot cach im lang."""
    assert is_usable_match(match(participant(1, ["A"])))
    assert not is_usable_match(match(participant(1, ["A"]), set_number=17))


def test_non_ranked_queues_are_rejected() -> None:
    """Hyper roll / double up co meta khac - tron vao thi so lieu vo nghia."""
    assert not is_usable_match(match(participant(1, ["A"]), queue_id=1160))


def test_camel_case_info_fields_are_also_read() -> None:
    """`info` cua TFT dung snake_case, nguoc voi phan con lai cua Riot API.

    Doc ca hai de khong vo hieu neu Riot chuan hoa lai.
    """
    m = {
        "metadata": {"match_id": "VN2_2"},
        "info": {
            "tftSetNumber": TARGET_SET_NUMBER,
            "queueId": RANKED_TFT_QUEUE_ID,
            "participants": [participant(1, ["A"])],
        },
    }
    assert is_usable_match(m)


def test_match_without_participants_is_rejected() -> None:
    assert not is_usable_match(match())


# --- Tong hop --------------------------------------------------------------


def test_aggregator_counts_one_observation_per_augment_held() -> None:
    agg = AugmentAggregator()
    agg.add_match(match(participant(1, ["A", "B"]), participant(8, ["A"])))
    assert agg.tallies["A"].n == 2
    assert agg.tallies["B"].n == 1
    assert agg.tallies["A"].avg_place == pytest.approx(4.5)
    assert agg.tallies["B"].avg_place == pytest.approx(1.0)


def test_top4_and_win_rate_are_computed_from_placement() -> None:
    agg = AugmentAggregator()
    for placement in (1, 2, 5, 8):
        agg.add_match(match(participant(placement, ["A"]), match_id=f"VN2_{placement}"))
    t = agg.tallies["A"]
    assert t.n == 4
    assert t.top4_rate == pytest.approx(0.5)
    assert t.win_rate == pytest.approx(0.25)
    assert t.avg_place == pytest.approx(4.0)


def test_rejected_matches_are_counted_but_not_tallied() -> None:
    """Phai phan biet duoc "da xem" va "dung duoc" - de bao cao ti le loc."""
    agg = AugmentAggregator()
    agg.add_match(match(participant(1, ["A"])))
    agg.add_match(match(participant(1, ["B"]), set_number=17))
    assert agg.matches_seen == 2
    assert agg.matches_used == 1
    assert "B" not in agg.tallies


def test_invalid_placements_are_skipped() -> None:
    agg = AugmentAggregator()
    agg.add_match(match(participant(0, ["A"]), participant(3, ["A"])))
    assert agg.tallies["A"].n == 1


def test_match_ids_are_recorded_for_provenance() -> None:
    """Truy nguoc den tung match la diem manh nhat cua nguon nay."""
    agg = AugmentAggregator()
    agg.add_match(match(participant(1, ["A"]), match_id="VN2_42"))
    assert agg.match_ids == ["VN2_42"]


def test_rows_match_the_csv_provider_contract() -> None:
    agg = AugmentAggregator()
    agg.add_match(match(participant(2, ["A"])))
    row = next(iter(agg.rows("riot:test")))
    assert set(row) == {"api_name", "avg_place", "top4_rate", "win_rate", "sample_n", "source"}
    assert row["source"] == "riot:test"


def test_rows_can_drop_augments_below_a_sample_floor() -> None:
    agg = AugmentAggregator()
    agg.add_match(match(participant(1, ["rare"]), participant(2, ["common"])))
    agg.add_match(match(participant(3, ["common"]), match_id="VN2_2"))
    kept = {r["api_name"] for r in agg.rows("s", min_sample_n=2)}
    assert kept == {"common"}


# --- Provider --------------------------------------------------------------


def test_provider_satisfies_the_protocol_and_never_calls_the_network() -> None:
    """`get()` chi tra cache. Mot request HTTP tren duong 30 giay la vi pham
    SPEC 3.5.3 - va lam ablation study mat tinh tai lap."""
    agg = AugmentAggregator()
    agg.add_match(match(participant(1, ["A"])))
    provider = RiotApiProvider.from_aggregator(agg, "riot:test")

    assert isinstance(provider, AugmentStatsProvider)
    assert provider.name == "riot-api"
    assert len(provider) == 1

    stats = provider.get("A")
    assert stats is not None
    assert stats.avg_place == pytest.approx(1.0)
    assert stats.source == "riot:test"
    assert provider.get("khong_co") is None


def test_empty_provider_is_a_valid_state() -> None:
    assert RiotApiProvider().get("A") is None


# --- Rate limiter ----------------------------------------------------------


def test_limiter_throttles_on_the_two_minute_window() -> None:
    """100 req / 2 phut moi la gioi han that (~0.83 req/s), khong phai 20/s."""
    now = [0.0]
    slept: list[float] = []

    def sleep(d: float) -> None:
        slept.append(d)
        now[0] += d

    limiter = RateLimiter(sleep=sleep, clock=lambda: now[0])
    for _ in range(200):
        limiter.acquire()
        now[0] += 0.001

    assert slept, "khong ngu lan nao -> se dinh 429"
    assert now[0] > 100.0, "200 request khong the xong trong duoi 100 giay"


def test_limiter_does_not_livelock_on_a_subnanosecond_wait() -> None:
    """Regression: phep tru dau cham dong sinh ra khoang cho ~1.1e-16 giay.

    Ngu tung do khong lam dong ho nhich duoc, nen acquire() tinh lai y het
    va quay mai o 100% CPU. Bug that, da lam treo ca suite truoc khi sua.

    Test dung dong ho CHI nhich khi co ai ngu - dung dieu kien sinh ra
    livelock - va chan so vong lap de treo thi do chu khong phai treo mai.
    """
    now = [0.0]
    limiter = RateLimiter(sleep=lambda d: now.__setitem__(0, now[0] + d), clock=lambda: now[0])

    calls = 0
    for _ in range(60):
        limiter.acquire()
        now[0] += 0.001
        calls += 1
    assert calls == 60


def test_limiter_ignores_waits_below_the_floor() -> None:
    """Khoang cho duoi 1 ms bi bo qua - la ngu nhieu (bien an toan 10% da du)."""
    now = [0.0]
    slept: list[float] = []
    limiter = RateLimiter(
        sleep=lambda d: (slept.append(d), now.__setitem__(0, now[0] + d))[0],
        clock=lambda: now[0],
    )
    for _ in range(40):
        limiter.acquire()
        now[0] += 0.001
    assert all(d > 0.001 for d in slept), f"co lan ngu duoi nguong: {slept}"


# --- Tong hop doi hinh -----------------------------------------------------
#
# ⚠️ Phat hien 2026-09-01: participant Set 18 KHONG con truong `augments`.
# Nhung `units`/`traits`/`placement` van co, nen doi hinh crawl duoc that.
# Cac test duoi day bao ve duong do.


def trait(name: str, style: int = 3, num_units: int = 4) -> dict[str, Any]:
    return {"name": name, "style": style, "num_units": num_units, "tier_current": 1}


def unit(character_id: str, items: list[str] | None = None) -> dict[str, Any]:
    return {"character_id": character_id, "itemNames": items or [], "tier": 2}


def comp_participant(
    placement: int,
    traits: list[dict[str, Any]],
    units: list[dict[str, Any]] | None = None,
    level: int = 8,
) -> dict[str, Any]:
    return {
        "placement": placement,
        "traits": traits,
        "units": units or [],
        "level": level,
    }


def test_set18_participants_really_have_no_augments_field() -> None:
    """Ghi lai phat hien: khong con `augments` trong payload Set 18.

    Test nay khong goi mang - no khoa lai HINH DANG du lieu that da do duoc,
    de neu ai do sau nay tuong `augments` van con thi doc duoc o day.
    Cac truong con lai la nhung gi con dung duoc.
    """
    real_keys = {
        "companion", "gold_left", "last_round", "level", "missions",
        "placement", "players_eliminated", "puuid", "riotIdGameName",
        "riotIdTagline", "time_eliminated", "total_damage_to_players",
        "traits", "units", "win",
    }
    assert "augments" not in real_keys
    assert {"units", "traits", "placement", "level"} <= real_keys


def test_inactive_traits_are_not_counted() -> None:
    """style = 0 nghia la co unit mang trait nhung CHUA du nguong kich hoat."""
    p = comp_participant(1, [trait("A", style=0), trait("B", style=2)])
    assert active_traits(p) == {"B": 4}


def test_main_trait_is_the_highest_style() -> None:
    p = comp_participant(1, [trait("A", style=1), trait("B", style=4)])
    assert main_trait(p) == "B"


def test_main_trait_breaks_ties_on_unit_count() -> None:
    p = comp_participant(1, [trait("A", style=3, num_units=2), trait("B", style=3, num_units=6)])
    assert main_trait(p) == "B"


def test_main_trait_is_none_when_nothing_is_active() -> None:
    assert main_trait(comp_participant(1, [trait("A", style=0)])) is None
    assert main_trait(comp_participant(1, [])) is None


def test_participants_group_into_comps_by_main_trait() -> None:
    agg = CompAggregator()
    agg.add_match(
        match(
            comp_participant(1, [trait("Riftbeast")]),
            comp_participant(5, [trait("Riftbeast")]),
            comp_participant(2, [trait("Ravager")]),
        )
    )
    assert set(agg.comps) == {"Riftbeast", "Ravager"}
    assert agg.comps["Riftbeast"].n == 2
    assert agg.comps["Riftbeast"].avg_placement == pytest.approx(3.0)
    assert agg.comps["Ravager"].top4_rate == pytest.approx(1.0)


def test_units_and_items_are_counted_per_comp() -> None:
    agg = CompAggregator()
    agg.add_match(
        match(
            comp_participant(
                1, [trait("R")], [unit("DA_18_Ahri", ["TFT_Item_BlueBuff"]), unit("DA_Krug18")]
            )
        )
    )
    tally = agg.comps["R"]
    assert tally.units["DA_18_Ahri"] == 1
    assert tally.items["TFT_Item_BlueBuff"] == 1


def test_participants_without_an_active_trait_are_skipped() -> None:
    agg = CompAggregator()
    agg.add_match(match(comp_participant(1, [trait("A", style=0)])))
    assert agg.comps == {}
    assert agg.participants == 0


def test_records_match_the_metacomp_schema_exactly() -> None:
    """MetaComp(**r) splat thang - thua mot key la TypeError luc nap."""
    from src.knowledge.comp_database import MetaComp

    agg = CompAggregator()
    for i in range(3):
        agg.add_match(
            match(
                comp_participant(1, [trait("R")], [unit("DA_X", ["I1"])]),
                match_id=f"VN2_{i}",
            )
        )
    records = agg.comp_records("riot:test", min_sample_n=1)
    assert records
    allowed = set(MetaComp.__dataclass_fields__)
    for r in records:
        assert set(r) <= allowed, set(r) - allowed
        MetaComp(**r)


def test_best_augments_is_empty_never_invented() -> None:
    """Riot khong cap augment o Set 18 -> de rong, KHONG doan.

    CompSelector coi danh sach rong la "khong co tin hieu", dung hon han mot
    danh sach bia ma no se tin.
    """
    agg = CompAggregator()
    agg.add_match(match(comp_participant(1, [trait("R")])))
    assert agg.comp_records("s", min_sample_n=1)[0]["best_augments"] == []


def test_comps_below_the_sample_floor_are_dropped() -> None:
    agg = CompAggregator()
    agg.add_match(
        match(
            comp_participant(1, [trait("pho_bien")]),
            comp_participant(2, [trait("pho_bien")]),
            comp_participant(3, [trait("hiem")]),
        )
    )
    kept = {r["name"] for r in agg.comp_records("s", min_sample_n=2)}
    assert kept == {"pho_bien Core"}


def test_records_are_ranked_by_average_placement() -> None:
    agg = CompAggregator()
    agg.add_match(
        match(
            comp_participant(1, [trait("tot")]),
            comp_participant(8, [trait("te")]),
        )
    )
    records = agg.comp_records("s", min_sample_n=1)
    assert [r["name"] for r in records] == ["tot Core", "te Core"]
    assert records[0]["tier"] == "S"


def test_play_rate_is_a_share_of_participants() -> None:
    agg = CompAggregator()
    agg.add_match(
        match(
            comp_participant(1, [trait("A")]),
            comp_participant(2, [trait("A")]),
            comp_participant(3, [trait("B")]),
            comp_participant(4, [trait("B")]),
        )
    )
    for r in agg.comp_records("s", min_sample_n=1):
        assert r["play_rate"] == pytest.approx(0.5)


def test_matches_from_other_sets_never_reach_the_comp_tally() -> None:
    agg = CompAggregator()
    agg.add_match(match(comp_participant(1, [trait("A")]), set_number=17))
    assert agg.comps == {}
    assert agg.matches_seen == 1
    assert agg.matches_used == 0


def test_only_defining_traits_are_kept() -> None:
    """Trait phai xuat hien o >= mot nua so van cua doi hinh do.

    Khong loc thi mot doi hinh liet ke 17 trait - moi trait ma bat ky ai
    trong nhom tung bat mot lan. Do duoc tren du lieu that 2026-09-01.
    """
    agg = CompAggregator()
    for i in range(4):
        # "R" co o ca 4 van; "hiem" chi o van dau tien.
        traits = [trait("R")] + ([trait("hiem", style=1, num_units=2)] if i == 0 else [])
        agg.add_match(match(comp_participant(1, traits), match_id=f"VN2_{i}"))

    record = agg.comp_records("s", min_sample_n=1)[0]
    assert "R" in record["traits"]
    assert "hiem" not in record["traits"], record["traits"]


def test_trait_share_threshold_is_tunable() -> None:
    """Ha nguong thi trait phu duoc giu lai.

    "hiem" phai co style THAP hon "R", neu khong no thanh trait chinh va
    participant do bi tach sang mot doi hinh khac (main_trait pha hoa bang
    ten, va "hiem" > "R").
    """
    agg = CompAggregator()
    for i in range(4):
        traits = [trait("R")] + ([trait("hiem", style=1, num_units=2)] if i == 0 else [])
        agg.add_match(match(comp_participant(1, traits), match_id=f"VN2_{i}"))

    strict = agg.comp_records("s", min_sample_n=1)[0]
    loose = agg.comp_records("s", min_sample_n=1, trait_share=0.2)[0]
    assert "hiem" not in strict["traits"]
    assert "hiem" in loose["traits"]
