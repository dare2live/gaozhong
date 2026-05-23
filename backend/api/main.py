"""最小 HTTP server (stdlib only). 路由由 routes/*.py 自动注册.

启动:  python3 backend/api/main.py [--port 8765]
访问:  http://127.0.0.1:8765/  (前端首页)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from backend.api.routes import ALL_ROUTES  # noqa: E402

FRONTEND_DIR = ROOT / "frontend"

MIME_MAP = {
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".png": "image/png",
    ".pdf": "application/pdf",
}


def guess_mime(name: str) -> str:
    for ext, mime in MIME_MAP.items():
        if name.endswith(ext):
            return mime
    return "application/octet-stream"


class Handler(BaseHTTPRequestHandler):
    server_version = "gaozhong/0.2"

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {fmt % args}\n")

    # do_GET dispatches: static (/, /static/*, textbook pdf) → API route (ALL_ROUTES) → 404
    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)
        try:
            if self._try_static(path):
                return
            if self._try_textbook_pdf(path):
                return
            self._dispatch_api(path, qs)
        except Exception as e:
            self._json(500, {"error": str(e), "type": type(e).__name__})

    # --- dispatch helpers ---
    def _try_static(self, path: str) -> bool:
        if path == "/" or path == "/index.html":
            self._send_file(FRONTEND_DIR / "index.html", "text/html; charset=utf-8")
            return True
        if path == "/student" or path == "/student.html":
            self._send_file(FRONTEND_DIR / "student.html", "text/html; charset=utf-8")
            return True
        if path.startswith("/static/"):
            self._send_file(FRONTEND_DIR / "static" / path[len("/static/"):],
                            guess_mime(path))
            return True
        return False

    def _try_textbook_pdf(self, path: str) -> bool:
        m = re.match(r"^/api/textbooks/([^/]+)/([^/]+)/pdf$", path)
        if not m:
            return False
        ver, vol = unquote(m.group(1)), unquote(m.group(2))
        pdf = ROOT / "data" / "textbooks" / ver / f"{vol}.pdf"
        if not pdf.exists():
            self._json(404, {"error": "not found", "path": str(pdf)})
        else:
            self._send_file(pdf, "application/pdf")
        return True

    def _dispatch_api(self, path: str, qs: dict) -> None:
        handler = ALL_ROUTES.get(path)
        if handler is None:
            self._json(404, {"error": "no route", "path": path,
                              "available": sorted(ALL_ROUTES) + ["/", "/static/*",
                              "/api/textbooks/<ver>/<vol>/pdf"]})
            return
        try:
            body = handler(qs)
        except FileNotFoundError as e:
            self._json(503, {"error": str(e)})
            return
        self._json(200, body)

    # --- response helpers ---
    def _json(self, status: int, body) -> None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _send_file(self, path: Path, mime: str) -> None:
        if not path.exists() or not path.is_file():
            self._json(404, {"error": "file not found", "path": str(path)})
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"serving http://{args.host}:{args.port}")
    print(f"routes: {sorted(ALL_ROUTES)}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
