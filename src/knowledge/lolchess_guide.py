"""Client lolchess.gg/guide -> bang co che game Set 18 (SPEC 3.4).

VI SAO THEM NGUON NAY
    Cac bang co che - XP len cap, thu nhap, chuoi, ti le shop, pool tuong -
    KHONG co trong du lieu Riot phat ra: scan map22.bin.json tren PBE cho 0 hit
    (xem roll_odds.py). Truoc nguon nay, repo dung so cua cac set truoc va da
    SAI: XP 7->8 ghi 48 trong khi 18.1 la 60 va 18.2 la 56.

MUC DO TIN CAY - PHAI TACH BACH KHI TRICH TRONG BAO CAO
    Bang XP     : trang guide ghi 56/64/64, va patch notes 18.2 tren CHINH
                  lolchess ghi "60 => 56, 68 => 64, 68 => 64" -> khop. Day la
                  bang chung trang guide duoc cap nhat theo patch.
    Gia tuong   : cost[0] cua 65/65 tuong khop CDragon - hai nguon doc lap.
    Ti le shop, pool, chuoi, thu nhap: CHI co tren trang guide. Khong patch
                  notes nao cua Set 18 nhac toi -> so cua ben thu ba, chua doi
                  chieu client. Ngoai ra 18.1 ghi "Wisps appear in every other
                  shop" - mot o shop bi Wisp che, nen ti le roll hieu dung khac
                  bang nay.

CAU TRUC TRANG (do 2026-09-14)
    /guide/exp, /guide/reroll, /guide/rounds, /guide/role : bang render san
        trong HTML (SSR). /guide/role render "Recommended Items" o client nen
        HTML rong - dung `recommendItems` theo TUNG TUONG thay the.
    __NEXT_DATA__ cua moi trang: championRefs / traitRefs / itemRefs.
    /guide/patch-notes/<id> : __NEXT_DATA__ co patchNoteListRefs + noi dung.

KIEN TRUC: CRAWL OFFLINE, KHONG BAO GIO GOI LUC CHAY
    Chi scripts/crawl_lolchess_guide.py goi mang. Runtime doc file da ket tinh.
"""

from __future__ import annotations

import html as html_lib
import json
import re
import time
from html.parser import HTMLParser
from typing import Any

import requests

HOST = "https://lolchess.gg"
GUIDE_PAGES = ("exp", "reroll", "rounds", "role")
USER_AGENT = "TFT-Agent-Thesis/0.1 (single-user research build)"
MIN_INTERVAL_S = 1.0


class LolchessError(RuntimeError):
    """Loi mang hoac trang doi cau truc - that bai to, khong tra so rong."""


# -- doc bang HTML -------------------------------------------------------------


class _TableParser(HTMLParser):
    """Gom moi <table> thanh list hang -> list o {text, alts, src, colspan}.

    Bo qua noi dung <style> va <svg>: trang nhung CSS ngay trong <table>.
    """

    SKIP = ("style", "svg", "script")

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[dict[str, Any]]]] = []
        self._stack: list[list[list[dict[str, Any]]]] = []
        self._cell: dict[str, Any] | None = None
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag in self.SKIP:
            self._skip += 1
        elif tag == "table":
            self._stack.append([])
        elif tag == "tr" and self._stack:
            self._stack[-1].append([])
        elif tag in ("td", "th") and self._stack and self._stack[-1]:
            span = a.get("colspan") or a.get("colSpan") or "1"
            self._cell = {"text": "", "alts": [], "src": [], "colspan": int(span)}
            self._stack[-1][-1].append(self._cell)
        elif tag == "img" and self._cell is not None:
            self._cell["alts"].append(a.get("alt") or "")
            self._cell["src"].append(a.get("src") or "")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP:
            self._skip = max(0, self._skip - 1)
        elif tag in ("td", "th") and self._cell is not None:
            self._cell["text"] = " ".join(self._cell["text"].split())
            self._cell = None
        elif tag == "table" and self._stack:
            self.tables.append(self._stack.pop())

    def handle_data(self, data: str) -> None:
        if self._cell is not None and not self._skip:
            self._cell["text"] += " " + data


def tables(page_html: str) -> list[list[list[dict[str, Any]]]]:
    parser = _TableParser()
    parser.feed(page_html)
    return parser.tables


