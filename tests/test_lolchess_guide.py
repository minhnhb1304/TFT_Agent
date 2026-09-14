"""Test nguon lolchess.gg/guide - chay hoan toan OFFLINE.

Ba nhom:
    1. Parser tren fixture HTML that (da rut gon) - so khop tung con so.
    2. DRIFT: hang so trong code (roll_odds, rules_engine, scoring_weights)
       phai bang data/lolchess_guide.json. Crawl lai sau patch ma so doi thi
       nhom nay do - sua hang so co y thuc, khong de lech im lang.
    3. DOI CHIEU CHEO: bang cua lolchess vs nguon khac (CDragon, patch notes,
       luat xoay bai cua nguoi choi).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.knowledge.lolchess_guide import (
    LolchessClient,
    LolchessError,
    parse_champions,
    parse_exp,
    parse_patch_list,
    parse_reroll,
    parse_roles,
    parse_rounds,
    parse_system_changes,
)

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures" / "lolchess"


def page(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def guide() -> dict:
    return json.loads((ROOT / "data" / "lolchess_guide.json").read_text(encoding="utf-8"))


# --- 1. parser ---------------------------------------------------------------------


def test_exp_page_gives_set18_xp_table_and_income() -> None:
    eco = parse_exp(page("exp.html"))
    assert eco["xp_to_next"] == {1: 0, 2: 2, 3: 6, 4: 10, 5: 20, 6: 36, 7: 56, 8: 64, 9: 64}
    assert eco["passive_xp_per_round"] == 2
    assert eco["pvp_win_gold"] == 1
    assert eco["streak_bonus"] == {1: 0, 2: 1, 3: 1, 4: 1, 5: 2, 6: 3}
    assert eco["base_income"][-1] == {"round": "2-2~", "gold": 5}
    assert eco["interest"][-1] == {"min": 50, "max": None, "gold": 5}


def test_reroll_page_gives_shop_odds_and_pool() -> None:
    shop = parse_reroll(page("reroll.html"))
    assert shop["pool_size"] == {1: 30, 2: 25, 3: 18, 4: 10, 5: 9}
    assert shop["shop_odds"][8] == [0.15, 0.20, 0.32, 0.30, 0.03]
    assert len(shop["shop_odds"]) == 10


def test_rounds_page_gives_carousel_and_augment_rounds() -> None:
    rounds = parse_rounds(page("rounds.html"))
    assert rounds["stages"]["4"] == ["PvP", "PvP", "PvP", "Carousel", "PvP", "PvP", "Cho'Gath"]
    assert set(rounds["carousel_round"].values()) == {4}
    assert rounds["augment_rounds"] == ["2-1", "3-2", "4-2"]


def test_role_page_gives_mana_rules() -> None:
    roles = parse_roles(page("role.html"))
    assert len(roles) == 13
    assert "Gain Mana from taking damage." in roles["Magic Tank"]


def test_champion_refs_skip_unbuyable_units() -> None:
    champs = {c["api_name"]: c for c in parse_champions(page("reroll.html"))}
    assert champs["DA_18_Ahri"]["cost"] == 4
    assert champs["DA_18_Ahri"]["role"] == "APCaster"
    assert "DA_RabadonsDeathcap" in champs["DA_18_Ahri"]["recommend_items"]
    assert all(c["cost"] > 0 for c in champs.values())


def test_patch_notes_expose_set18_versions_and_system_changes() -> None:
    assert [p["version"] for p in parse_patch_list(page("patch-notes.html"))] == [
        "18.1", "18.1b", "18.1c", "18.1d", "18.2",
    ]
    assert parse_system_changes(page("patch-notes.html"))["SYSTEMS - XP PER LEVEL"][0] == (
        "Level 7 to Level 8: 60 ⇒ 56"
    )
    assert "SYSTEMS - SET MECHANIC: WISPS" in parse_system_changes(page("patch-notes-551.html"))


def test_changed_page_fails_loudly_instead_of_returning_empty_tables() -> None:
    with pytest.raises(LolchessError):
        parse_exp("<html><body><p>trang doi cau truc</p></body></html>")


class FakeResponse:
    def __init__(self, status: int, headers: dict[str, str]) -> None:
        self.status_code, self.headers, self.text = status, headers, ""


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.headers: dict[str, str] = {}
        self.response = response

    def get(self, *args, **kwargs) -> FakeResponse:
        return self.response


def test_waf_challenge_is_reported_not_bypassed() -> None:
    """lolchess chan client khong phai trinh duyet. Bao ro, KHONG gia User-Agent."""
    client = LolchessClient(FakeSession(FakeResponse(202, {"x-amzn-waf-action": "challenge"})))
    with pytest.raises(LolchessError, match="--from-dir"):
        client.get("/guide/exp")
    assert "Mozilla" not in client.session.headers["User-Agent"]


# --- 3. doi chieu cheo -----------------------------------------------------------------


def test_xp_table_is_corroborated_by_patch_notes(guide: dict) -> None:
    """Bang chung trang guide duoc cap nhat theo patch, khong phai so set cu."""
    latest = guide["patches"][-1]
    assert latest["version"] == guide["meta"]["latest_patch"]
    changes = " ".join(latest["systems"].get("SYSTEMS - XP PER LEVEL", []))
    assert f"⇒ {guide['economy']['xp_to_next']['7']}" in changes


def test_champion_costs_agree_with_cdragon(guide: dict) -> None:
    cdragon = json.loads((ROOT / "data" / "champion_costs.json").read_text(encoding="utf-8"))["costs"]
    lolchess = {c["api_name"]: c["cost"] for c in guide["champions"]}
    assert set(cdragon) <= set(lolchess)
    assert {k: lolchess[k] for k in cdragon} == cdragon

