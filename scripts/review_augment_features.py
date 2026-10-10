"""Duyet tay bang dac trung augment: mo mot trang trong trinh duyet, danh dau dung/sai, sua nhan.

    .venv\\Scripts\\python scripts\\review_augment_features.py

Trang chay o 127.0.0.1, KHONG mo ra ngoai may. Moi lan bam la ghi ngay vao
`data/eval/augment_feature_review.json` (mac dinh), nen dong trang giua chung
khong mat gi. File review KHONG sua `data/augment_features.json`; ap ket qua
la mot buoc rieng, sau khi duyet xong.

Moi entry review luu kem `original` - nhan tai thoi diem duyet - de do do chinh
xac cua tung cach trich (deterministic-v1 vs LLM) ke ca sau khi file dac trung
da duoc sua.

Schema nhan (2026-10-05): `categories` 1-3 nhan (nhan chinh dau tien, `category`
= categories[0]), `carry_type` AD/AP/both/none, `frontline` bool. Entry review cu
(fix.category don, carry "tank") duoc CHUYEN DOI KHI DOC (`migrate_review`) va gan
co `recheck`; file review chi bi ghi lai tung entry qua duong luu binh thuong.
Dinh nghia: docs/category-multilabel/definition.md

Luot chao (2026-10-06): moi dong kem `offer_rounds` (2-1 / 3-2 / 4-2) vi `tempo` phai
xet TAI LUOT loi duoc chao. Lay tu bang feature; dong chua co thi lui ve snapshot
`data/augment_rounds.datatft.json` (may chu CN: tin hieu, khong phai ground truth).
Entry da chap nhan `tempo = immediate` cho loi chi co o 2-1 tu truoc khi trang hien
luot duoc gan co `recheck` khi doc. Xem docs/offer-rounds/overview.md
"""

from __future__ import annotations

import argparse
import copy
import dataclasses
import json
import re
import sys
import threading
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.knowledge.augment_features import (  # noqa: E402
    CARRY_TYPES, COMPONENT_PATTERNS, GENERIC_ITEM_PATTERNS, LEGACY_CARRY_TANK, OFFER_ROUNDS, TEMPOS,
    AugmentFeature, FeatureTable, check_feature,
)
from src.knowledge.cdragon_client import select_set_data  # noqa: E402

PAGE = (Path(__file__).parent / "review_augment_features.html").read_text(encoding="utf-8")

# `category` van luu trong `original` (de so voi review cu) nhung trong `fix` no
# luon suy ra tu categories[0], khong sua rieng.
LABEL_FIELDS = ("category", "categories", "carry_type", "frontline", "tempo", "econ_value",
                "trait_affinity", "item_grants", "board_condition", "offer_rounds")
FEATURE_FIELDS = tuple(f.name for f in dataclasses.fields(AugmentFeature))
VERDICTS = ("ok", "wrong", "unsure")
# Key CHI dung de gan nhan tay (ground truth), extractor chua sinh va ItemFit chua
# cham. Tach `Anvil` theo loai de va them qua tang thang Artifact/Radiant; doi
# extractor + ItemFit la viec rieng, xem docs/next-steps.md.
REVIEW_ONLY_GRANTS = ("ComponentAnvil", "CompletedAnvil", "ArtifactAnvil", "Artifact", "RadiantItem")
RE_PLACEHOLDER = re.compile(r"@([\w.]+)(\*100)?@")
RE_TAG = re.compile(r"<[^>]+>")


def fnv1a32(text: str) -> str:
    """Hash CDragon dung cho key effects bi bam: `{%08x}` cua FNV-1a 32 bit tren ten viet thuong."""
    h = 0x811C9DC5
    for b in text.lower().encode("utf-8"):
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return f"{{{h:08x}}}"


def render_desc(desc: str, effects: dict) -> str:
    """Thay @Key@ bang gia tri trong `effects` (ten tran hoac ten bi bam); bo the HTML.

    Placeholder khong resolve duoc giu nguyen de nguoi duyet thay ro cho trong.
    """
    lower = {str(k).lower(): v for k, v in (effects or {}).items()}

    def sub(m: re.Match) -> str:
        key = m.group(1).lower()
        v = lower.get(key, lower.get(fnv1a32(key)))
        if not isinstance(v, (int, float)):
            return m.group(0)
        if m.group(2):
            v *= 100
        return f"{v:g}"

    return RE_TAG.sub(" ", RE_PLACEHOLDER.sub(sub, desc or "")).replace("  ", " ").strip()