def _texts(row: list[dict[str, Any]]) -> list[str]:
    return [c["text"] for c in row]


def _find_table(page_html: str, header: str) -> list[list[dict[str, Any]]]:
    """Bang dau tien co mot o hang dau chua `header`. Khong co -> LolchessError."""
    for table in tables(page_html):
        if table and any(header in t for t in _texts(table[0])):
            return table
    raise LolchessError(f"khong tim thay bang co cot {header!r} - trang da doi cau truc?")


def _signed_int(text: str) -> int:
    """"+5" -> 5, "-" -> 0, "56 XP" -> 56."""
    m = re.search(r"-?\d+", text.replace("+", ""))
    return int(m.group()) if m and text.strip() != "-" else 0


# -- tung trang ------------------------------------------------------------------


def parse_exp(page_html: str) -> dict[str, Any]:
    """Bang XP, thu nhap co ban, lai, thuong chuoi, vang thang PvP."""
    xp_table = _find_table(page_html, "→ Lvl.")
    headers, values = _texts(xp_table[0]), _texts(xp_table[1])
    xp_to_next: dict[int, int] = {}
    for head, value in zip(headers, values):
        target = int(re.search(r"Lvl\.(\d+)", head).group(1))
        xp_to_next[target - 1] = _signed_int(value)

    def rows(header: str) -> list[list[str]]:
        return [_texts(r) for r in _find_table(page_html, header)[1:]]

    base_income = [
        {"round": r[0].replace(" ", ""), "gold": _signed_int(r[1])} for r in rows("Round")
    ]
    interest = []
    for label, gold in rows("Banked Gold"):
        low = int(re.match(r"\d+", label).group())
        high = re.search(r"~(\d+)", label)
        interest.append({"min": low, "max": int(high.group(1)) if high else None, "gold": _signed_int(gold)})
    streak_bonus = {int(re.match(r"\d+", label).group()): _signed_int(gold) for label, gold in rows("W/L Streaks")}

    text = html_lib.unescape(re.sub(r"<[^>]+>", " ", page_html))
    passive = re.search(r"(\d+)\s*EXP for each round", text)
    pvp_win = re.search(r"Get\s*(\d+)g if win a PvP round", text)
    if not passive or not pvp_win:
        raise LolchessError("khong doc duoc XP moi vong / vang thang PvP")
    return {
        "xp_to_next": xp_to_next,
        "passive_xp_per_round": int(passive.group(1)),
        "pvp_win_gold": int(pvp_win.group(1)),
        "base_income": base_income,
        "interest": interest,
        "streak_bonus": streak_bonus,
    }


def parse_reroll(page_html: str) -> dict[str, Any]:
    """Ti le shop theo cap + so ban moi tuong theo bac gia."""
    table = _find_table(page_html, "Level")
    pool_size: dict[int, int] = {}
    for cell in table[0][1:]:
        m = re.match(r"(\d)\s*\((\d+)\s*Total\)", cell["text"])
        if not m:
            raise LolchessError(f"o tieu de pool khong dung dang: {cell['text']!r}")
        pool_size[int(m.group(1))] = int(m.group(2))
    shop_odds: dict[int, list[float]] = {}
    for row in table[1:]:
        cells = _texts(row)
        level = int(re.search(r"\d+", cells[0]).group())
        shop_odds[level] = [round(_signed_int(c) / 100.0, 4) for c in cells[1:]]
    for level, odds in shop_odds.items():
        if abs(sum(odds) - 1.0) > 0.011:
            raise LolchessError(f"ti le shop cap {level} cong lai {sum(odds):.2f}, khong phai 100%")
    return {"pool_size": pool_size, "shop_odds": shop_odds}


def parse_rounds(page_html: str) -> dict[str, Any]:
    """Loai tung vong theo man, vong di cho va vong chon augment.

    Hang co anh `stageN.png` liet ke 7 vong bang `alt` cua icon. Vong chon
    augment mang them icon `augments_round` trong cung o.
    """
    table = _find_table(page_html, "Round 1")
    stages: dict[str, list[str]] = {}
    augment_rounds: list[str] = []
    for row in table[1:]:
        stage_img = next((s for c in row for s in c["src"] if re.search(r"/stage\d+\.png", s)), None)
        if not stage_img:
            continue
        stage = re.search(r"stage(\d+)\.png", stage_img).group(1)
        rounds = row[2:9]
        stages[stage] = [next((a for a in c["alts"] if a != "augments_round"), "") for c in rounds]
        augment_rounds += [f"{stage}-{i}" for i, c in enumerate(rounds, 1) if "augments_round" in c["alts"]]
    if not stages or any(len(r) != 7 for r in stages.values()):
        raise LolchessError("khong doc duoc cau truc vong dau")
    carousel = {s: r.index("Carousel") + 1 for s, r in stages.items() if "Carousel" in r}
    return {"stages": stages, "carousel_round": carousel, "augment_rounds": augment_rounds}


