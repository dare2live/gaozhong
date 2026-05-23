"""最小 HTTP API + 静态文件 server (stdlib only, 零新增依赖).

启动:  python3 backend/api/main.py [--port 8765]
访问:  http://127.0.0.1:8765/  (前端首页)
       http://127.0.0.1:8765/api/...   (JSON API)

路由 (MVP, 都只读, 配合 frontend/index.html 展示 truth source):
  GET /api/stats
  GET /api/cefr_vocab?level=义教|必修|选必&prefix=ab&limit=100
  GET /api/grammar_items
  GET /api/theme_contexts
  GET /api/liaoning/allowed_publishers
  GET /api/liaoning/city_choice
  GET /api/textbooks
  GET /api/textbooks/{version_key}/{volume_key}/pdf   (静态送 PDF)
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
# Allow `from backend.services import ...` when started as `python3 backend/api/main.py`
sys.path.insert(0, str(ROOT))

import duckdb  # noqa: E402
DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"
FRONTEND_DIR = ROOT / "frontend"


def db_ro() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"DB 不存在, 先跑 python3 scripts/init_db.py — {DB_PATH}")
    return duckdb.connect(str(DB_PATH), read_only=True)


def rows_to_dicts(cur) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def api_stats(_qs: dict) -> dict:
    con = db_ro()
    try:
        s = {}
        for tbl in [
            "cefr_vocab", "grammar_items", "theme_contexts",
            "liaoning_allowed_publishers", "liaoning_city_textbook_choice",
            "textbooks", "file_manifest", "nodes", "edges",
            "exam_questions", "audit_findings",
        ]:
            s[tbl] = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        s["vocab_by_level"] = dict(
            con.execute("SELECT cefr_level, COUNT(*) FROM cefr_vocab GROUP BY cefr_level").fetchall()
        )
        s["cities_by_publisher"] = dict(
            con.execute(
                "SELECT publisher_short, COUNT(*) FROM liaoning_city_textbook_choice "
                "WHERE subject = '英语' GROUP BY publisher_short"
            ).fetchall()
        )
        s["exam_by_province"] = dict(
            con.execute("SELECT province, COUNT(*) FROM exam_questions GROUP BY province").fetchall()
        )
        s["audit_by_severity"] = dict(
            con.execute("SELECT severity, COUNT(*) FROM audit_findings GROUP BY severity").fetchall()
        )
        s["edges_by_relation"] = dict(
            con.execute("SELECT relation, COUNT(*) FROM edges GROUP BY relation ORDER BY COUNT(*) DESC").fetchall()
        )
        return s
    finally:
        con.close()


def api_cefr_vocab(qs: dict) -> list[dict]:
    level = qs.get("level", [None])[0]
    prefix = qs.get("prefix", [""])[0].lower()
    try:
        limit = min(int(qs.get("limit", ["200"])[0]), 1000)
    except ValueError:
        limit = 200
    where = []
    args: list = []
    if level:
        where.append("cefr_level = ?")
        args.append(level)
    if prefix:
        where.append("word LIKE ?")
        args.append(prefix + "%")
    sql = "SELECT word, cefr_level, raw_suffix FROM cefr_vocab"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY word LIMIT ?"
    args.append(limit)
    con = db_ro()
    try:
        return rows_to_dicts(con.execute(sql, args))
    finally:
        con.close()


def api_grammar_items(_qs: dict) -> list[dict]:
    con = db_ro()
    try:
        return rows_to_dicts(con.execute(
            "SELECT grammar_item_id, category, label, cefr_level FROM grammar_items ORDER BY grammar_item_id"
        ))
    finally:
        con.close()


def api_theme_contexts(_qs: dict) -> list[dict]:
    con = db_ro()
    try:
        return rows_to_dicts(con.execute(
            "SELECT theme_context_id, level1, level2 FROM theme_contexts ORDER BY level1, level2 NULLS FIRST"
        ))
    finally:
        con.close()


def api_allowed_publishers(_qs: dict) -> list[dict]:
    con = db_ro()
    try:
        rows = rows_to_dicts(con.execute(
            "SELECT rank, chief_editor, publisher, book_title, volumes_json, source "
            "FROM liaoning_allowed_publishers WHERE subject = '英语' ORDER BY rank"
        ))
        for r in rows:
            r["volumes"] = json.loads(r.pop("volumes_json"))
        return rows
    finally:
        con.close()


def api_city_choice(_qs: dict) -> list[dict]:
    con = db_ro()
    try:
        return rows_to_dicts(con.execute(
            "SELECT city, publisher_short, source FROM liaoning_city_textbook_choice "
            "WHERE subject = '英语' ORDER BY publisher_short, city"
        ))
    finally:
        con.close()


def api_textbooks(_qs: dict) -> list[dict]:
    con = db_ro()
    try:
        return rows_to_dicts(con.execute(
            "SELECT version_key, volume_key, publisher_label, pdf_pages, pdf_rel_path, pdf_sha256 "
            "FROM textbooks ORDER BY version_key, volume_key"
        ))
    finally:
        con.close()


def api_audit_findings(_qs: dict) -> list[dict]:
    con = db_ro()
    try:
        return rows_to_dicts(con.execute(
            "SELECT audit_kind, severity, target, expected, actual, delta, note "
            "FROM audit_findings ORDER BY audit_kind, severity DESC"
        ))
    finally:
        con.close()


def api_graph_stats(_qs: dict) -> dict:
    from backend.services import graph as gsvc
    con = db_ro()
    try:
        return gsvc.stats(con)
    finally:
        con.close()


def api_graph_neighbors(qs: dict) -> list[dict]:
    from backend.services import graph as gsvc
    node = qs.get("node", [""])[0]
    if not node:
        return []
    rel = qs.get("relation", [None])[0]
    direction = qs.get("direction", ["out"])[0]
    try:
        limit = min(int(qs.get("limit", ["50"])[0]), 500)
    except ValueError:
        limit = 50
    con = db_ro()
    try:
        return gsvc.neighbors(con, node, rel, direction, limit)
    finally:
        con.close()


def api_exam_questions(qs: dict) -> list[dict]:
    province = qs.get("province", [None])[0]
    qtype = qs.get("type", [None])[0]
    year = qs.get("year", [None])[0]
    try:
        limit = min(int(qs.get("limit", ["20"])[0]), 200)
    except ValueError:
        limit = 20
    where, args = [], []
    if province:
        where.append("province LIKE ?"); args.append(f"%{province}%")
    if qtype:
        where.append("question_type = ?"); args.append(qtype)
    if year:
        where.append("year = ?"); args.append(int(year))
    sql = ("SELECT question_id, year, province, paper_type, question_type, "
           "SUBSTR(raw_question, 1, 200) AS preview, source_file, source_index "
           "FROM exam_questions")
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY year DESC, question_id LIMIT ?"
    args.append(limit)
    con = db_ro()
    try:
        return rows_to_dicts(con.execute(sql, args))
    finally:
        con.close()


ROUTES = {
    "/api/stats": api_stats,
    "/api/cefr_vocab": api_cefr_vocab,
    "/api/grammar_items": api_grammar_items,
    "/api/theme_contexts": api_theme_contexts,
    "/api/liaoning/allowed_publishers": api_allowed_publishers,
    "/api/liaoning/city_choice": api_city_choice,
    "/api/textbooks": api_textbooks,
    "/api/audit/findings": api_audit_findings,
    "/api/graph/stats": api_graph_stats,
    "/api/graph/neighbors": api_graph_neighbors,
    "/api/exam_questions": api_exam_questions,
}


class Handler(BaseHTTPRequestHandler):
    server_version = "gaozhong/0.1"

    def log_message(self, fmt, *args):  # quieter
        sys.stderr.write(f"[{self.log_date_time_string()}] {fmt % args}\n")

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self._serve_file(FRONTEND_DIR / "index.html", "text/html; charset=utf-8")
            return
        if path.startswith("/static/"):
            rel = path[len("/static/"):]
            self._serve_file(FRONTEND_DIR / "static" / rel, self._guess_mime(rel))
            return

        # serve textbook PDF: /api/textbooks/<version>/<volume>/pdf
        m = re.match(r"^/api/textbooks/([^/]+)/([^/]+)/pdf$", path)
        if m:
            ver, vol = unquote(m.group(1)), unquote(m.group(2))
            pdf = ROOT / "data" / "textbooks" / ver / f"{vol}.pdf"
            if not pdf.exists():
                self._json(404, {"error": "not found", "path": str(pdf)})
                return
            self._serve_file(pdf, "application/pdf")
            return

        handler = ROUTES.get(path)
        if handler is None:
            self._json(404, {"error": "no route", "path": path,
                              "available": sorted(ROUTES) + ["/", "/static/*",
                              "/api/textbooks/<ver>/<vol>/pdf"]})
            return
        try:
            body = handler(qs)
        except FileNotFoundError as e:
            self._json(503, {"error": str(e)})
            return
        except Exception as e:
            self._json(500, {"error": str(e), "type": type(e).__name__})
            return
        self._json(200, body)

    # --- helpers ---
    def _json(self, status: int, body):
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _serve_file(self, path: Path, mime: str):
        if not path.exists() or not path.is_file():
            self._json(404, {"error": "file not found", "path": str(path)})
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    @staticmethod
    def _guess_mime(name: str) -> str:
        if name.endswith(".css"): return "text/css; charset=utf-8"
        if name.endswith(".js"): return "application/javascript; charset=utf-8"
        if name.endswith(".html"): return "text/html; charset=utf-8"
        if name.endswith(".png"): return "image/png"
        if name.endswith(".pdf"): return "application/pdf"
        return "application/octet-stream"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    if not DB_PATH.exists():
        print(f"DB 不存在: {DB_PATH}", file=sys.stderr)
        print("先跑: python3 scripts/init_db.py", file=sys.stderr)
        sys.exit(1)
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"serving http://{args.host}:{args.port}  (Ctrl+C to stop)")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
