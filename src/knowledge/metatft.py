"""Client MetaTFT -> bang tier augment lam nguon du phong (SPEC 3.4, Nhiem vu 5).

VI SAO DUNG DUOC TRUC TIEP
    MetaTFT cung cap REST API noi bo:
        GET https://api-hc.metatft.com/tft-stat-api/augments_tiers?tft_set=TFTSet18

    Payload JSON tra ve gom danh sach tierList (S, A, B, C) do chuyen gia META Spencer xep hang.
    Dinh danh dung truc tiep ma Riot apiName (DA_...), khop >98% voi data/augment_features.json.

PROVENANCE
    Xep hang boi: MetaTFT (META Spencer).
    Thuoc tinh is_ordinal luon True, sample_n luon 0 theo bat bien cua ExpertTierListProvider.
    Dong vai tro nguon du phong thu hai sau TFT Academy:
        CSV (so do duoc) -> TFT Academy (chuyen gia chinh) -> MetaTFT (du phong) -> Null
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import requests

METATFT_HOST = "https://www.metatft.com"
TIERLIST_API_URL = "https://api-hc.metatft.com/tft-stat-api/augments_tiers"
GAMES_STAT_API_URL = "https://api-hc.metatft.com/tft-stat-api/games?days=7"
TIERLIST_PAGE_URL = f"{METATFT_HOST}/augments"

USER_AGENT = "TFT-Agent-Thesis/0.1 (research build)"
DEFAULT_TIMEOUT_S = 10.0
VALID_TIERS = ("S", "A", "B", "C", "D")


class MetaTFTError(RuntimeError):
    """Loi khi giao tiep hoac parse du lieu tu MetaTFT."""


class MetaTFTClient:
    """Client lay du lieu bang tier augment tu MetaTFT."""

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

    def get_augments_tierlist(self, set_num: int = 18) -> dict[str, Any]:
        """Goi API lay danh sach tier list cua mot Set tu MetaTFT."""
        url = f"{TIERLIST_API_URL}?tft_set=TFTSet{set_num}"
        try:
            resp = self.session.get(url, headers=self._headers(), timeout=self.timeout_s)
        except requests.RequestException as exc:
            raise MetaTFTError(f"Loi ket noi den {url}: {exc}") from exc

        if resp.status_code != 200:
            raise MetaTFTError(
                f"MetaTFT tra status {resp.status_code} tai {url}: {resp.text[:200]}"
            )

        try:
            return resp.json()
        except ValueError as exc:
            raise MetaTFTError(f"Phan hoi tu {url} khong phai JSON hop le") from exc

    def get_patch_info(self) -> dict[str, str]:
        """Lay thong tin patch hien tai tu endpoint thong ke tran dau cua MetaTFT."""
        try:
            resp = self.session.get(
                GAMES_STAT_API_URL, headers=self._headers(), timeout=self.timeout_s
            )
            if resp.status_code != 200:
                return {}
            data = resp.json()
            games = data.get("games") or []
            if games and isinstance(games, list):
                first_game = games[0]
                patch_raw = first_game.get("patch")
                if isinstance(patch_raw, list):
                    patch_str = "".join(str(p) for p in patch_raw)
                    return {"patch": patch_str}
                if isinstance(patch_raw, str):
                    return {"patch": patch_raw}
            return {}
        except Exception:
            return {}


def parse_tierlist_augments(payload: dict[str, Any]) -> dict[str, list[str]]:
    """Tach cac augment theo tung bac S, A, B, C, D tu payload MetaTFT API."""
    tier_list = None
    if "tierList" in payload:
        tier_list = payload["tierList"]
    elif "content" in payload:
        inner = payload["content"]
        if isinstance(inner, dict):
            if "content" in inner and isinstance(inner["content"], dict):
                tier_list = inner["content"].get("tierList")
            elif "tierList" in inner:
                tier_list = inner["tierList"]

    if not tier_list or not isinstance(tier_list, list):
        raise MetaTFTError("Payload khong chua danh sach 'tierList' hop le")

    out: dict[str, list[str]] = {t: [] for t in VALID_TIERS}
    seen: set[str] = set()

    for item in tier_list:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label", "")).strip().upper()
        if label not in out:
            continue
        content = item.get("content") or []
        for aug in content:
            if isinstance(aug, dict):
                aug_id = str(aug.get("id", "")).strip()
            else:
                aug_id = str(aug).strip()
            if aug_id and aug_id not in seen:
                seen.add(aug_id)
                out[label].append(aug_id)

    # Chi giu cac tier co chua augment
    return {t: out[t] for t in VALID_TIERS if out[t]}


def format_raw_text(
    tiers: dict[str, list[str]],
    meta: dict[str, Any] | None = None,
) -> str:
    """Xuat du lieu ra format text trung gian tuong thich scripts/import_augment_tiers.py.

    Format:
        # Patch: 18.1d
        # Rated by: MetaTFT (META Spencer)
        S: DA_18_..., DA_...
        A: DA_18_...
    """
    lines: list[str] = []
    if meta:
        lines.append("# MetaTFT Augments Tier List (Crawl tự động)")
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
        "rated_by": meta.get("rated_by", "MetaTFT (META Spencer)"),
        "source_url": meta.get("source_url", TIERLIST_PAGE_URL),
        "patch": meta.get("patch", "?"),
        "stage": meta.get("stage", "All"),
        "lang": "en",
        "imported_at": date.today().isoformat(),
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "total_augments": sum(len(v) for v in tiers.values()),
        "is_backup": True,
        "note": meta.get(
            "note",
            "Xep hang CHU QUAN cua chuyen gia MetaTFT (META Spencer). "
            "Nguon du phong thu hai sau TFT Academy. "
            "AugmentStats.is_evidence luon False cho nguon nay.",
        ),
    }
    return {
        "meta": full_meta,
        "tiers": {t: tiers[t] for t in VALID_TIERS if t in tiers},
    }