def parse_roles(page_html: str) -> dict[str, list[str]]:
    """Ten vai tro -> luat mana/phong thu. Do goi y cua trang render o client, bo qua."""
    found = re.findall(
        r"<div[^>]*>((?:Attack|Magic|Hybrid) [A-Z][a-z]+)</div></div><div[^>]*><p[^>]*>(.*?)</p>",
        page_html,
        re.S,
    )
    if not found:
        raise LolchessError("khong doc duoc danh sach vai tro")
    return {
        name: [html_lib.unescape(r).strip() for r in re.split(r"<br\s*/?>", body) if r.strip()]
        for name, body in found
    }


def next_data(page_html: str) -> dict[str, Any]:
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', page_html, re.S)
    if not m:
        raise LolchessError("trang khong co __NEXT_DATA__")
    return json.loads(m.group(1))


def _query(data: dict[str, Any], key: str) -> Any:
    for q in data.get("props", {}).get("pageProps", {}).get("dehydratedState", {}).get("queries", []):
        if q.get("queryKey", [None])[0] == key:
            return q["state"]["data"]
    return None


def parse_champions(page_html: str) -> list[dict[str, Any]]:
    """Tuong mua duoc (gia > 0): apiName, gia theo sao, vai tro, trait, do goi y."""
    refs = _query(next_data(page_html), "championRefs")
    if not refs:
        raise LolchessError("khong co championRefs trong __NEXT_DATA__")
    return [
        {
            "api_name": c["ingameKey"],
            "name": c["name"],
            "cost": c["cost"][0],
            "cost_by_star": c["cost"],
            "role": c.get("role") or "",
            "traits": c.get("traits") or [],
            "recommend_items": c.get("recommendItems") or [],
        }
        for c in refs["champions"]
        if c.get("cost") and c["cost"][0] > 0
    ]


def parse_patch_list(page_html: str, season: str = "set18") -> list[dict[str, Any]]:
    notes = (_query(next_data(page_html), "patchNoteListRefs") or {}).get("patchNotes", [])
    return sorted(
        ({"id": n["id"], "version": n["patchVersion"], "registered_at": n["registeredAt"]}
         for n in notes if n.get("season") == season),
        key=lambda n: n["registered_at"],
    )


def parse_system_changes(page_html: str) -> dict[str, list[str]]:
    """Muc "SYSTEMS - ..." cua mot ban patch notes."""
    data = _query(next_data(page_html), "patchNoteDataRefs") or {}
    content = data.get("patchNote", {}).get("content", {})
    return {k: v.get("descs") or [] for k, v in content.items() if k.upper().startswith("SYSTEMS")}


# -- mang -----------------------------------------------------------------------


class LolchessClient:
    """Chi scripts/crawl_lolchess_guide.py duoc dung. Runtime khong goi mang."""

    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en-US,en"})
        self._last = 0.0

    def get(self, path: str) -> str:
        wait = MIN_INTERVAL_S - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        url = f"{HOST}{path}"
        try:
            resp = self.session.get(url, params={"hl": "en"}, timeout=20)
        except requests.RequestException as exc:
            raise LolchessError(f"loi ket noi {url}: {exc}") from exc
        finally:
            self._last = time.monotonic()
        if resp.headers.get("x-amzn-waf-action"):
            raise LolchessError(
                f"{url} bi AWS WAF chan ({resp.headers['x-amzn-waf-action']}). KHONG gia "
                "User-Agent trinh duyet de lach - luu trang bang trinh duyet roi chay "
                "scripts/crawl_lolchess_guide.py --from-dir <thu muc>."
            )
        if resp.status_code != 200:
            raise LolchessError(f"{url} tra HTTP {resp.status_code}")
        return resp.text
