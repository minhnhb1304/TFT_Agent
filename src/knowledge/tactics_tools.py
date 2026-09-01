"""Client tactics.tools -> doi hinh meta + stats unit/trait/item (SPEC 3.4).

VI SAO THEM NGUON NAY
    data/meta_comps.json hien do CHINH TA crawl tu tft-match-v1: 249 match,
    1988 participant, median sample_n = 25. Con so do that va truy nguoc duoc
    den tung match_id - do la diem manh - nhung no qua nho de noi bat cu dieu
    gi ve meta.

    tactics.tools tong hop cung mot thu tu hang trieu van (1.752.735 van o
    rankGroup "all", do 2026-09-01). Doi lai: KHONG cong bo phuong phap, va
    khong truy nguoc duoc den match_id nao. Hai nguon nay bu nhau chu khong
    thay the nhau - vi the crawl script ghi ra MOT FILE KHAC, khong de len
    file cua Riot. Xem docstring cua scripts/crawl_tactics_tools.py.

DIEU DA DO DUOC VE AUGMENT - va vi sao no quan trong
    Payload cua tactics.tools co san bon truong augment: `augmentSingles`,
    `aug1s`, `aug2s`, `aug3s`. Do 2026-09-01, ca bon RONG o moi rank group,
    ke ca rankGroup=3 voi 1,75 trieu van; trang /augments cua ho cung tra
    `{"singles": [], "pairs": [], "trios": []}`.

    Nghia la: viec khong lay duoc so lieu augment KHONG phai gioi han cua du
    an nay. Trang stats lon nhat cong khai cung khong co. Do la ket luan
    manh hon nhieu cho bao cao - va `augment_row_count()` duoi day ton tai
    de test khoa lai ket luan do, chu khong phai de "cho chac".

BAY DA BIET: HAI QUY UOC KHAC NHAU TRONG CUNG MOT API
    - /team-compositions : `top4` va `win` la SO DEM (int).
    - /stats2/general    : `top4` va `won` la PHAN TRAM 0..100 (float).

    Tron hai cai lai thi top4_rate ra 50.0 thay vi 0.5, va BaseScorer se coi
    moi thu la hoan hao. Chuyen doi nam gon o hai ham record duoi day, khong
    o cho nao khac.

KIEN TRUC: CRAWL OFFLINE, KHONG BAO GIO GOI LUC CHAY
    Giong RiotClient: TacticsToolsClient chi duoc scripts/crawl_tactics_tools.py
    dung. Runtime doc file da ket tinh. SPEC 3.5.3 - khong co gi cham mang
    nam tren duong quyet dinh 30 giay.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Iterable

import requests

# Endpoint cong khai, khong key, khong chu ky. Do 2026-09-01.
COMPS_HOST = "https://api.tft.tools"
STATS_HOST = "https://d3.tft.tools"

# Ranked TFT - cung queue voi RiotClient. Doi queue la doi meta.
RANKED_QUEUE_ID = 1100

# Ma patch cua tactics.tools cho Set 18 patch 18.1. Bundle cua ho khai bao
# danh sach patch la [16170] - dung MOT phan tu, tuc Set 18 chi moi co mot
# patch. Sang 18.2 con so nay se doi va PHAI cap nhat co y thuc, khong doan.
SET18_PATCH = 16170

# Ten -> ma rankGroup trong URL. Lay tu bundle cua tactics.tools.
RANK_GROUPS: dict[str, int] = {
    "top": 0,
    "high": 1,
    "plat": 2,
    "all": 3,
    "gm": 4,
}

USER_AGENT = "TFT-Agent-Thesis/0.1 (single-user research build)"

# Gian cach toi thieu giua hai request. Khong phai rate limit cua ho cong bo
# - ho khong cong bo cai nao - ma la muc lich su tu dat: mot dot crawl chi
# can 2-3 request tong cong.
MIN_INTERVAL_S = 1.0

# Duoi ti le nay thi coi unit/trait la khong dinh nghia doi hinh. Cung y
# tuong voi `trait_share` cua CompAggregator: khong loc thi mot doi hinh
# liet ke moi trait tung co ai bat mot lan.
DEFINING_SHARE = 0.5


class TacticsToolsError(RuntimeError):
    """Loi goi tactics.tools - luon fail sang, khong bao gio nuot."""


@dataclass
class TacticsToolsClient:
    """Doc hai endpoint cong khai cua tactics.tools.

    Khong co retry phuc tap: mot dot crawl la 2-3 request: hong thi chay lai
    ca lenh re hon nhieu so voi mot vong retry am tham lam mo nguyen nhan.
    """

    patch: int = SET18_PATCH
    queue_id: int = RANKED_QUEUE_ID
    timeout_s: float = 30.0
    _last_call: float = 0.0

    def _get(self, url: str) -> Any:
        wait = MIN_INTERVAL_S - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

        try:
            resp = requests.get(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                timeout=self.timeout_s,
            )
        except requests.RequestException as exc:
            raise TacticsToolsError(f"khong goi duoc {url}: {exc}") from exc

        if resp.status_code != 200:
            raise TacticsToolsError(f"{url} tra HTTP {resp.status_code}")
        try:
            return resp.json()
        except ValueError as exc:
            raise TacticsToolsError(f"{url} khong tra JSON: {exc}") from exc

    def team_compositions(self, rank_group: int) -> dict[str, Any]:
        return self._get(f"{COMPS_HOST}/team-compositions/{rank_group}/{self.patch}")

    def general_stats(self, rank_group: int) -> dict[str, Any]:
        return self._get(
            f"{STATS_HOST}/stats2/general/{self.queue_id}/{self.patch}/{rank_group}"
        )


def rank_group_code(name: str) -> int:
    """Ten rank group -> ma so trong URL. Ten la vi pham thi bao ngay."""
    try:
        return RANK_GROUPS[name]
    except KeyError:
        raise TacticsToolsError(
            f"rank group '{name}' khong ton tai. Cac gia tri hop le: "
            f"{', '.join(sorted(RANK_GROUPS))}"
        ) from None


def source_label(kind: str, rank_group: str, patch: int, count: int) -> str:
    """Provenance ghi vao tung ban ghi.

    Phai doc duoc tren overlay va trong bao cao. Co chu `tactics.tools` o dau
    la co y: nguoi doc phai thay ngay day KHONG phai so tu crawl duoc.
    """
    return f"tactics.tools:{kind}/{rank_group}/patch={patch}/n={count}"


# --- doi hinh --------------------------------------------------------------


def augment_row_count(comps_payload: dict[str, Any]) -> int:
    """Dem tong so ban ghi augment trong payload doi hinh.

    Tra 0 nghia la tactics.tools cung khong co so lieu augment - ket qua do
    duoc 2026-09-01. Ham nay ton tai de test khoa ket luan do lai: neu mot
    ngay nao do no khac 0, nghia la nguon augment da mo lai va
    data/augment_stats.csv co the thoi la MOCK-NOT-REAL.
    """
    keys = ("augmentSingles", "aug1s", "aug2s", "aug3s")
    total = 0
    for group in comps_payload.get("groups") or []:
        full = group.get("full") or {}
        for key in keys:
            total += len(full.get(key) or [])
    return total


def _defining(rows: Iterable[Any], group_count: int, share: float) -> list[tuple[str, int, int]]:
    """Loc `units`/`traits` cua mot group xuong con phan DINH NGHIA doi hinh.

    Ca hai truong deu la list `[id, tier_hoac_style, count, place]`.
    """
    out: list[tuple[str, int, int]] = []
    floor = group_count * share
    for row in rows:
        if not isinstance(row, list) or len(row) < 3:
            continue
        count = int(row[2])
        if count >= floor:
            out.append((str(row[0]), int(row[1]), count))
    return sorted(out, key=lambda r: (-r[2], r[0]))


def _modal_level(levels: Any) -> int:
    """Level pho bien nhat. `levels` la list `[level, ?, count]`."""
    best_level, best_count = 8, -1
    for row in levels or []:
        if isinstance(row, list) and len(row) >= 3 and int(row[2]) > best_count:
            best_level, best_count = int(row[0]), int(row[2])
    return best_level


def comp_records(
    payload: dict[str, Any],
    source: str,
    min_sample_n: int = 200,
    n_core: int = 4,
    n_flex: int = 4,
    n_items: int = 3,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Payload /team-compositions -> ban ghi dung SCHEMA MetaComp.

    Them mot key la se TypeError luc CompDatabase.load() - do la y muon: hai
    nguon (Riot va tactics.tools) phai do CUNG mot khuon, neu khong thi
    comp_selector se phai biet du lieu den tu dau.

    `min_sample_n` mac dinh 200 - bang nguong MetaComp.is_evidence. Nguon nay
    co hang trieu van nen loc chat duoc, khac han nguon Riot (mac dinh 20).
    """
    groups = payload.get("groups") or []
    total = max(1, int(payload.get("count") or 0))

    eligible = []
    for group in groups:
        full = group.get("full") or {}
        count = int(full.get("count") or 0)
        if count >= min_sample_n:
            eligible.append(full)
    eligible.sort(key=lambda f: (float(f.get("place") or 9.0), -int(f.get("count") or 0)))
    eligible = eligible[:limit]

    records: list[dict[str, Any]] = []
    for rank, full in enumerate(eligible):
        count = int(full["count"])
        units = _defining(full.get("units") or [], count, DEFINING_SHARE)
        traits = _defining(full.get("traits") or [], count, DEFINING_SHARE)

        # `carryUnits` la [unitId, trong so] da xep san theo do quan trong.
        carries = [str(c[0]) for c in (full.get("carryUnits") or []) if isinstance(c, list) and c]
        # `generalItems` la [itemId, count, place, top4, won].
        items = [
            str(i[0])
            for i in (full.get("generalItems") or [])
            if isinstance(i, list) and i
        ]

        unit_ids = [u[0] for u in units]
        # Carry di truoc: doi hinh duoc nhan dien boi carry chu khong boi unit
        # dong nhat. Phan con lai giu thu tu theo do pho bien.
        core = carries[:n_core] + [u for u in unit_ids if u not in carries]
        core = core[:n_core]
        flex = [u for u in unit_ids if u not in core][:n_flex]

        tier = "S" if rank < 2 else "A" if rank < 5 else "B" if rank < 9 else "C"
        top4 = int(full.get("top4") or 0)
        win = int(full.get("win") or 0)
        main_trait = traits[0][0] if traits else "?"
        name = f"{carries[0]} / {main_trait}" if carries else f"{main_trait} Core"

        records.append(
            {
                "name": name,
                "tier": tier,
                "core_units": core,
                "flex_units": flex,
                "core_items": items[:n_items],
                # Bon truong augment cua ho deu rong - xem augment_row_count().
                # De rong thay vi doan, dung nhu nguon Riot.
                "best_augments": [],
                "traits": {t[0]: t[1] for t in traits},
                "avg_placement": round(float(full.get("place") or 4.5), 3),
                # Dem -> ti le. Endpoint kia dung phan tram; xem docstring module.
                "top4_rate": round(top4 / count, 4),
                "win_rate": round(win / count, 4),
                "play_rate": round(count / total, 4),
                "level_timing": {str(_modal_level(full.get("levels"))): 5},
                "early_game": [],
                "positioning_notes": (
                    f"Tong hop boi tactics.tools tu {count} van. Ho KHONG cong bo "
                    "phuong phap nhom doi hinh va khong truy nguoc duoc den match_id "
                    "- khac voi nguon Riot tu crawl. Doc so nay nhu so cua ben thu ba."
                ),
                "source": source,
                "sample_n": count,
            }
        )
    return records


