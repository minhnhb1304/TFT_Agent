"""Nap mot bang tier augment do NGUOI xep -> data/augment_tiers.json.

    python scripts/import_augment_tiers.py bang.txt \
        --rated-by "TFT Academy (Dishsoap)" \
        --source-url https://tftacademy.com/tierlist/augments \
        --patch 18.1 --lang en

VI SAO LA NAP TAY CHU KHONG PHAI CRAWL
    Ba trang stats lon deu KHONG cho lay bang tier bang mot request sach se:

      - tactics.tools : khong co bang tier augment. Truong augment cua ho
        rong tren 1,75 trieu van (do 2026-09-01).
      - datatft.com   : bang tier nam HARDCODE trong bundle JS, ma hoa bang
        ma 2 ky tu tro vao mot mang xay o runtime. Giai duoc, nhung vo moi
        lan ho build lai - va do khong phai nen mong cho mot con so trong
        bao cao.
      - tftacademy.com: du lieu nam duoi /_app/, chinh robots.txt cua ho ghi
        Disallow.

    Nen: nguoi doc bang bang mat, dan vao mot file van ban, va KY TEN vao
    provenance. Cham hon, nhung `rated_by` khi do la su that kiem chung duoc
    thay vi mot chuoi tu sinh.

DINH DANG FILE VAO
    Moi dong: `BAC: ten, ten, ten`. Bac hop le: S A B C D. Dong bat dau bang
    `#` la ghi chu. Nhieu dong cung mot bac thi gop lai.

        # Prismatic - TFT Academy, patch 18.1
        S: Tinh Hoa Rong, Vien Man
        A: Cu Danh Cuoi, Ban Nang Sinh Ton
        B: DA_18_BranchingOut

    Ten co the la ten hien thi (se tra qua data/name_index.json) HOAC apiName
    viet thang. Ten khong tra duoc, hoac tra ra NHIEU HON MOT apiName, deu bi
    BAO LOI chu khong doan - dung nguyen tac cua name_index.py.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.knowledge.name_index import NameIndex  # noqa: E402
from src.knowledge.stats_provider import ExpertTierListProvider  # noqa: E402
from src.utils.settings import Settings  # noqa: E402

DEFAULT_OUT = ROOT / "data" / "augment_tiers.json"
VALID_TIERS = tuple(ExpertTierListProvider.TIER_PLACEMENT)


def parse_tier_file(text: str) -> dict[str, list[str]]:
    """Van ban -> {bac: [ten thô]}. Loi cu phap thi bao ngay tai dong do."""
    out: dict[str, list[str]] = {}
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"dong {lineno}: thieu dau ':' -> {raw!r}")
        tier, _, rest = line.partition(":")
        key = tier.strip().upper()
        if key not in VALID_TIERS:
            raise ValueError(
                f"dong {lineno}: bac '{tier.strip()}' khong hop le "
                f"(chi chap nhan {', '.join(VALID_TIERS)})"
            )
        names = [n.strip() for n in rest.split(",") if n.strip()]
        out.setdefault(key, []).extend(names)
    return out


def resolve_all(
    parsed: dict[str, list[str]], index: NameIndex, lang: str
) -> tuple[dict[str, list[str]], list[str]]:
    """Ten hien thi -> apiName. Tra ve (bang da tra, danh sach loi doc duoc).

    Khong doan bao gio: khong tra duoc va tra ra nhieu hon mot deu vao danh
    sach loi. Mot bang tier gan sai augment con te hon khong co bang tier.
    """
    resolved: dict[str, list[str]] = {}
    problems: list[str] = []
    seen: dict[str, str] = {}

    for tier in VALID_TIERS:
        for name in parsed.get(tier, []):
            if index.display_name(name, "augments", lang) or name.startswith("DA_"):
                hits = [name]
            else:
                hits = index.resolve(name, "augments", lang)

            if not hits:
                problems.append(f"[{tier}] khong tra duoc ten: {name!r}")
                continue
            if len(hits) > 1:
                problems.append(f"[{tier}] {name!r} map mo -> {hits}")
                continue

            api = hits[0]
            if api in seen:
                problems.append(f"[{tier}] {api} da xuat hien o bac {seen[api]}")
                continue
            seen[api] = tier
            resolved.setdefault(tier, []).append(api)
    return resolved, problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="file van ban dinh dang 'BAC: ten, ten'")
    parser.add_argument(
        "--rated-by",
        required=True,
        help="AI xep bang nay. Bat buoc - mot bang tier khong ai ky ten thi vo gia tri.",
    )
    parser.add_argument("--source-url", required=True, help="link den bang goc")
    parser.add_argument("--patch", required=True, help="patch cua bang, vi du 18.1")
    parser.add_argument("--lang", default="en", choices=["en", "vi"])
    parser.add_argument("--name-index", default=None, help="mac dinh: paths.name_index")
    parser.add_argument("--note", default="", help="ghi chu them vao provenance")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument(
        "--allow-unresolved",
        action="store_true",
        help="ghi file du con ten khong tra duoc (van in ra het)",
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    src = Path(args.input)
    if not src.exists():
        print(f"khong thay {src}", file=sys.stderr)
        return 1

    out = Path(args.out)
    if out.exists() and not args.overwrite:
        print(f"{out} da ton tai. Them --overwrite de de len.", file=sys.stderr)
        return 1

    settings = Settings.load()
    index_path = Path(args.name_index) if args.name_index else settings.path("name_index")
    index = NameIndex.load(index_path)
    if index.is_empty:
        print(
            f"{index_path} rong hoac khong ton tai. Chay scripts/build_name_index.py "
            "truoc, hoac viet thang apiName vao file vao.",
            file=sys.stderr,
        )

    try:
        parsed = parse_tier_file(src.read_text(encoding="utf-8"))
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    resolved, problems = resolve_all(parsed, index, args.lang)
    for p in problems:
        print(f"  ! {p}", file=sys.stderr)
    if problems and not args.allow_unresolved:
        print(
            f"\n{len(problems)} muc chua xu ly duoc - KHONG ghi file. Sua ten trong "
            f"{src}, hoac them --allow-unresolved de bo qua chung.",
            file=sys.stderr,
        )
        return 1

    if not resolved:
        print("khong tra duoc muc nao - khong ghi file.", file=sys.stderr)
        return 1

    payload = {
        "meta": {
            "rated_by": args.rated_by,
            "source_url": args.source_url,
            "patch": args.patch,
            "lang": args.lang,
            "imported_at": date.today().isoformat(),
            "input_file": src.name,
            "unresolved": len(problems),
            "note": args.note
            or (
                "Xep hang CHU QUAN cua nguoi choi, khong kem co mau. "
                "AugmentStats.is_evidence luon False cho nguon nay."
            ),
        },
        "tiers": {t: resolved[t] for t in VALID_TIERS if t in resolved},
    }
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    total = sum(len(v) for v in resolved.values())
    print(f"\nda ghi {total} augment -> {out}")
    for tier in VALID_TIERS:
        if tier in resolved:
            print(f"  {tier}: {len(resolved[tier])}")
    print(f"provenance: {args.rated_by} / patch {args.patch} / {args.source_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
