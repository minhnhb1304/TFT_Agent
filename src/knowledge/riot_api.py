"""Client tft-match-v1 + tong hop stats augment - SPEC 3.4.2, feedback #5.

VI SAO NGUON NAY LA NGUON TOT NHAT CHO DO AN
    Moi nguon khac deu la hop den: OP.GG MCP vuong ToS va khong kiem chung
    duoc cach ho tinh; cac trang stats khong cong bo co mau. Tu crawl
    tft-match-v1 thi moi con so trong bao cao deu truy nguoc duoc den mot
    tap match_id cu the, va hoi dong hoi "so nay o dau ra" thi tra loi duoc.

KIEN TRUC: CRAWL OFFLINE, KHONG BAO GIO GOI API LUC CHAY
    RiotClient chi duoc scripts/crawl_augment_stats.py dung. Ket qua ket
    tinh thanh data/augment_stats.csv, va runtime doc CSV do qua CsvProvider.
    LLM va HTTP deu KHONG duoc nam tren duong quyet dinh co han gio
    (SPEC 3.5.3) - augment chi co ~30 giay de chon.

HAI CAI BAY DA BIET
    1. `info` cua TFT match-v1 dung snake_case (`queue_id`, `tft_set_number`)
       chu khong phai camelCase nhu phan con lai cua Riot API. Doc ca hai de
       chac.
    2. `tft_set_number` PHAI duoc loc. Match cua set truoc van nam trong
       lich su cua nguoi choi, va augment cua set cu se lam ban stats.

RATE LIMIT
    Personal key: 20 request / 1 giay va 100 request / 2 phut. Gioi han 2
    phut moi la cai that su chan - no cho trung binh 0.83 req/s. Client tu
    dieu tiet theo ca hai cua so va ton trong header Retry-After khi dinh
    429; khong bao gio spam lai.

    Personal key HET HAN SAU 24 GIO. Dinh 401 nghia la key het han, khong
    phai sai code - va thong bao loi phai noi ro dieu do.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Iterator

import requests

# Ranked TFT. Match thuong/hyper roll/double up co queue khac va meta khac,
# tron vao thi so lieu mat y nghia.
RANKED_TFT_QUEUE_ID = 1100

TARGET_SET_NUMBER = 18

USER_AGENT = "TFT-Agent-Thesis/0.1 (single-user research build)"

# platform host -> regional host cho match-v1. VN2 thuoc cum SEA.
REGIONAL_OF_PLATFORM = {
    "vn2": "sea",
    "sg2": "sea",
    "th2": "sea",
    "tw2": "sea",
    "ph2": "sea",
    "oc1": "sea",
    "kr": "asia",
    "jp1": "asia",
    "na1": "americas",
    "br1": "americas",
    "la1": "americas",
    "la2": "americas",
    "euw1": "europe",
    "eun1": "europe",
    "tr1": "europe",
    "ru": "europe",
}

APEX_TIERS = ("challenger", "grandmaster", "master")

# Cho ngan hon nguong nay thi coi nhu khong phai cho.
#
# Khong phai vi toi uu ma vi DUNG DAN: phep tru dau cham dong sinh ra nhung
# khoang cho kieu 1.1e-16 giay. Ngu tung do khong lam dong ho nhich duoc,
# nen vong lap tinh lai y het va quay mai o 100% CPU. Do la mot livelock
# that, da bat duoc bang test.
#
# Bo qua mot khoang cho 1 ms la an toan: gioi han that do bang giay, va bien
# an toan 10% o `safety` da nuot phan sai so nay tu lau.
MIN_SLEEP_S = 0.001


class RiotApiError(RuntimeError):
    """Loi goi Riot API - luon fail sang, khong bao gio nuot."""


class RiotAuthError(RiotApiError):
    """401/403 - gan nhu luon la Personal Key da het han (24 gio)."""


@dataclass
class RateLimiter:
    """Dieu tiet theo HAI cua so truot cung luc.

    Gioi han 100 req / 120 s moi la cai that su chan (0.83 req/s trung binh),
    khong phai gioi han 20 req/s. Giu dau thoi gian cua moi request roi ngu
    vua du de ca hai cua so deu hop le.
    """

    per_second: int = 20
    per_two_minutes: int = 100
    # Chua an het han muc - dinh 429 ton nhieu thoi gian hon la di cham.
    safety: float = 0.90
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic

    _stamps: list[float] = field(default_factory=list)

    def acquire(self) -> None:
        while True:
            now = self.clock()
            self._stamps = [t for t in self._stamps if now - t < 120.0]

            waits = []
            recent = [t for t in self._stamps if now - t < 1.0]
            if len(recent) >= int(self.per_second * self.safety):
                waits.append(1.0 - (now - min(recent)))
            if len(self._stamps) >= int(self.per_two_minutes * self.safety):
                waits.append(120.0 - (now - min(self._stamps)))

            # Loc theo MIN_SLEEP_S chu khong phai > 0: xem chu thich o hang so.
            delay = max([w for w in waits if w > MIN_SLEEP_S], default=0.0)
            if delay <= 0:
                self._stamps.append(now)
                return
            self.sleep(delay)


@dataclass
class RiotClient:
    """Doc tft-league-v1 va tft-match-v1. CHI DOC - khong endpoint ghi nao.

    Args:
        api_key: Personal Key. Het han sau 24 gio.
        platform: host theo server, VD "vn2" cho DTCL Viet Nam.
        regional: host theo cum cho match-v1. Suy ra tu platform neu bo trong.
    """

    api_key: str
    platform: str = "vn2"
    regional: str | None = None
    timeout: int = 20
    limiter: RateLimiter = field(default_factory=RateLimiter)
    session: Any = None

    def __post_init__(self) -> None:
        self.platform = self.platform.lower()
        if self.regional is None:
            self.regional = REGIONAL_OF_PLATFORM.get(self.platform)
            if self.regional is None:
                raise RiotApiError(
                    f"khong biet regional host cho platform {self.platform!r}. "
                    f"Truyen regional= thang, hoac chon trong {sorted(REGIONAL_OF_PLATFORM)}."
                )
        if self.session is None:
            self.session = requests.Session()

    # -- tang HTTP ---------------------------------------------------------

    def _get(self, host: str, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"https://{host}.api.riotgames.com{path}"
        for attempt in range(4):
            self.limiter.acquire()
            resp = self.session.get(
                url,
                headers={"X-Riot-Token": self.api_key, "User-Agent": USER_AGENT},
                params=params,
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                return resp.json()

            if resp.status_code in (401, 403):
                raise RiotAuthError(
                    f"HTTP {resp.status_code} tu {path}. Personal Key het han sau 24 gio - "
                    "vao https://developer.riotgames.com/ lay key moi roi cap nhat .env."
                )
            if resp.status_code == 429:
                # Ton trong Retry-After. Dung doan, dung spam.
                wait = float(resp.headers.get("Retry-After", "10"))
                self.limiter.sleep(wait + 1.0)
                continue
            if resp.status_code >= 500 and attempt < 3:
                self.limiter.sleep(2.0 * (attempt + 1))
                continue

            raise RiotApiError(f"HTTP {resp.status_code} tu {url}: {resp.text[:200]}")

        raise RiotApiError(f"het luot thu lai cho {url}")

    # -- endpoint ----------------------------------------------------------

    def apex_league(self, tier: str) -> dict[str, Any]:
        """challenger / grandmaster / master cua queue RANKED_TFT."""
        if tier not in APEX_TIERS:
            raise RiotApiError(f"tier phai thuoc {APEX_TIERS}, nhan {tier!r}")
        return self._get(self.platform, f"/tft/league/v1/{tier}")

    def apex_puuids(self, tiers: Iterable[str] = APEX_TIERS) -> list[str]:
        """PUUID cua toan bo nguoi choi hang cao.

        Doc thang `puuid` tu league entry. `summonerId` da bi Riot go dan tu
        2025 - khong xay duong di nao qua no nua.
        """
        seen: list[str] = []
        known: set[str] = set()
        for tier in tiers:
            for entry in self.apex_league(tier).get("entries", []):
                puuid = entry.get("puuid")
                if puuid and puuid not in known:
                    known.add(puuid)
                    seen.append(puuid)
        return seen

    def match_ids(self, puuid: str, count: int = 20) -> list[str]:
        return self._get(
            self.regional or "",
            f"/tft/match/v1/matches/by-puuid/{puuid}/ids",
            {"count": max(1, min(count, 200))},
        )

    def match(self, match_id: str) -> dict[str, Any]:
        return self._get(self.regional or "", f"/tft/match/v1/matches/{match_id}")


# -- tang tong hop (thuan, khong mang) -------------------------------------


def match_info(match: dict[str, Any]) -> dict[str, Any]:
    return match.get("info") or {}


def _field(info: dict[str, Any], snake: str, camel: str) -> Any:
    """Doc mot truong co the o snake_case hoac camelCase.

    `info` cua TFT match-v1 dung snake_case (`queue_id`, `tft_set_number`),
    nguoc voi phan con lai cua Riot API. Doc ca hai de khong phu thuoc vao
    viec Riot co chuan hoa lai hay khong.
    """
    value = info.get(snake)
    return info.get(camel) if value is None else value


def is_usable_match(
    match: dict[str, Any],
    set_number: int = TARGET_SET_NUMBER,
    queue_id: int | None = RANKED_TFT_QUEUE_ID,
) -> bool:
    """Match co duoc tinh vao stats khong.

    Loc `tft_set_number` la BAT BUOC: lich su nguoi choi con match cua set
    truoc, va augment set cu se lam ban so lieu mot cach im lang.
    """
    info = match_info(match)
    if int(_field(info, "tft_set_number", "tftSetNumber") or 0) != set_number:
        return False
    if queue_id is not None:
        if int(_field(info, "queue_id", "queueId") or 0) != queue_id:
            return False
    return bool(info.get("participants"))


@dataclass
class AugmentTally:
    """Bo dem tho cho mot augment."""

    n: int = 0
    placement_sum: int = 0
    top4: int = 0
    wins: int = 0

    @property
    def avg_place(self) -> float:
        return self.placement_sum / self.n if self.n else 0.0

    @property
    def top4_rate(self) -> float:
        return self.top4 / self.n if self.n else 0.0

    @property
    def win_rate(self) -> float:
        return self.wins / self.n if self.n else 0.0


class AugmentAggregator:
    """Dem placement theo augment. Thuan, khong cham mang - test duoc offline.

    Mot participant dong gop MOT quan sat cho MOI augment ho cam. Do la cach
    moi trang stats TFT tinh, va can noi ro trong bao cao: day la ti le
    placement TRUNG BINH CO DIEU KIEN khi cam augment do, KHONG phai hieu
    ung nhan qua cua augment. Augment manh va nguoi choi gioi tuong quan
    voi nhau.
    """

    def __init__(self) -> None:
        self.tallies: dict[str, AugmentTally] = defaultdict(AugmentTally)
        self.matches_seen = 0
        self.matches_used = 0
        self.participants = 0
        self.match_ids: list[str] = []

    def add_match(self, match: dict[str, Any], **kwargs: Any) -> bool:
        self.matches_seen += 1
        if not is_usable_match(match, **kwargs):
            return False

        info = match_info(match)
        for p in info.get("participants", []):
            placement = int(p.get("placement") or 0)
            if not 1 <= placement <= 8:
                continue
            self.participants += 1
            for api_name in p.get("augments") or []:
                t = self.tallies[str(api_name)]
                t.n += 1
                t.placement_sum += placement
                t.top4 += 1 if placement <= 4 else 0
                t.wins += 1 if placement == 1 else 0

        self.matches_used += 1
        match_id = (match.get("metadata") or {}).get("match_id")
        if match_id:
            self.match_ids.append(str(match_id))
        return True

    def add_matches(self, matches: Iterable[dict[str, Any]], **kwargs: Any) -> None:
        for m in matches:
            self.add_match(m, **kwargs)

    def rows(self, source: str, min_sample_n: int = 1) -> Iterator[dict[str, Any]]:
        """Dong CSV theo dung hop dong cua CsvProvider, sap xep theo apiName."""
        for api_name, t in sorted(self.tallies.items()):
            if t.n < min_sample_n:
                continue
            yield {
                "api_name": api_name,
                "avg_place": f"{t.avg_place:.3f}",
                "top4_rate": f"{t.top4_rate:.4f}",
                "win_rate": f"{t.win_rate:.4f}",
                "sample_n": t.n,
                "source": source,
            }

    def summary(self) -> dict[str, Any]:
        counts = [t.n for t in self.tallies.values()]
        return {
            "matches_seen": self.matches_seen,
            "matches_used": self.matches_used,
            "participants": self.participants,
            "augments": len(self.tallies),
            "min_sample_n": min(counts) if counts else 0,
            "max_sample_n": max(counts) if counts else 0,
            "median_sample_n": sorted(counts)[len(counts) // 2] if counts else 0,
        }


# -- Tong hop doi hinh -----------------------------------------------------
#
# VI SAO LOP NAY TON TAI BEN CANH AugmentAggregator
#
# Do 2026-09-01 tren vn2, Set 18 (3 match, 24 participant): participant cua
# tft-match-v1 KHONG con truong `augments`, va toan bo payload khong chua
# chuoi "augment" nao. Cac truong con lai:
#
#     companion, gold_left, last_round, level, missions, placement,
#     players_eliminated, puuid, riotIdGameName, riotIdTagline,
#     time_eliminated, total_damage_to_players, traits, units, win
#
# Nghia la Riot API KHONG cap duoc so lieu augment cho Set 18 - nhung `units`,
# `traits` va `placement` thi VAN CO. Doi hinh meta vi the crawl duoc that,
# va do la thu thay the duoc data/meta_comps.json gia lap.
#
# AugmentAggregator duoc GIU LAI: no dung, co test, va se chay ngay khi Riot
# tra truong `augments` ve.


# Style cua trait: 0 = khong kich hoat. Chi dem trait dang thuc su bat.
TRAIT_ACTIVE_MIN_STYLE = 1


def active_traits(participant: dict[str, Any]) -> dict[str, int]:
    """Trait dang bat cua mot nguoi choi -> so unit dong gop.

    `style` = 0 nghia la co unit mang trait do nhung chua du nguong kich hoat.
    Dem ca nhung trait do se lam moi doi hinh trong giong nhau.
    """
    out: dict[str, int] = {}
    for t in participant.get("traits") or []:
        if int(t.get("style") or 0) >= TRAIT_ACTIVE_MIN_STYLE:
            out[str(t.get("name"))] = int(t.get("num_units") or 0)
    return out


def main_trait(participant: dict[str, Any]) -> str | None:
    """Trait dinh danh doi hinh: bat o bac cao nhat, hoa thi nhieu unit hon.

    Day la mot phep XAP XI va phai noi ro trong bao cao: doi hinh that duoc
    dinh nghia boi carry va item chu khong chi boi trait. Nhung trait la tin
    hieu on dinh duy nhat co san trong du lieu, va no du de nhom cac van dau
    giong nhau lai voi nhau.
    """
    active = [
        t
        for t in (participant.get("traits") or [])
        if int(t.get("style") or 0) >= TRAIT_ACTIVE_MIN_STYLE
    ]
    if not active:
        return None
    best = max(
        active,
        key=lambda t: (
            int(t.get("style") or 0),
            int(t.get("num_units") or 0),
            str(t.get("name")),
        ),
    )
    return str(best.get("name"))


@dataclass
class CompTally:
    """Bo dem cho mot doi hinh, dinh danh boi trait chinh."""

    trait: str
    n: int = 0
    placement_sum: int = 0
    top4: int = 0
    wins: int = 0
    units: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    items: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    # So unit tieu bieu cua moi trait (lay max qua cac van).
    traits: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    # BAO NHIEU van co trait do bat. Can rieng bo dem nay vi `traits` mot minh
    # khong phan biet duoc "trait dinh nghia doi hinh" voi "mot nguoi tinh co
    # bat no mot lan" - va gop het lai thi mot doi hinh liet ke 17 trait.
    trait_seen: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    levels: list[int] = field(default_factory=list)

    @property
    def avg_placement(self) -> float:
        return self.placement_sum / self.n if self.n else 0.0

    @property
    def top4_rate(self) -> float:
        return self.top4 / self.n if self.n else 0.0

    @property
    def win_rate(self) -> float:
        return self.wins / self.n if self.n else 0.0


class CompAggregator:
    """Nhom participant thanh doi hinh theo trait chinh, roi tinh thong ke.

    Moi participant la MOT quan sat. `play_rate` tinh tren tong so participant
    chu khong tren so match - mot lobby 8 nguoi cho 8 quan sat.
    """

    def __init__(self) -> None:
        self.comps: dict[str, CompTally] = {}
        self.matches_seen = 0
        self.matches_used = 0
        self.participants = 0
        self.match_ids: list[str] = []

    def add_match(self, match: dict[str, Any], **kwargs: Any) -> bool:
        self.matches_seen += 1
        if not is_usable_match(match, **kwargs):
            return False

        for p in match_info(match).get("participants", []):
            placement = int(p.get("placement") or 0)
            trait = main_trait(p)
            if not 1 <= placement <= 8 or not trait:
                continue

            self.participants += 1
            tally = self.comps.setdefault(trait, CompTally(trait))
            tally.n += 1
            tally.placement_sum += placement
            tally.top4 += 1 if placement <= 4 else 0
            tally.wins += 1 if placement == 1 else 0
            tally.levels.append(int(p.get("level") or 0))

            for name, num in active_traits(p).items():
                tally.traits[name] = max(tally.traits[name], num)
                tally.trait_seen[name] += 1
            for unit in p.get("units") or []:
                tally.units[str(unit.get("character_id"))] += 1
                for item in unit.get("itemNames") or []:
                    tally.items[str(item)] += 1

        self.matches_used += 1
        match_id = (match.get("metadata") or {}).get("match_id")
        if match_id:
            self.match_ids.append(str(match_id))
        return True

    def comp_records(
        self,
        source: str,
        min_sample_n: int = 20,
        n_core: int = 4,
        n_flex: int = 4,
        n_items: int = 3,
        limit: int = 12,
        trait_share: float = 0.5,
    ) -> list[dict[str, Any]]:
        """Ban ghi dung SCHEMA MetaComp. Them mot key la se TypeError luc nap."""
        eligible = sorted(
            (c for c in self.comps.values() if c.n >= min_sample_n),
            key=lambda c: (c.avg_placement, -c.n),
        )[:limit]

        total = max(1, self.participants)
        records: list[dict[str, Any]] = []
        for rank, comp in enumerate(eligible):
            units = [u for u, _ in sorted(comp.units.items(), key=lambda kv: (-kv[1], kv[0]))]
            items = sorted(comp.items.items(), key=lambda kv: (-kv[1], kv[0]))
            avg_level = round(sum(comp.levels) / len(comp.levels)) if comp.levels else 8
            tier = "S" if rank < 2 else "A" if rank < 5 else "B" if rank < 9 else "C"

            # Chi giu trait DINH NGHIA doi hinh: xuat hien o it nhat mot nua so
            # van cua doi hinh do. Khong loc thi mot doi hinh liet ke 17 trait
            # - tuc la moi trait ai do tung bat mot lan - va so do vo nghia.
            defining_traits = {
                name: comp.traits[name]
                for name, seen in sorted(comp.trait_seen.items())
                if seen >= comp.n * trait_share
            }

            records.append(
                {
                    "name": f"{comp.trait} Core",
                    "tier": tier,
                    "core_units": units[:n_core],
                    "flex_units": units[n_core : n_core + n_flex],
                    "core_items": [i for i, _ in items[:n_items]],
                    # Riot khong cap augment o Set 18 -> khong do duoc. De rong
                    # thay vi doan: CompSelector coi day la khong co tin hieu,
                    # dung hon la mot danh sach bia.
                    "best_augments": [],
                    "traits": defining_traits,
                    "avg_placement": round(comp.avg_placement, 3),
                    "top4_rate": round(comp.top4_rate, 4),
                    "win_rate": round(comp.win_rate, 4),
                    "play_rate": round(comp.n / total, 4),
                    "level_timing": {str(avg_level): 5},
                    "early_game": [],
                    "positioning_notes": (
                        f"Do tu {comp.n} van hang cao. Trait chinh: {comp.trait}. "
                        "Doi hinh nhom theo trait bat o bac cao nhat - mot xap xi, "
                        "khong phai dinh nghia doi hinh cua nguoi choi."
                    ),
                    "source": source,
                    "sample_n": comp.n,
                }
            )
        return records

    def summary(self) -> dict[str, Any]:
        counts = [c.n for c in self.comps.values()]
        return {
            "matches_seen": self.matches_seen,
            "matches_used": self.matches_used,
            "participants": self.participants,
            "comps": len(self.comps),
            "max_sample_n": max(counts) if counts else 0,
            "median_sample_n": sorted(counts)[len(counts) // 2] if counts else 0,
        }
