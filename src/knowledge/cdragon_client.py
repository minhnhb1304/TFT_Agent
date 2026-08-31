"""Client CommunityDragon - nguon du lieu tinh cua Set 18.

Module nay khong chi tai file ve. No ma hoa NAM CAI BAY IM LANG da do duoc va
ghi lai o research/set-data.md thanh assertion chay luc runtime.

Ly do: nap nham du lieu ma khong bao loi la kieu hong nguy hiem nhat cua du an
nay. Pipeline van chay, overlay van hien so, chi co dieu moi thu deu sai. Tha
crash sang o luc khoi dong con hon.

Nam cai bay (do 2026-08-28 tren /latest/):
    1. vn_vn.json moi nhu that nhung dong bang tu 2023-05-03
    2. sets['18'] trong file tong hop chi la stub 19 quai PvE, ten la "Set10"
    3. Set 18 dung lai ten asset cua Set 10 -> key theo mutator, khong theo name
    4. character_id khong con bat dau bang TFT18_ - 65/65 bat dau bang DA
    5. URL icon ghep chuoi tu ten hien thi chi dung 34/36 -> phai doc icon nguyen van
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

BASE = "https://raw.communitydragon.org"
DEFAULT_BRANCH = "latest"
USER_AGENT = "TFT-Agent-Thesis/0.1 (single-user research build)"

# Cac hang so DO DUOC, dung lam regression assert. Xem research/set-data.md.
EXPECTED_SET_NAME = "TFTSet18"
EXPECTED_ROSTER_SIZE = 65
EXPECTED_TIER_DISTRIBUTION = {1: 14, 2: 13, 3: 14, 4: 14, 5: 10}

# File locale cu hon nguong nay -> nghi ngo nap nham nguon hoac nguon da chet.
MAX_LOCALE_AGE_DAYS = 30


class CDragonError(RuntimeError):
    """Loi nap du lieu CommunityDragon - luon fail sang, khong bao gio nuot."""


def select_set_data(locale: dict[str, Any], mutator: str = EXPECTED_SET_NAME) -> dict[str, Any]:
    """Lay khoi setData cua DUNG set dang target - key theo `mutator`.

    Bay so 6 (do 2026-09-01 tren ban locale DAY DU, khong lo ra o fixture
    trimmed vi fixture chi co dung mot phan tu setData):

        setData[0] la TFTSet14, KHONG phai Set 18.

    File locale that mang 35 khoi setData khong sap xep theo thu tu nao, va
    khoi cua Set 18 co `name` la "Set10" (Set 18 dung lai ten asset cua Set
    10 - bay so 4 trong research/set-data.md). Nghia la:

        setData[0]      -> sai set, im lang
        loc theo name   -> sai set, im lang
        loc theo mutator-> dung

    Lay nham khoi nay thi bang anh xa trait sai toan bo ma khong bao loi:
    `trait_affinity` rong het, BoardFit thanh trung tinh cho moi augment.
    """
    for block in locale.get("setData") or []:
        if block.get("mutator") == mutator:
            return block
    seen = sorted({str(b.get("mutator")) for b in locale.get("setData") or []})
    raise CDragonError(
        f"Khong tim thay setData co mutator={mutator!r}. Cac mutator co san: {seen}"
    )


@dataclass(frozen=True)
class ChampionEntry:
    """Mot tuong trong roster Set 18."""

    character_id: str
    display_name: str
    tier: int
    traits: tuple[str, ...]
    square_icon_path: str

    @property
    def icon_url(self) -> str:
        """URL icon - DOC NGUYEN VAN tu squareIconPath, khong bao gio ghep chuoi.

        Bay so 5: casing khac nhau ngay trong cung mot path
        (thu muc TFT18_Murkwolf vs file TFT18_MurkWolf_Square).
        """
        path = self.square_icon_path.replace("/lol-game-data/assets", "").lower()
        return f"{BASE}/{DEFAULT_BRANCH}/plugins/rcp-be-lol-game-data/global/default{path}"


@dataclass
class CDragonClient:
    """Tai, cache va KIEM CHUNG du lieu Set 18.

    Args:
        branch: "latest" (mac dinh) hoac "pbe". Tinh den 2026-08-29 hai nhanh
            giong het nhau; "pbe" se co gia tri lai khi standalone client len PBE.
        cache_dir: noi luu file da tai.
        offline: neu True, chi doc tu cache - dung cho test khong co mang.
    """

    branch: str = DEFAULT_BRANCH
    cache_dir: Path = field(default_factory=lambda: Path("data/cdragon_cache"))
    offline: bool = False
    timeout: int = 60

    def __post_init__(self) -> None:
        self.cache_dir = Path(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # -- tang tai ----------------------------------------------------------

    def _url(self, path: str) -> str:
        return f"{BASE}/{self.branch}/{path}"

    def _fetch(self, path: str, cache_name: str) -> tuple[Any, str | None]:
        """Tai mot file JSON, tra ve (noi dung, Last-Modified).

        Neu offline=True thi doc thang tu cache va khong cham mang.
        """
        cache_file = self.cache_dir / cache_name
        meta_file = self.cache_dir / f"{cache_name}.meta"

        if self.offline:
            if not cache_file.exists():
                raise CDragonError(
                    f"offline=True nhung khong co cache {cache_file}. "
                    "Chay mot lan online truoc, hoac dung fixture trong test."
                )
            last_mod = meta_file.read_text(encoding="utf-8").strip() if meta_file.exists() else None
            return json.loads(cache_file.read_text(encoding="utf-8")), last_mod

        resp = requests.get(
            self._url(path), headers={"User-Agent": USER_AGENT}, timeout=self.timeout
        )
        if resp.status_code != 200:
            raise CDragonError(f"HTTP {resp.status_code} khi tai {self._url(path)}")

        last_mod = resp.headers.get("Last-Modified")
        cache_file.write_text(resp.text, encoding="utf-8")
        if last_mod:
            meta_file.write_text(last_mod, encoding="utf-8")
        return resp.json(), last_mod

    # -- tang kiem chung ---------------------------------------------------

    def load_set_info(self) -> dict[str, Any]:
        """Doc tftsets.json va assert dung set dang target.

        Bay so 3: key goc la LCTFTModeData, khong phai root.
        """
        data, _ = self._fetch(
            "plugins/rcp-be-lol-game-data/global/default/v1/tftsets.json",
            "tftsets.json",
        )
        root = data.get("LCTFTModeData", data)
        default_set = root.get("mDefaultSet", {})
        set_name = default_set.get("SetName")

        if set_name != EXPECTED_SET_NAME:
            raise CDragonError(
                f"mDefaultSet.SetName = {set_name!r}, mong doi {EXPECTED_SET_NAME!r}. "
                "Riot da doi set - PHAI calibrate lai ROI va sinh lai asset truoc khi chay tiep."
            )
        return default_set

    def load_roster(self) -> list[ChampionEntry]:
        """Doc roster tu tftchampions-teamplanner.json.

        Bay so 2: TUYET DOI khong doc roster tu cdragon/tft/{lang}.json ->
        sets['18'] o do chi la stub 19 quai PvE, ten la "Set10".
        """
        data, _ = self._fetch(
            "plugins/rcp-be-lol-game-data/global/default/v1/tftchampions-teamplanner.json",
            "tftchampions-teamplanner.json",
        )
        raw = data.get(EXPECTED_SET_NAME)
        if not raw:
            raise CDragonError(
                f"Khong co key {EXPECTED_SET_NAME!r} trong teamplanner. "
                f"Cac key co san: {sorted(data)}"
            )

        roster = [
            ChampionEntry(
                character_id=c["character_id"],
                display_name=c["display_name"],
                tier=int(c["tier"]),
                traits=tuple(t["name"] for t in c.get("traits", [])),
                square_icon_path=c["squareIconPath"],
            )
            for c in raw
        ]

        self._assert_roster_sane(roster)
        return roster

    @staticmethod
    def _assert_roster_sane(roster: list[ChampionEntry]) -> None:
        """Regression assert - so lieu do duoc 2026-08-28, xem research/set-data.md."""
        if len(roster) != EXPECTED_ROSTER_SIZE:
            raise CDragonError(f"Roster co {len(roster)} tuong, mong doi {EXPECTED_ROSTER_SIZE}")

        dist: dict[int, int] = {}
        for c in roster:
            dist[c.tier] = dist.get(c.tier, 0) + 1
        if dist != EXPECTED_TIER_DISTRIBUTION:
            raise CDragonError(f"Phan bo tier {dist}, mong doi {EXPECTED_TIER_DISTRIBUTION}")

        # Bay so 4: character_id khong con bat dau bang TFT18_.
        odd = [c.character_id for c in roster if not c.character_id.startswith("DA")]
        if odd:
            raise CDragonError(f"character_id khong bat dau bang DA: {odd[:5]}")

    def load_locale(self, lang: str = "vi_vn") -> dict[str, Any]:
        """Nap file ngon ngu va assert do tuoi.

        Bay so 1: vn_vn.json tra HTTP 200 y het vi_vn.json tren nhanh /pbe/
        nhung dong bang tu 2023-05-03. Tren /latest/ no 404. Assert Last-Modified
        bat duoc CA HAI truong hop, va ca truong hop nguon chet trong tuong lai.
        """
        if lang == "vn_vn":
            raise CDragonError(
                "vn_vn la file moi nhu that (dong bang 2023-05-03). Dung vi_vn."
            )

        data, last_mod = self._fetch(f"cdragon/tft/{lang}.json", f"{lang}.json")

        if last_mod:
            age_days = self._age_in_days(last_mod)
            if age_days is not None and age_days > MAX_LOCALE_AGE_DAYS:
                raise CDragonError(
                    f"{lang}.json cu {age_days:.0f} ngay (Last-Modified: {last_mod}). "
                    f"Nguong {MAX_LOCALE_AGE_DAYS} ngay - nghi ngo nap nham nguon hoac nguon da chet."
                )
        return data

    @staticmethod
    def _age_in_days(last_modified: str) -> float | None:
        """Doi header Last-Modified thanh so ngay. Tra None neu khong parse duoc."""
        try:
            parsed = time.strptime(last_modified, "%a, %d %b %Y %H:%M:%S %Z")
        except (ValueError, TypeError):
            return None
        dt = datetime(*parsed[:6], tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0

    # -- tien ich ----------------------------------------------------------

    @staticmethod
    def icon_url(icon_field: str, branch: str = DEFAULT_BRANCH) -> str:
        """Doi field icon (duoi .tex) thanh URL .png dung duoc.

        Bay so 5: 36/36 trait resolve duoc bang cach nay; ghep chuoi tu ten
        hien thi tieng Anh chi dung 34/36.
        """
        path = str(icon_field).lower().replace(".tex", ".png").lstrip("/")
        return f"{BASE}/{branch}/game/{path}"
