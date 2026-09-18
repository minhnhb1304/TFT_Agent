"""Cong cu xem lai nhan playtest: mo mot trang trong trinh duyet, sua roi luu (moc M0).

    .venv\\Scripts\\python scripts\\review_playtest_labels.py data\\eval\\playtest\\<id>.json \\
        --video "D:\\workspace\\tft_record\\<file>.mp4"

Trang chay o 127.0.0.1, KHONG mo ra ngoai may. Moi offer hien anh chup kem ba o
nhap ten lo (go tieng Viet, co goi y), o chon o vua reroll, va nut chen/xoa offer.
`--video` la tuy chon, chi can khi muon chup them anh cho offer chen tay.

Huong dan kiem tay tung buoc: docs/playtest-fixes/labeling-guide.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.eval.playtest_labels import from_dict  # noqa: E402
from src.eval.playtest_review import augment_options, capture_snapshot, resolve_slot, save_payload  # noqa: E402
from src.knowledge.name_index import NameIndex  # noqa: E402

PAGE = (Path(__file__).parent / "review_playtest_labels.html").read_text(encoding="utf-8")


def make_handler(args, labels_path: Path, options: list[dict], known: set[str]):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args) -> None:      # noqa: D102 - im lang, khong spam console
            pass

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, data: dict) -> None:
            self._send(code, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self) -> None:                   # noqa: N802
            if self.path in ("/", "/index.html"):
                return self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            if self.path == "/api/state":
                data = json.loads(labels_path.read_text(encoding="utf-8"))
                return self._json(200, {"labels": data, "options": options,
                                        "path": str(labels_path), "has_video": bool(args.video)})
            if self.path.startswith("/file/"):
                target = (ROOT / self.path[len("/file/"):]).resolve()
                if not target.is_file() or ROOT not in target.parents:
                    return self._send(404, b"not found", "text/plain")
                return self._send(200, target.read_bytes(), "image/jpeg")
            self._send(404, b"not found", "text/plain")

        def do_POST(self) -> None:                  # noqa: N802
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")

            if self.path == "/api/resolve":
                return self._json(200, {"api": resolve_slot(payload.get("text", ""), options)})

            if self.path == "/api/snapshot":
                if not args.video:
                    return self._json(400, {"error": "chưa truyền --video nên không chụp được ảnh"})
                try:
                    rel = capture_snapshot(args.video, float(payload["at_s"]),
                                           labels_path.parent / "snapshots" / labels_path.stem, "manual")
                    return self._json(200, {"snapshot": Path(rel).resolve().relative_to(ROOT).as_posix()})
                except Exception as exc:            # noqa: BLE001 - loi nao cung phai hien ra trang
                    return self._json(400, {"error": str(exc)})

            if self.path == "/api/save":
                _, errors = save_payload(payload, labels_path, known)
                if errors:
                    return self._json(200, {"ok": False, "errors": errors})
                verified = sum(1 for s in from_dict(payload).screens if s.verified)
                print(f"đã lưu {labels_path.name} — {verified} màn verified", flush=True)
                return self._json(200, {"ok": True, "verified": verified})

            self._json(404, {"error": "không có endpoint này"})

    return Handler


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Xem lại và sửa nhãn playtest trong trình duyệt")
    ap.add_argument("labels")
    ap.add_argument("--video", help="để chụp thêm ảnh cho offer chèn tay")
    ap.add_argument("--name-index", default="data/name_index.json")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args(argv)

    labels_path = Path(args.labels).resolve()
    if not labels_path.is_file():
        print(f"không thấy file nhãn: {labels_path}")
        return 1

    index = NameIndex.load(args.name_index)
    options = augment_options(index)
    known = set(index.display.get("augments", {}))

    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(args, labels_path, options, known))
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Mở {url} để xem lại {labels_path.name}. Ctrl+C để dừng.")
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