def build_options(locale: dict) -> dict:
    """Gia tri hop le cho hai truong danh sach - trang chi cho CHON, khong cho go tu do.

    item_grants: bo key ma extractor sinh ra va ItemFit doc, cong REVIEW_ONLY_GRANTS.
    `Anvil` (chung chung) van giu de nhan cu cua extractor khong bi coi la sai dinh dang.
    """
    traits = sorted(({"api": t["apiName"], "name": t["name"]} for t in select_set_data(locale).get("traits", [])),
                    key=lambda x: x["name"].lower())
    return {"item_grants": [*COMPONENT_PATTERNS, *GENERIC_ITEM_PATTERNS, *REVIEW_ONLY_GRANTS],
            "trait_affinity": traits}


def load_datatft(path: Path) -> dict:
    """`{api_name: {"rounds": [...], "types": [...]}}` tu snapshot datatft; thieu file = rong."""
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("augments", {})


def load_flags(path: Path) -> tuple[dict, str | None]:
    """`({api_name: [ly do, ...]}, created_at)` cua vong duyet 2; thieu file = rong."""
    if not path.is_file():
        return {}, None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("flags", {}), data.get("meta", {}).get("created_at")


def build_rows(features: dict, locale: dict, tiers_path: Path, datatft: dict | None = None,
               flags: dict | None = None) -> list[dict]:
    raw = {str(i.get("apiName")): i for i in locale.get("items", []) if i.get("isAugment")}
    academy: dict[str, str] = {}
    if tiers_path.is_file():
        for grade, names in json.loads(tiers_path.read_text(encoding="utf-8"))["tiers"].items():
            for n in names:
                academy[n] = grade

    rows = []
    for api, f in features.items():
        r = raw.get(api, {})
        # Luot chao: uu tien bang feature (co the da sua tay), rong thi lui ve datatft.
        # `datatft_types` la ma tho cua nguon, CHUA xac nhan y nghia: chi hien, khong dich.
        src = (datatft or {}).get(api, {})
        src_rounds = [x for x in OFFER_ROUNDS if x in src.get("rounds", [])]
        own = list(f.get("offer_rounds") or [])
        rows.append({**f, "desc": render_desc(r.get("desc", ""), r.get("effects", {})),
                     "academy": academy.get(api, "-"),
                     "offer_rounds": own or src_rounds,
                     "offer_rounds_source": "feature" if own else ("datatft" if src_rounds else None),
                     "datatft_rounds": src_rounds,
                     "datatft_types": list(src.get("types", [])),
                     "flags": list((flags or {}).get(api, []))})
    rows.sort(key=lambda x: (x["name"] or x["api_name"]).lower())
    return rows


def _migrate_labels(labels: dict, reasons: list[str], where: str) -> None:
    """Sua tai cho mot dict nhan (original hoac fix) tu schema cu sang moi."""
    if labels.get("carry_type") == LEGACY_CARRY_TANK:
        labels["carry_type"] = "none"
        labels["frontline"] = True
        reasons.append(f"{where}: carry_type cũ 'tank' đã đổi thành none + frontline, kiểm tra lại")


def tempo_round_reason(entry: dict, row: dict | None) -> str | None:
    """Ly do xem lai `tempo` theo luot chao, hoac None.

    Bat entry da CHAP NHAN `tempo = immediate` (verdict ok, hoac wrong ma tempo sau sua
    van immediate) cho loi chi chao o 2-1. Entry luu sau khi trang hien luot co
    `original.offer_rounds` khac rong: nguoi duyet da thay luot, khong gan co nua
    (bam luu lai la bo co). Khong bao gio tu doi nhan.
    """
    if row is None or entry.get("verdict") not in ("ok", "wrong"):
        return None
    orig = entry.get("original") if isinstance(entry.get("original"), dict) else {}
    if orig.get("offer_rounds"):
        return None
    fix = entry.get("fix") if isinstance(entry.get("fix"), dict) else {}
    tempo = fix.get("tempo", orig.get("tempo", row.get("tempo")))
    rounds = fix.get("offer_rounds", row.get("offer_rounds"))
    if tempo == "immediate" and rounds == ["2-1"]:
        return ("tempo: lõi chỉ xuất hiện ở 2-1 mà đã duyệt là immediate trước khi trang hiện lượt; "
                "xét lại tại 2-1 rồi lưu lại để bỏ cờ")
    return None


