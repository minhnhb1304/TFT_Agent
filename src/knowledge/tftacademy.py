"""Client TFT Academy -> bang tier augment cua pro players (SPEC 3.4, Nhiem vu 1).

VI SAO DUNG DUOC TRUC TIEP
    TFT Academy cung cap REST API noi bo cong khai:
        GET https://tftacademy.com/api/tierlist/augments?set=18

    Payload JSON tra ve gom 12 bang tier:
      - 3 tier lõi: 1 (Silver), 2 (Gold), 3 (Prismatic).
      - 4 giai doan: "2-1", "3-2", "4-2" va tong hop "All".
      - Cac bac xep hang: S, A, B, C.
      - Dinh danh: dung truc tiep ma Riot apiName (DA_...), khop >99% voi data/augment_features.json.

PROVENANCE
    Xep hang boi: Dishsoap & Frodan (TFT Academy).
    Thuoc tinh is_ordinal luon True, sample_n luon 0 theo bat bien cua ExpertTierListProvider.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import requests

TFTACADEMY_HOST = "https://tftacademy.com"
TIERLIST_API_URL = f"{TFTACADEMY_HOST}/api/tierlist/augments"
TIERLIST_PAGE_URL = f"{TFTACADEMY_HOST}/tierlist/augments"
DATA_JSON_URL = f"{TFTACADEMY_HOST}/tierlist/augments/__data.json"

USER_AGENT = "TFT-Agent-Thesis/0.1 (research build)"
DEFAULT_TIMEOUT_S = 10.0
VALID_TIERS = ("S", "A", "B", "C", "D")


class TFTAcademyError(RuntimeError):
    """Loi khi giao tiep hoac parse du lieu tu TFT Academy."""


class TFTAcademyClient:
    """Client lay du lieu tu TFT Academy."""

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

    def get_augments_tierlist(self, set_num: int = 18) -> dict[str, Any]:
        """Goi API lay danh sach tier list cua mot Set."""
        url = f"{TIERLIST_API_URL}?set={set_num}"
        try:
            resp = self.session.get(url, headers=self._headers(), timeout=self.timeout_s)
        except requests.RequestException as exc:
            raise TFTAcademyError(f"Loi ket noi den {url}: {exc}") from exc

        if resp.status_code != 200:
            raise TFTAcademyError(
                f"TFT Academy tra status {resp.status_code} tai {url}: {resp.text[:200]}"
            )

        try:
            return resp.json()
        except ValueError as exc:
            raise TFTAcademyError(f"Phan hoi tu {url} khong phai JSON hop le") from exc

    def get_patch_info(self) -> dict[str, str]:
        """Lay thong tin patch va lastUpdated tu SvelteKit __data.json."""
        try:
            resp = self.session.get(DATA_JSON_URL, headers=self._headers(), timeout=self.timeout_s)
            if resp.status_code != 200:
                return {}
            data = resp.json()
            patch = ""
            last_updated = ""
            for node in data.get("nodes", []):
                node_data = node.get("data")
                if isinstance(node_data, list):
                    for item in node_data:
                        if isinstance(item, str):
                            if re.match(r"^\d+\.\d+[a-z]?$", item):
                                patch = item
                            elif re.match(r"^\d{4}-\d{2}-\d{2}", item):
                                last_updated = item
            return {"patch": patch, "last_updated": last_updated}
        except Exception:
            return {}


def parse_tierlist_augments(
    payload: dict[str, Any],
    stage: str = "All",
) -> dict[str, list[str]]:
    """Tach cac augment theo tung bac S, A, B, C, D tu payload API.

    stage: "All" (tong hop moi stage) hoac "2-1", "3-2", "4-2".
    """
    entries = payload.get("augments_tierlists") or []
    if not entries:
        raise TFTAcademyError("Payload khong chua ban ghi 'augments_tierlists'")

    stage_lower = stage.strip().lower()
    matched_entries = [
        e for e in entries if str(e.get("stage", "")).strip().lower() == stage_lower
    ]

    if not matched_entries:
        available_stages = sorted({str(e.get("stage")) for e in entries})
        raise TFTAcademyError(
            f"Khong tim thay stage '{stage}'. Cac stage co san: {available_stages}"
        )

    out: dict[str, list[str]] = {t: [] for t in VALID_TIERS}
    seen: set[str] = set()

    for entry in matched_entries:
        tiers_dict = entry.get("tier") or {}
        for tier_key, aug_list in tiers_dict.items():
            t_upper = tier_key.strip().upper()
            if t_upper not in out:
                continue
            for aug in aug_list:
                aug_clean = str(aug).strip()
                if aug_clean and aug_clean not in seen:
                    seen.add(aug_clean)
                    out[t_upper].append(aug_clean)

    # Chi giu cac tier co chua augment
    return {t: out[t] for t in VALID_TIERS if out[t]}


def format_raw_text(
    tiers: dict[str, list[str]],
    meta: dict[str, Any] | None = None,
) -> str:
    """Xuat du lieu ra format text trung gian tuong thich scripts/import_augment_tiers.py.

    Format:
        # Patch: 18.1d
        # Rated by: TFT Academy (Dishsoap & Frodan)
        S: DA_18_..., DA_...
        A: DA_18_...
    """
    lines: list[str] = []
    if meta:
        lines.append("# TFT Academy Augments Tier List (Crawl tự động)")
        for k, v in meta.items():
            lines.append(f"# {k}: {v}")
        lines.append("")

    for tier in VALID_TIERS:
        augs = tiers.get(tier, [])
        if augs:
            lines.append(f"{tier}: {', '.join(augs)}")

    return "\n".join(lines) + "\n"


def build_tierlist_payload(
    tiers: dict[str, list[str]],
    meta: dict[str, Any],
) -> dict[str, Any]:
    """Dong goi thanh payload JSON dung chuan ExpertTierListProvider.load()."""
    full_meta = {
        "rated_by": meta.get("rated_by", "TFT Academy (Dishsoap & Frodan)"),
        "source_url": meta.get("source_url", TIERLIST_PAGE_URL),
        "patch": meta.get("patch", "?"),
        "stage": meta.get("stage", "All"),
        "lang": "en",
        "imported_at": date.today().isoformat(),
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "total_augments": sum(len(v) for v in tiers.values()),
        "note": meta.get(
            "note",
            "Xep hang CHU QUAN cua chuyen gia TFT Academy (Dishsoap & Frodan). "
            "AugmentStats.is_evidence luon False cho nguon nay.",
        ),
    }
    return {
        "meta": full_meta,
        "tiers": {t: tiers[t] for t in VALID_TIERS if t in tiers},
    }
