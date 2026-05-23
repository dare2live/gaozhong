"""GET /api/textbooks 列表 + /api/textbooks/<ver>/<vol>/pdf 静态送 PDF."""
from __future__ import annotations

from backend.api.db import db_ro, rows_to_dicts


def api_textbooks(_qs: dict) -> list[dict]:
    con = db_ro()
    try:
        return rows_to_dicts(con.execute(
            "SELECT version_key, volume_key, publisher_label, pdf_pages, pdf_rel_path, pdf_sha256 "
            "FROM textbooks ORDER BY version_key, volume_key"
        ))
    finally:
        con.close()


ROUTES = {"/api/textbooks": api_textbooks}
# Note: /api/textbooks/<ver>/<vol>/pdf 是动态路由, 在 main.Handler.do_GET 里直接处理 (static file).