def migrate_review(entry: dict, row: dict | None) -> dict:
    """Ban sao entry review theo schema moi, kem `recheck` (ly do can xem lai).

    CHI dung khi doc (tra cho trang). Khong ghi nguoc ra file: file review la du
    lieu tay cua nguoi dung, entry chi doi shape khi chinh nguoi do bam luu lai.
    """
    e = copy.deepcopy(entry)
    reasons: list[str] = []
    orig = e.get("original")
    if isinstance(orig, dict):
        if "categories" not in orig and orig.get("category"):
            orig["categories"] = [orig["category"]]
        _migrate_labels(orig, reasons, "nhãn lúc duyệt")
        orig.setdefault("frontline", False)
    fix = e.get("fix")
    if isinstance(fix, dict):
        if "category" in fix:
            cat = fix.pop("category")
            if "categories" not in fix:
                fix["categories"] = [cat]
                reasons.append(f"đã sửa category (nhãn đơn) thành {cat!r}: chọn lại đủ categories")
        _migrate_labels(fix, reasons, "nhãn sửa")
    if row is not None and isinstance(orig, dict):
        changed = [k for k in LABEL_FIELDS if k in orig and orig[k] != row.get(k)]
        if changed:
            reasons.append("nhãn hiện tại khác lúc duyệt: " + ", ".join(changed))
    tempo_reason = tempo_round_reason(e, row)
    if tempo_reason:
        reasons.append(tempo_reason)
    if reasons:
        e["recheck"] = reasons
    return e


def validate_fix(row: dict, fix: dict) -> list[str]:
    """Loi cua nhan sau sua (rong = hop le): kieu du lieu, roi bat bien check_feature."""
    errs: list[str] = []
    cats = fix.get("categories")
    if cats is not None and (not isinstance(cats, list) or not all(isinstance(c, str) for c in cats)):
        return ["categories phải là danh sách nhãn"]
    if cats == []:
        return ["cần chọn ít nhất 1 nhãn categories"]
    if "carry_type" in fix and fix["carry_type"] not in CARRY_TYPES:
        errs.append(f"carry_type phải là một trong {', '.join(CARRY_TYPES)}")
    if "frontline" in fix and not isinstance(fix["frontline"], bool):
        errs.append("frontline phải là true/false")
    if "tempo" in fix and fix["tempo"] not in TEMPOS:
        errs.append(f"tempo phải là một trong {', '.join(TEMPOS)}")
    if "econ_value" in fix and fix["econ_value"] not in (0, 1, 2, 3):
        errs.append("econ_value phải là 0-3")
    rounds = fix.get("offer_rounds")
    if rounds is not None and (not isinstance(rounds, list) or not all(isinstance(x, str) for x in rounds)):
        errs.append("offer_rounds phải là danh sách lượt")
    if errs:
        return errs
    merged = {k: row[k] for k in FEATURE_FIELDS if k in row}
    merged.update({k: v for k, v in fix.items() if k in FEATURE_FIELDS})
    if cats:
        merged["category"] = cats[0]
    return check_feature(AugmentFeature(**merged))


def load_reviews(path: Path) -> dict:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"meta": {}, "reviews": {}}