# --- stats unit / trait / item --------------------------------------------


def _pct(value: Any) -> float:
    """Phan tram 0..100 -> ti le 0..1. Xem bay o docstring module."""
    return round(float(value or 0.0) / 100.0, 4)


def general_records(payload: dict[str, Any], source: str) -> dict[str, Any]:
    """Payload /stats2/general -> ban ghi phang, da chuan hoa ti le.

    CHUA duoc noi vao scoring engine. Day la du lieu tho de item_advisor va
    board_fit dung sau nay; noi vao bay gio la them mot duong anh huong khong
    ai do duoc trong ablation study (SPEC 12.4).
    """
    units = [
        {
            "api_name": api_name,
            "count": int(row.get("count") or 0),
            "avg_place": float(row.get("place") or 0.0),
            "top4_rate": _pct(row.get("top4")),
            "win_rate": _pct(row.get("won")),
            "top_items": [str(i) for i in (row.get("topItems") or [])],
            "source": source,
        }
        for api_name, row in sorted((payload.get("units") or {}).items())
    ]
    traits = [
        {
            "api_name": api_name,
            "count": int(row.get("count") or 0),
            "avg_place": float(row.get("place") or 0.0),
            "top4_rate": _pct(row.get("top4")),
            "win_rate": _pct(row.get("won")),
            "source": source,
        }
        for api_name, row in sorted((payload.get("traits") or {}).items())
    ]
    items = [
        {
            "api_name": str(row.get("itemId") or ""),
            "count": int(row.get("count") or 0),
            "avg_place": float(row.get("place") or 0.0),
            "top4_rate": _pct(row.get("top4")),
            "win_rate": _pct(row.get("won")),
            "source": source,
        }
        for row in sorted(
            payload.get("items") or [], key=lambda r: str(r.get("itemId") or "")
        )
    ]
    return {
        "total_entries": int(payload.get("totalEntries") or 0),
        "last_updated": int(payload.get("lastUpdated") or 0),
        "units": units,
        "traits": traits,
        "items": items,
    }
