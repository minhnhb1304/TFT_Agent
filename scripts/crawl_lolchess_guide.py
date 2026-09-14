"""Crawl lolchess.gg/guide -> data/lolchess_guide.json (SPEC 3.4).

Ket tinh cac bang co che game Set 18 ma Riot khong phat ra: XP len cap, thu
nhap, lai, chuoi, ti le shop, pool tuong, cau truc vong dau, vai tro tuong,
va muc SYSTEMS cua moi ban patch notes Set 18.

Muc do tin cay tung bang ghi ngay trong file dau ra (meta.reliability) va
trong docstring cua src/knowledge/lolchess_guide.py - doc truoc khi trich so.

    python scripts/crawl_lolchess_guide.py           # ~10 request, cach nhau 1 giay
    python scripts/crawl_lolchess_guide.py --from-dir <thu muc>

lolchess dat AWS WAF truoc site: client khong phai trinh duyet nhan HTTP 202 +
`x-amzn-waf-action: challenge`. Script KHONG gia User-Agent trinh duyet de lach.
Bi chan thi luu trang bang trinh duyet (Ctrl+S, "HTML only") vao mot thu muc:

    exp.html  reroll.html  rounds.html  role.html
    patch-notes.html            <- lolchess.gg/guide/patch-notes
    patch-notes-<id>.html       <- tung ban Set 18, id lay tu trang tren

Sau khi crawl, chay `pytest tests/test_lolchess_guide.py`: cac test "drift"
so hang so trong code (roll_odds, rules_engine, scoring_weights.yaml) voi
file vua sinh. Patch doi so thi test do ngay - sua hang so co y thuc.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.knowledge.lolchess_guide import (  # noqa: E402
    HOST,
    LolchessClient,
    parse_champions,
    parse_exp,
    parse_patch_list,
    parse_reroll,
    parse_roles,
    parse_rounds,
    parse_system_changes,
)

DEFAULT_OUT = ROOT / "data" / "lolchess_guide.json"
# Chi giu tuong cua Set 18; championRefs cua trang lan ca don vi set cu.
SET_PREFIX = "DA_"

RELIABILITY = {
    "economy.xp_to_next": "Khop patch notes 18.2 tren lolchess (60=>56, 68=>64, 68=>64).",
    "champions.cost": "Khop CDragon setData cho 65/65 tuong trong roster.",
    "shop": "Chi co tren trang guide, khong patch notes Set 18 nao nhac toi. "
            "Chua doi chieu client. 18.1: Wisp xuat hien moi shop thu hai.",
    "economy.streak_bonus/base_income/interest": "Chi co tren trang guide, chua doi chieu client.",
    "rounds": "Chi co tren trang guide. Vong di cho x-4 khop mo ta cua nguoi choi.",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--from-dir", default=None, help="doc trang da luu thay vi goi mang")
    args = parser.parse_args(argv)

    if args.from_dir:
        folder = Path(args.from_dir)

        def fetch(path: str) -> str:
            name = path.removeprefix("/guide/").replace("/", "-") + ".html"
            return (folder / name).read_text(encoding="utf-8")
    else:
        fetch = LolchessClient().get

    pages = {name: fetch(f"/guide/{name}") for name in ("exp", "reroll", "rounds", "role")}
    patch_index = fetch("/guide/patch-notes")

    patches = []
    for note in parse_patch_list(patch_index):
        body = fetch(f"/guide/patch-notes/{note['id']}")
        patches.append({**note, "systems": parse_system_changes(body)})

    champions = [c for c in parse_champions(pages["reroll"]) if c["api_name"].startswith(SET_PREFIX)]
    payload = {
        "meta": {
            "source": f"{HOST}/guide/{{exp,reroll,rounds,role,patch-notes}}",
            "provider": "lolchess.gg (PlayXP) - ben thu ba, khong phai Riot",
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "latest_patch": patches[-1]["version"] if patches else None,
            "reliability": RELIABILITY,
        },
        "economy": parse_exp(pages["exp"]),
        "shop": parse_reroll(pages["reroll"]),
        "rounds": parse_rounds(pages["rounds"]),
        "roles": parse_roles(pages["role"]),
        "champions": sorted(champions, key=lambda c: c["api_name"]),
        "patches": patches,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    eco, shop = payload["economy"], payload["shop"]
    print(f"da ghi -> {out}")
    print(f"  patch moi nhat: {payload['meta']['latest_patch']} ({len(patches)} ban Set 18)")
    print(f"  XP len cap: {eco['xp_to_next']}")
    print(f"  pool: {shop['pool_size']}  |  tuong: {len(champions)}  |  vai tro: {len(payload['roles'])}")
    print(f"  vong chon augment: {payload['rounds']['augment_rounds']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