def write_reviews(path: Path, data: dict) -> None:
    """Ghi qua file tam roi thay the, de Ctrl+C giua chung khong de lai file hong."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def make_handler(rows: list[dict], options: dict, review_path: Path, features_path: Path,
                 flags_since: str | None = None):
    by_api = {r["api_name"]: r for r in rows}
    allowed = {"item_grants": set(options["item_grants"]),
               "trait_affinity": {t["api"] for t in options["trait_affinity"]}}
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args) -> None:      # noqa: D102 - im lang, khong spam console
            pass

        def _json(self, code: int, data: dict) -> None:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:                   # noqa: N802
            if self.path in ("/", "/index.html"):
                body = PAGE.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path == "/api/state":
                with lock:
                    raw = load_reviews(review_path)["reviews"]
                reviews = {k: migrate_review(v, by_api.get(k)) for k, v in raw.items()}
                return self._json(200, {"rows": rows, "options": options, "reviews": reviews,
                                        "flags_since": flags_since,
                                        "path": str(review_path.relative_to(ROOT))})
            self._json(404, {"error": "không có endpoint này"})

        def do_POST(self) -> None:                  # noqa: N802
            if self.path != "/api/save":
                return self._json(404, {"error": "không có endpoint này"})
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")
            api = payload.get("api_name")
            review = payload.get("review")
            if api not in by_api:
                return self._json(400, {"error": f"không có lõi {api!r}"})

            with lock:
                data = load_reviews(review_path)
                data["meta"] = {"features_file": features_path.relative_to(ROOT).as_posix(),
                                "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
                if review is None:
                    data["reviews"].pop(api, None)
                else:
                    if review.get("verdict") not in VERDICTS:
                        return self._json(400, {"error": "verdict phải là ok / wrong / unsure"})
                    row = by_api[api]
                    entry = {
                        "verdict": review["verdict"],
                        "note": str(review.get("note") or ""),
                        "original": {k: row.get(k) for k in LABEL_FIELDS},
                        "extraction_method": row.get("extraction_method"),
                        "updated_at": data["meta"]["updated_at"],
                    }
                    if review["verdict"] == "wrong":
                        fix = {k: v for k, v in (review.get("fix") or {}).items() if k in LABEL_FIELDS}
                        cat = fix.pop("category", None)      # client cu chi gui nhan don
                        if cat is not None and "categories" not in fix:
                            fix["categories"] = [cat]
                        for k, ok in allowed.items():
                            bad = [v for v in fix.get(k) or [] if v not in ok]
                            if bad:
                                return self._json(400, {"error": f"{k} có giá trị không hợp lệ: {bad}"})
                        errs = validate_fix(row, fix)
                        if errs:
                            print(f"TỪ CHỐI {api}: {'; '.join(errs)}", flush=True)
                            return self._json(400, {"error": "Nhãn chưa hợp lệ: " + "; ".join(errs)})
                        if fix.get("categories"):
                            fix["category"] = fix["categories"][0]
                        entry["fix"] = {k: v for k, v in fix.items() if v != row.get(k)}
                    data["reviews"][api] = entry
                write_reviews(review_path, data)
                n = len(data["reviews"])
            print(f"đã lưu {api} ({review['verdict'] if review else 'xóa'}) — {n}/{len(rows)} lõi đã duyệt", flush=True)
            self._json(200, {"ok": True, "entry": data["reviews"].get(api)})

    return Handler


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Duyệt tay nhãn phân loại lõi trong trình duyệt")
    ap.add_argument("--features", default="data/augment_features.json")
    ap.add_argument("--locale", default="data/cdragon_cache/en_us.json")
    ap.add_argument("--tiers", default="data/augment_tiers.json")
    ap.add_argument("--rounds", default="data/augment_rounds.datatft.json",
                    help="snapshot datatft: lượt chào cho dòng chưa có offer_rounds, và mã type")
    ap.add_argument("--flags", default="data/eval/augment_review_round2.json",
                    help="danh sách lõi cần duyệt lại (vòng 2) kèm lý do; thiếu file thì bỏ qua")
    ap.add_argument("--out", default="data/eval/augment_feature_review.json")
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args(argv)

    features_path = (ROOT / args.features).resolve()
    review_path = (ROOT / args.out).resolve()
    # Qua FeatureTable/AugmentFeature de bang shape cu (chua co categories, carry
    # "tank") cung duoc chuyen doi y nhu luc runtime.
    features = {k: f.to_dict() for k, f in FeatureTable.load(features_path).features.items()}
    locale = json.loads((ROOT / args.locale).read_text(encoding="utf-8"))
    flags, flags_since = load_flags((ROOT / args.flags).resolve())
    rows = build_rows(features, locale, (ROOT / args.tiers).resolve(),
                      load_datatft((ROOT / args.rounds).resolve()), flags)
    options = build_options(locale)

    server = ThreadingHTTPServer(("127.0.0.1", args.port),
                                 make_handler(rows, options, review_path, features_path, flags_since))
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Mở {url} để duyệt {len(rows)} lõi. Kết quả ghi vào {review_path.relative_to(ROOT)}. Ctrl+C để dừng.")
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nđã dừng.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
