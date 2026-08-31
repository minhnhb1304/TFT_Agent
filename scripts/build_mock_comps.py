"""Sinh data/meta_comps.json GIA LAP - feedback Tier 1 #2.

⚠️ DA BI THAY THE. Dung scripts/crawl_meta_comps.py thay cho script nay.

    Tu 2026-09-01, doi hinh meta DO DUOC that qua tft-match-v1: `units`,
    `traits` va `placement` deu con nguyen trong payload match. Khong con ly
    do gi de dung so gia cho comp.

    Script nay duoc GIU LAI cho truong hop khong co Riot API key (VD nguoi
    cham do an muon chay lai pipeline ma khong dang ky key). Chay no se ghi
    de du lieu that bang du lieu gia - nen no doi --overwrite, va
    tests/test_meta_comps.py se DO NGAY neu file ket qua mang source
    MOCK-NOT-REAL.

VI SAO FILE NAY TON TAI
    Khong co nguon meta comp Set 18 nao da xac minh (research/prior-art.md:
    OP.GG MCP vuong ToS va chua smoke-test; cac trang stats con cold-start).
    Khong co file nay thi CompDatabase rong, va CompSelector khong co gi de
    xep hang - ca nhanh SPEC 3.5.2 nam im.

    Feedback Tier 1 #2 chot: dung mock dung format de thuat toan chay ngay.

KHONG BIA TEN TUONG
    Day la diem khac biet giua "mock" va "bia". Ten comp, danh sach unit,
    trait va item deu lay tu du lieu Set 18 THAT trong data/cdragon_cache/
    (65 tuong, 36 trait, 51 item hoan chinh). Chi CAC CON SO thong ke
    (avg_placement, top4_rate, win_rate, play_rate) la gia lap.

    Nho the: cau truc du lieu dung that, nen khi cam nguon meta that vao thi
    chi doi so, khong phai doi code. Va OCR doc ra ten tuong nao thi cung
    khop duoc voi core_units.

KHOA LA apiName (feedback #6/#7)
    core_units giu `character_id` (VD: DA_18_Xayah), traits giu trait apiName.
    Ten hien thi cho nguoi doc nam o positioning_notes. Tang vision se dich
    ket qua OCR -> apiName truoc khi dung GameState, giong het cach
    data/name_index.json lam voi augment.

SO NAY LA GIA VA TU KHAI BAO LA GIA
    `source` = "MOCK-NOT-REAL" tren tung comp -> CompDatabase.sources va moi
    reason string cua CompSelector deu lo ra. Khong dung cho bao cao do an.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.knowledge.cdragon_client import CDragonClient, select_set_data  # noqa: E402
from src.utils.settings import Settings  # noqa: E402

MOCK_SOURCE = "MOCK-NOT-REAL"
DEFAULT_OUT = ROOT / "data" / "meta_comps.json"

# So comp sinh ra. Du de CompSelector co canh tranh thuc su, khong nhieu den
# muc khong ai doc noi file bang tay.
N_COMPS = 10

# Kich thuoc doi hinh - core la phan dinh danh comp, flex la phan thay duoc.
# Trait Set 18 chi co 5-7 tuong (Riftbeast nhieu nhat: 10), nen dieu kien du
# tieu chuan la N_CORE + 1 chu khong phai N_CORE + N_FLEX; flex lay phan con lai.
N_CORE = 4
N_FLEX = 4
N_ITEMS = 3
N_AUGMENTS = 3

# Co mau. PHAI >= 200 (MetaComp.is_evidence) - duoi nguong do CompSelector
# keo meta_score ve trung tinh va thanh phan meta mat tac dung.
SAMPLE_MIN = 400
SAMPLE_MAX = 6000

TIER_LABELS = ("S", "S", "A", "A", "A", "B", "B", "B", "C", "C")


def unit_hash(key: str, salt: str) -> float:
    """So thuc trong [0, 1) sinh deterministic - khong dung random/hash()."""
    digest = hashlib.sha256(f"{key}|{salt}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / float(1 << 64)


def completed_items(locale: dict[str, Any]) -> list[str]:
    """Item hoan chinh chuan: ghep tu dung 2 component, khong phai augment."""
    out = [
        str(i["apiName"])
        for i in locale.get("items", [])
        if str(i.get("apiName", "")).startswith("TFT_Item_")
        and not i.get("isAugment")
        and len(i.get("composition") or []) == 2
        and all(str(c).startswith("TFT_Item_") for c in i["composition"])
    ]
    return sorted(set(out))


def trait_api_names(locale: dict[str, Any]) -> dict[str, str]:
    """Ten trait hien thi -> apiName, tu DUNG khoi setData cua Set 18."""
    return {t["name"]: t["apiName"] for t in select_set_data(locale).get("traits", [])}


def group_by_trait(roster: list[Any]) -> dict[str, list[Any]]:
    groups: dict[str, list[Any]] = {}
    for champ in roster:
        for trait in champ.traits:
            groups.setdefault(trait, []).append(champ)
    return groups


def pick_augments(features: dict[str, Any], trait_api: str, seed: str) -> list[str]:
    """Uu tien augment co trait_affinity khop; thieu thi lay theo hash."""
    matched = sorted(
        api for api, f in features.items() if trait_api in (f.get("trait_affinity") or [])
    )
    if len(matched) >= N_AUGMENTS:
        return matched[:N_AUGMENTS]

    pool = sorted(api for api, f in features.items() if int(f.get("tier", 0)) >= 2)
    for api in sorted(pool, key=lambda a: unit_hash(a, seed)):
        if api not in matched:
            matched.append(api)
        if len(matched) >= N_AUGMENTS:
            break
    return matched[:N_AUGMENTS]


def build_comp(
    trait_name: str,
    trait_api: str,
    champs: list[Any],
    items: list[str],
    features: dict[str, Any],
    trait_apis: dict[str, str],
    rank: int,
) -> dict[str, Any]:
    """Mot ban ghi MetaComp. Khong duoc them key la - MetaComp(**c) se TypeError."""
    # Cost cao dung lam core (carry), cost thap lam early game.
    by_power = sorted(champs, key=lambda c: (-c.tier, c.character_id))
    core = by_power[:N_CORE]
    flex = by_power[N_CORE : N_CORE + N_FLEX]
    early = [c.character_id for c in sorted(champs, key=lambda c: (c.tier, c.character_id))[:3]]

    seed = trait_api
    # Comp xep hang cao thi placement tot hon - quan he don dieu, co nhieu nhe.
    avg_placement = round(3.9 + rank * 0.12 + unit_hash(seed, "place") * 0.20, 3)
    top4_rate = round(max(0.30, min(0.70, 0.62 - rank * 0.025)), 4)
    win_rate = round(max(0.06, min(0.25, top4_rate / 3.8)), 4)
    play_rate = round(0.02 + unit_hash(seed, "play") * 0.10, 4)
    sample_n = SAMPLE_MIN + int(unit_hash(seed, "n") * (SAMPLE_MAX - SAMPLE_MIN))

    chosen_items = sorted(items, key=lambda i: unit_hash(i, seed))[:N_ITEMS]
    display = ", ".join(c.display_name for c in core)

    # Doi hinh that khong bao gio chi co mot trait: dem cac trait phu ma
    # chinh cac core unit da mang san, giu nhung trait dat nguong >= 2.
    secondary: dict[str, int] = {}
    for champ in core:
        for name in champ.traits:
            api = trait_apis.get(name)
            if api and api != trait_api:
                secondary[api] = secondary.get(api, 0) + 1
    traits = {trait_api: len(core)}
    traits.update({api: n for api, n in sorted(secondary.items()) if n >= 2})

    return {
        "name": f"{trait_name} Core",
        "tier": TIER_LABELS[rank] if rank < len(TIER_LABELS) else "C",
        "core_units": [c.character_id for c in core],
        "flex_units": [c.character_id for c in flex],
        "core_items": chosen_items,
        "best_augments": pick_augments(features, trait_api, seed),
        "traits": traits,
        "avg_placement": avg_placement,
        "top4_rate": top4_rate,
        "win_rate": win_rate,
        "play_rate": play_rate,
        # level -> stage nen len level do.
        "level_timing": {"6": 3, "7": 4, "8": 5},
        "early_game": early,
        "positioning_notes": (
            f"DU LIEU GIA LAP ({MOCK_SOURCE}) - khong dung cho bao cao. "
            f"Core (ten hien thi): {display}."
        ),
        "source": MOCK_SOURCE,
        "sample_n": sample_n,
    }


def build(cache_dir: Path, features_path: Path) -> dict[str, Any]:
    client = CDragonClient(cache_dir=cache_dir, offline=True)
    roster = client.load_roster()
    locale = client.load_locale("en_us")

    trait_apis = trait_api_names(locale)
    items = completed_items(locale)
    features = json.loads(features_path.read_text(encoding="utf-8")).get("augments", {})

    groups = group_by_trait(roster)
    # Trait du quan so de dung mot doi hinh, va co it nhat mot tuong cost >= 4
    # de lam carry. Sap xep on dinh de ket qua tai lap duoc.
    eligible = sorted(
        (
            (name, champs)
            for name, champs in groups.items()
            if name in trait_apis
            and len(champs) >= N_CORE + 1
            and any(c.tier >= 4 for c in champs)
        ),
        key=lambda kv: (-len(kv[1]), kv[0]),
    )[:N_COMPS]

    if not eligible:
        raise SystemExit("Khong trait nao du dieu kien - kiem tra lai cache roster.")

    comps = [
        build_comp(name, trait_apis[name], champs, items, features, trait_apis, rank)
        for rank, (name, champs) in enumerate(eligible)
    ]
    return {
        "meta": {
            "set": "TFTSet18",
            "source": MOCK_SOURCE,
            "warning": "So lieu thong ke la GIA LAP. Unit/trait/item lay tu du lieu Set 18 that.",
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "n": len(comps),
        },
        "comps": comps,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--features", default=str(ROOT / "data" / "augment_features.json"))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Bat buoc neu file da ton tai. Chan viec de nham len du lieu THAT.",
    )
    args = parser.parse_args(argv)

    out = Path(args.out)
    if out.exists() and not args.overwrite:
        print(f"{out} da ton tai. Them --overwrite neu chac chan.", file=sys.stderr)
        return 1

    settings = Settings.load()
    cache_dir = Path(args.cache_dir) if args.cache_dir else settings.path("cdragon_cache")

    payload = build(cache_dir, Path(args.features))
    out.parent.mkdir(parents=True, exist_ok=True)
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print(f"da ghi {len(payload['comps'])} comp -> {out}")
    for c in payload["comps"]:
        print(f"  [{c['tier']}] {c['name']:28s} core={len(c['core_units'])} n={c['sample_n']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
