"""Duyet tay bang dac trung augment: mo mot trang trong trinh duyet, danh dau dung/sai, sua nhan.

    .venv\\Scripts\\python scripts\\review_augment_features.py

Trang chay o 127.0.0.1, KHONG mo ra ngoai may. Moi lan bam la ghi ngay vao
`data/eval/augment_feature_review.json` (mac dinh), nen dong trang giua chung
khong mat gi. File review KHONG sua `data/augment_features.json`; ap ket qua
la mot buoc rieng, sau khi duyet xong.

Moi entry review luu kem `original` - nhan tai thoi diem duyet - de do do chinh
xac cua tung cach trich (deterministic-v1 vs LLM) ke ca sau khi file dac trung
da duoc sua.
"""

from __future__ import annotations

import argparse
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
PAGE = (Path(__file__).parent / "review_augment_features.html").read_text(encoding="utf-8")

LABEL_FIELDS = ("category", "carry_type", "tempo", "econ_value",
                "trait_affinity", "item_grants", "board_condition")
VERDICTS = ("ok", "wrong", "unsure")
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


def build_rows(features_path: Path, locale_path: Path, tiers_path: Path) -> list[dict]:
    features = json.loads(features_path.read_text(encoding="utf-8"))["augments"]
    locale = json.loads(locale_path.read_text(encoding="utf-8"))
    raw = {str(i.get("apiName")): i for i in locale.get("items", []) if i.get("isAugment")}
    academy: dict[str, str] = {}
    if tiers_path.is_file():
        for grade, names in json.loads(tiers_path.read_text(encoding="utf-8"))["tiers"].items():
            for n in names:
                academy[n] = grade

    rows = []
    for api, f in features.items():
        r = raw.get(api, {})
        rows.append({**f, "desc": render_desc(r.get("desc", ""), r.get("effects", {})),
                     "academy": academy.get(api, "-")})
    rows.sort(key=lambda x: (x["name"] or x["api_name"]).lower())
    return rows


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


def make_handler(rows: list[dict], review_path: Path, features_path: Path):
    by_api = {r["api_name"]: r for r in rows}
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
                    reviews = load_reviews(review_path)["reviews"]
                return self._json(200, {"rows": rows, "reviews": reviews,
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
    ap.add_argument("--out", default="data/eval/augment_feature_review.json")
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args(argv)

    features_path = (ROOT / args.features).resolve()
    review_path = (ROOT / args.out).resolve()
    rows = build_rows(features_path, (ROOT / args.locale).resolve(), (ROOT / args.tiers).resolve())

    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(rows, review_path, features_path))
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
