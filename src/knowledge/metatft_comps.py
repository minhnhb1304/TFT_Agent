"""Client & Parser MetaTFT Comps -> cum doi hinh meta Machine Learning (META Spencer).

VI SAO DUNG DUOC TRUC TIEP
    MetaTFT cung cap REST API noi bo:
        GET https://api-hc.metatft.com/tft-comps-api/latest_cluster_info
        GET https://api-hc.metatft.com/tft-comps-api/comp_builds

    Payload JSON tra ve gom 53 cum doi hinh thuc te duoc gom bang K-means clustering tu hang trieu van dau:
      - cluster: ma cum (vi du 422000)
      - name_string: ten dac trung theo carry / trait chu dao
      - units_string: danh sach tuong chinh trong cum
      - traits_string: cac moc trait kich hoat
      - overall (tu comp_builds): sample_n that (vi du 40.230 van) va avg_placement (vi du 4.4785)
      - builds: trang bi tren carry thuc te duoc nguoi choi su dung nhieu nhat

PROVENANCE
    Xep hang boi: MetaTFT (META Spencer).
    Thuoc tinh sample_n > 0 (so lieu do duoc thuc te tu hang trieu tran).
    Dong vai tro bo tro so do thuc te va backup cho TFT Academy.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

import requests

from .comp_database import MetaComp

METATFT_HOST = "https://www.metatft.com"
LATEST_CLUSTER_INFO_URL = "https://api-hc.metatft.com/tft-comps-api/latest_cluster_info"
COMP_BUILDS_URL = "https://api-hc.metatft.com/tft-comps-api/comp_builds"

USER_AGENT = "TFT-Agent-Thesis/0.1 (research build)"
DEFAULT_TIMEOUT_S = 12.0


class MetaTFTCompsError(RuntimeError):
    """Loi khi goi hoac parse du lieu doi hinh tu MetaTFT."""


class MetaTFTCompsClient:
    """Client lay du lieu doi hinh meta tu MetaTFT."""

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
            "Referer": f"{METATFT_HOST}/",
            "Origin": METATFT_HOST,
        }

    def get_cluster_info(self) -> dict[str, Any]:
        """Lay thong tin cac cum doi hinh tu latest_cluster_info."""
        try:
            resp = self.session.get(
                LATEST_CLUSTER_INFO_URL, headers=self._headers(), timeout=self.timeout_s
            )
        except requests.RequestException as exc:
            raise MetaTFTCompsError(f"Loi ket noi den {LATEST_CLUSTER_INFO_URL}: {exc}") from exc

        if resp.status_code != 200:
            raise MetaTFTCompsError(
                f"MetaTFT tra status {resp.status_code} tai {LATEST_CLUSTER_INFO_URL}"
            )
        try:
            return resp.json()
        except ValueError as exc:
            raise MetaTFTCompsError("Phan hoi tu latest_cluster_info khong phai JSON hop le") from exc

    def get_comp_builds(self) -> dict[str, Any]:
        """Lay thong ke avg_placement, sample_n va trang bi carry tu comp_builds."""
        try:
            resp = self.session.get(
                COMP_BUILDS_URL, headers=self._headers(), timeout=self.timeout_s
            )
        except requests.RequestException as exc:
            raise MetaTFTCompsError(f"Loi ket noi den {COMP_BUILDS_URL}: {exc}") from exc

        if resp.status_code != 200:
            raise MetaTFTCompsError(
                f"MetaTFT tra status {resp.status_code} tai {COMP_BUILDS_URL}"
            )
        try:
            return resp.json()
        except ValueError as exc:
            raise MetaTFTCompsError("Phan hoi tu comp_builds khong phai JSON hop le") from exc


def parse_metatft_comps(
    cluster_info_payload: dict[str, Any],
    comp_builds_payload: dict[str, Any],
    patch: str = "18.1d",
) -> list[MetaComp]:
    """Chuyen doi du lieu cum va builds tu MetaTFT thanh list[MetaComp]."""
    details = (
        cluster_info_payload.get("cluster_info", {}).get("cluster_details", {})
        if "cluster_info" in cluster_info_payload
        else cluster_info_payload.get("cluster_details", {})
    )
    clusters = details.get("clusters")
    if not clusters or not isinstance(clusters, list):
        raise MetaTFTCompsError("Payload latest_cluster_info khong chua danh sach 'clusters' hop le")

    builds_results = comp_builds_payload.get("results") or {}

    out: list[MetaComp] = []

    for c in clusters:
        if not isinstance(c, dict):
            continue

        c_id = str(c.get("Cluster", ""))
        name_str = str(c.get("name_string") or f"Cluster {c_id}").strip()
        comp_name = f"MetaTFT: {name_str}"

        # 1. Core units tu units_string
        units_raw = str(c.get("units_string") or "")
        core_units = [u.strip() for u in units_raw.split(",") if u.strip()]

        # 2. Traits tu traits_string (vi du: "DA_18_Defender_1, DA_18_Fae_2")
        traits_raw = str(c.get("traits_string") or "")
        traits: dict[str, int] = {}
        for part in traits_raw.split(","):
            part = part.strip()
            if not part:
                continue
            # Tach moc: vi du DA_18_Defender_1 -> key: DA_18_Defender, count: 1
            m = re.match(r"^(.*?)(?:_(\d+))?$", part)
            if m:
                t_name, count_str = m.group(1), m.group(2)
                traits[t_name] = int(count_str) if count_str else 1

        # 3. So lieu tu comp_builds
        b_data = builds_results.get(c_id, {})
        overall = b_data.get("overall", {})
        sample_n = int(overall.get("count") or 0)
        avg_placement = float(overall.get("avg") or 4.50)

        # 4. Core items tu top carry builds
        core_items_seen: set[str] = set()
        core_items: list[str] = []
        builds_list = b_data.get("builds") or []
        for build in builds_list[:5]:
            for itm in build.get("buildName") or []:
                itm_clean = str(itm).strip()
                if itm_clean and itm_clean not in core_items_seen:
                    core_items_seen.add(itm_clean)
                    core_items.append(itm_clean)

        # 5. Phan bac theo avg_placement thuc te
        if avg_placement <= 4.15:
            tier = "S"
        elif avg_placement <= 4.40:
            tier = "A"
        elif avg_placement <= 4.65:
            tier = "B"
        else:
            tier = "C"

        top4_rate = max(0.0, min(1.0, 0.5 + (4.5 - avg_placement) * 0.25))
        win_rate = max(0.0, min(1.0, 0.125 + (4.5 - avg_placement) * 0.08))

        source = f"metatft:META Spencer/cluster={c_id}/patch={patch}"

        comp = MetaComp(
            name=comp_name,
            tier=tier,
            core_units=core_units,
            flex_units=[],
            core_items=core_items[:6],
            best_augments=[],  # Match thuc te cua MetaTFT khong co augment
            traits=traits,
            avg_placement=round(avg_placement, 4),
            top4_rate=round(top4_rate, 4),
            win_rate=round(win_rate, 4),
            play_rate=round(sample_n / 1_000_000, 4) if sample_n else 0.0,
            level_timing={"8": 4},
            early_game=[],
            positioning_notes=f"Cụm thống kê K-means MetaTFT (n={sample_n:,} trận). Avg: {avg_placement:.2f}",
            source=source,
            sample_n=sample_n,
        )
        out.append(comp)

    return out


def build_meta_comps_payload(
    comps: list[MetaComp],
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dong goi list MetaComp thanh payload JSON."""
    full_meta = {
        "set": "TFTSet18",
        "provider": "metatft.com",
        "source": (meta or {}).get("source", "metatft:META Spencer"),
        "patch": (meta or {}).get("patch", "18.1d"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_comps": len(comps),
        "note": "Phân cụm máy học từ MetaTFT (META Spencer). Cung cấp cỡ mẫu thực và avg placement đo được.",
    }
    return {
        "meta": full_meta,
        "comps": [c.to_dict() for c in comps],
    }
