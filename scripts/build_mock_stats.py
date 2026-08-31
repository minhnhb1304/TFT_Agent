"""Sinh data/augment_stats.csv GIA LAP - feedback Tier 1 #1.

VI SAO FILE NAY TON TAI
    Khong co du lieu win-rate augment that cho Set 18: cac trang stats moi
    cold-start tu 2026-08-26 (research/set-data.md). Khong co file nay thi
    default_provider() roi ve NullProvider, BaseScorer tra 0.5 cho CA 254
    augment, va w1 = 0.30 tro thanh HANG SO - no khong the doi thu hang cua
    bat ky augment nao.

    Hau qua nang nhat nam o SPEC 12.4: dong ablation "chi w1" - dong quan
    trong nhat cua do an, dong tra loi cau hoi "vi sao phai lam advisor dong
    thay vi bang stats tinh" - suy bien thanh sap xep theo alphabet.

    Feedback Tier 1 #1 chot: dung mock dung format de thuat toan chay duoc
    ngay, sau nay co Riot API Key thi de len.

SO NAY LA GIA VA TU KHAI BAO LA GIA
    Cot `source` = "MOCK-NOT-REAL". BaseScorer in thang stats.source vao
    reason string (src/decision/scoring/base.py), nen overlay hien nguyen
    van "nguon: MOCK-NOT-REAL". Khong the vo tinh bao cao so nay nhu that.

    TUYET DOI khong dung file nay cho bat ky con so nao trong bao cao do an.

DETERMINISTIC
    Seed lay tu sha256(api_name), khong dung `random` va khong dung hash()
    cua Python (hash() doi giua cac lan chay vi PYTHONHASHSEED). Chay lai
    script cho ra file byte-identical - test khoa dieu nay.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MOCK_SOURCE = "MOCK-NOT-REAL"
DEFAULT_OUT = ROOT / "data" / "augment_stats.csv"
DEFAULT_FEATURES = ROOT / "data" / "augment_features.json"

# Thu tu cot phai khop CsvProvider.REQUIRED + cac cot tuy chon.
COLUMNS = ("api_name", "avg_place", "top4_rate", "win_rate", "sample_n", "source")

# Neo theo tier: augment bac cao thi manh hon, nen avg placement thap hon.
# Day la GIA DINH tao hinh dang du lieu, khong phai do dac.
TIER_ANCHOR = {1: 4.62, 2: 4.40, 3: 4.12}
FALLBACK_ANCHOR = 4.50

# Hieu chinh nhe theo category de w1 khong tuong quan hoan toan voi tier
# (neu no chi la ham cua tier thi ablation khong hoc duoc gi tu w1).
CATEGORY_SHIFT = {
    "econ": 0.05,      # doi tempo lay kinh te -> placement trung binh nhinh hon
    "reroll": 0.06,    # cam kiu, thang dam thua dam
    "combat": -0.05,
    "trait": -0.03,
    "item": -0.02,
    "utility": 0.0,
}

# Bien do nhieu quanh moc neo.
JITTER = 0.25

# Co mau. PHAI >= tuning.base.min_sample_n (200) trong scoring_weights.yaml:
# duoi nguong do BaseScorer keo diem ve 0.5 va w1 lai chet lan nua.
SAMPLE_MIN = 300
SAMPLE_MAX = 5000


def unit_hash(api_name: str, salt: str) -> float:
    """So thuc trong [0, 1) sinh deterministic tu api_name.

    Moi `salt` la mot dong doc lap - nho the avg_place va sample_n cua cung
    mot augment khong tuong quan gia tao voi nhau.
    """
    digest = hashlib.sha256(f"{api_name}|{salt}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / float(1 << 64)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def synth_row(api_name: str, tier: int, category: str) -> dict[str, object]:
    """Mot dong stats gia lap, nhat quan noi tai.

    top4_rate va win_rate suy ra TU avg_place chu khong boc rieng: du lieu
    that co rang buoc do, va neu mock vi pham thi bat ky kiem tra tinh hop
    ly nao cung phat hien ngay.
    """
    anchor = TIER_ANCHOR.get(tier, FALLBACK_ANCHOR)
    shift = CATEGORY_SHIFT.get(category, 0.0)
    jitter = (unit_hash(api_name, "place") * 2.0 - 1.0) * JITTER

    # Giu trong [3.5, 5.0] - dung khoang best_place/worst_place cua tuning.base,
    # de diem chuan hoa phu het [0, 1] thay vi don cuc.
    avg_place = clamp(anchor + shift + jitter, 3.5, 5.0)

    top4 = clamp(0.5 + (4.5 - avg_place) * 0.20, 0.35, 0.65)
    win = clamp(top4 / 4.0 + (unit_hash(api_name, "win") - 0.5) * 0.02, 0.08, 0.20)
    sample_n = SAMPLE_MIN + int(unit_hash(api_name, "n") * (SAMPLE_MAX - SAMPLE_MIN))

    return {
        "api_name": api_name,
        "avg_place": f"{avg_place:.3f}",
        "top4_rate": f"{top4:.4f}",
        "win_rate": f"{win:.4f}",
        "sample_n": sample_n,
        "source": MOCK_SOURCE,
    }


def build(features_path: Path) -> list[dict[str, object]]:
    payload = json.loads(features_path.read_text(encoding="utf-8"))
    augments = payload.get("augments", {})
    if not augments:
        raise SystemExit(f"{features_path} khong co augment nao - chay build_augment_features.py truoc.")
    return [
        synth_row(api_name, int(f.get("tier", 0)), str(f.get("category", "utility")))
        for api_name, f in sorted(augments.items())
    ]


def write_csv(rows: list[dict[str, object]], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    # newline="" + lineterminator="\n" -> file byte-identical tren moi OS.
    with io.open(out, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(COLUMNS), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", default=str(DEFAULT_FEATURES))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Bat buoc neu file da ton tai. Chan viec de nham len du lieu THAT.",
    )
    args = parser.parse_args(argv)

    out = Path(args.out)
    if out.exists() and not args.overwrite:
        print(
            f"{out} da ton tai. Them --overwrite neu chac chan muon de len.\n"
            "Neu day la du lieu that tu Riot API thi DUNG de len.",
            file=sys.stderr,
        )
        return 1

    rows = build(Path(args.features))
    write_csv(rows, out)

    places = [float(r["avg_place"]) for r in rows]
    print(f"da ghi {len(rows)} dong -> {out}")
    print(f"source = {MOCK_SOURCE} (hien nguyen van tren overlay)")
    print(f"avg_place: min {min(places):.3f} / trung binh {sum(places)/len(places):.3f} / max {max(places):.3f}")
    print(f"sample_n : tat ca trong [{SAMPLE_MIN}, {SAMPLE_MAX}] -> trust = 1.0, w1 that su phan biet duoc")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
