"""Client & Parser TFT Academy Comps -> doi hinh meta cua Pro Players (Dishsoap & Frodan).

VI SAO DUNG DUOC TRUC TIEP
    TFT Academy cung cap REST API noi bo cong khai:
        GET https://tftacademy.com/api/tierlist/comps?set=18

    Payload JSON tra ve gom 53 doi hinh meta Set 18 hoan chinh voi:
      - title: ten chien thuat ("Malphite AP Flex", "Rengar & Tristana Reroll",...)
      - tier: S, A, B, C, X
      - finalComp: 8-9 tuong kem vi tri boardIndex va trang bi chuan core_items
      - augments: danh sach best_augments kem apiName (khac phuc hoan toan diem mu do Riot an augment)
      - earlyComp: tuong def dau tran va tuong cam do tam
      - tips: huong dan len cap, roll va positioning

PROVENANCE
    Bien soan boi: Dishsoap & Frodan (TFT Academy).
    Thuoc tinh sample_n = 0 (y kien chuyen gia).
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import requests

from .comp_database import MetaComp

TFTACADEMY_HOST = "https://tftacademy.com"
COMPS_API_URL = f"{TFTACADEMY_HOST}/api/tierlist/comps"
COMPS_PAGE_URL = f"{TFTACADEMY_HOST}/tierlist/comps"

USER_AGENT = "TFT-Agent-Thesis/0.1 (research build)"
DEFAULT_TIMEOUT_S = 12.0

# Placement dai dien theo bac cua TFT Academy (tuong tu ExpertTierListProvider)
TIER_PLACEMENT_MAP: dict[str, float] = {
    "S": 3.95,
    "A": 4.25,
    "B": 4.55,
    "C": 4.90,
    "X": 4.50,  # X = off-meta / situational
}


class TFTAcademyCompsError(RuntimeError):
    """Loi khi goi hoac parse du lieu doi hinh tu TFT Academy."""


class TFTAcademyCompsClient:
    """Client lay du lieu doi hinh meta tu TFT Academy."""

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> None:
        self.session = session or requests.Session()
        self.timeout_s = timeout_s

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
        }

    def get_comps(self, set_num: int = 18) -> dict[str, Any]:
        """Goi API lay danh sach doi hinh meta cua mot Set."""
        url = f"{COMPS_API_URL}?set={set_num}"
        try:
            resp = self.session.get(url, headers=self._headers(), timeout=self.timeout_s)
        except requests.RequestException as exc:
            raise TFTAcademyCompsError(f"Loi ket noi den {url}: {exc}") from exc

        if resp.status_code != 200:
            raise TFTAcademyCompsError(
                f"TFT Academy tra status {resp.status_code} tai {url}: {resp.text[:200]}"
            )

        try:
            return resp.json()
        except ValueError as exc:
            raise TFTAcademyCompsError(f"Phan hoi tu {url} khong phai JSON hop le") from exc


def _load_traits_map(cdragon_cache_path: Path | None = None) -> dict[str, list[str]]:
    """Tra cuu danh sach trait cua tung tuong tu cdragon_cache/en_us.json."""
    if not cdragon_cache_path:
        cdragon_cache_path = Path("data/cdragon_cache/en_us.json")
    if not cdragon_cache_path.exists():
        return {}

    try:
        data = json.loads(cdragon_cache_path.read_text(encoding="utf-8"))
        for block in data.get("setData") or []:
            if block.get("mutator") == "TFTSet18":
                return {
                    c.get("apiName"): [str(t) for t in c.get("traits", [])]
                    for c in block.get("champions", [])
                    if c.get("apiName")
                }
    except Exception:
        pass
    return {}


def parse_tftacademy_comps(
    payload: dict[str, Any],
    patch: str = "18.1d",
    traits_map: dict[str, list[str]] | None = None,
) -> list[MetaComp]:
    """Chuyen doi danh sach guides tu payload TFT Academy thanh list[MetaComp]."""
    guides = payload.get("guides")
    if guides is None or not isinstance(guides, list):
        raise TFTAcademyCompsError("Payload khong chua danh sach 'guides' hop le")

    if traits_map is None:
        traits_map = _load_traits_map()

    source = f"tftacademy:Dishsoap & Frodan/patch={patch}"
    out: list[MetaComp] = []

    for g in guides:
        if not isinstance(g, dict):
            continue

        name = str(g.get("title") or g.get("metaTitle") or g.get("compSlug") or "Unnamed Comp").strip()
        raw_tier = str(g.get("tier") or "B").strip().upper()
        tier = raw_tier if raw_tier in ("S", "A", "B", "C") else "B"

        # 1. Core units tu finalComp
        final_comp = g.get("finalComp") or []
        core_units: list[str] = []
        core_items_seen: set[str] = set()
        core_items: list[str] = []

        for champ_entry in final_comp:
            if not isinstance(champ_entry, dict):
                continue
            c_api = str(champ_entry.get("apiName", "")).strip()
            if c_api and c_api not in core_units:
                core_units.append(c_api)

            # Trang bi tren tuong core (carries / main tanks)
            for itm in champ_entry.get("items") or []:
                itm_str = str(itm).strip()
                if itm_str and itm_str not in core_items_seen:
                    core_items_seen.add(itm_str)
                    core_items.append(itm_str)

        # 2. Flex units tu maxCap va altBuilds
        flex_units: list[str] = []
        for extra_list in [g.get("maxCap") or [], g.get("altBuilds") or []]:
            for champ_entry in extra_list:
                if not isinstance(champ_entry, dict):
                    continue
                c_api = str(champ_entry.get("apiName", "")).strip()
                if c_api and c_api not in core_units and c_api not in flex_units:
                    flex_units.append(c_api)

        # 3. Best augments tu augments (chi lay cac loi active)
        best_augments: list[str] = []
        for aug in g.get("augments") or []:
            if isinstance(aug, dict):
                if not aug.get("disabled", False):
                    aug_api = str(aug.get("apiName", "")).strip()
                    if aug_api and aug_api not in best_augments:
                        best_augments.append(aug_api)
            elif isinstance(aug, str):
                aug_str = aug.strip()
                if aug_str and aug_str not in best_augments:
                    best_augments.append(aug_str)

        # 4. Early game units
        early_game: list[str] = []
        for champ_entry in g.get("earlyComp") or []:
            if isinstance(champ_entry, dict):
                c_api = str(champ_entry.get("apiName", "")).strip()
                if c_api and c_api not in early_game:
                    early_game.append(c_api)

        # 5. Tinh toan active traits tu core_units
        traits_count: dict[str, int] = {}
        for u in core_units:
            u_traits = traits_map.get(u, [])
            for t in u_traits:
                traits_count[t] = traits_count.get(t, 0) + 1

        # 6. Ghi chu van hanh
        tips_list = g.get("tips") or []
        tips_text = " · ".join(
            f"{t.get('stage')}: {t.get('tip')}" for t in tips_list if isinstance(t, dict) and t.get("tip")
        )
        augments_tip = str(g.get("augmentsTip") or "").strip()
        difficulty = str(g.get("difficulty") or "").strip()
        style = str(g.get("style") or "").strip()

        notes_parts: list[str] = []
        if style:
            notes_parts.append(f"Phong cách: {style}")
        if difficulty:
            notes_parts.append(f"Độ khó: {difficulty}")
        if augments_tip:
            notes_parts.append(f"Lõi: {augments_tip}")
        if tips_text:
            notes_parts.append(tips_text)
        positioning_notes = " | ".join(notes_parts)

        # 7. Level timing mac dinh tu style
        level_timing: dict[str, int] = {}
        if "Fast 8" in style or "4-Cost" in style:
            level_timing = {"8": 4}  # Vong 4-2 len 8
        elif "Fast 9" in style:
            level_timing = {"9": 5}
        elif "Reroll" in style:
            level_timing = {"6": 3, "7": 4}

        avg_place = TIER_PLACEMENT_MAP.get(tier, 4.50)

        comp = MetaComp(
            name=name,
            tier=tier,
            core_units=core_units,
            flex_units=flex_units,
            core_items=core_items,
            best_augments=best_augments,
            traits=traits_count,
            avg_placement=avg_place,
            top4_rate=0.60 if tier in ("S", "A") else 0.50,
            win_rate=0.18 if tier == "S" else (0.14 if tier == "A" else 0.10),
            play_rate=0.03,
            level_timing=level_timing,
            early_game=early_game,
            positioning_notes=positioning_notes,
            source=source,
            sample_n=0,
        )
        out.append(comp)

    return out


def build_meta_comps_payload(
    comps: list[MetaComp],
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dong goi list MetaComp thanh payload JSON dung format data/meta_comps.json."""
    full_meta = {
        "set": "TFTSet18",
        "provider": "tftacademy.com",
        "source": (meta or {}).get("source", "tftacademy:Dishsoap & Frodan"),
        "patch": (meta or {}).get("patch", "18.1d"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_comps": len(comps),
        "note": "Biên soạn bởi chuyên gia TFT Academy (Dishsoap & Frodan). Đầy đủ core_items, best_augments và early_game.",
    }
    return {
        "meta": full_meta,
        "comps": [c.to_dict() for c in comps],
    }
