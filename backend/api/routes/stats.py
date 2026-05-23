"""GET /api/stats — 跨表概览, 用于前端首页 cards."""
from __future__ import annotations

from backend.api.db import db_ro


def api_stats(_qs: dict) -> dict:
    con = db_ro()
    try:
        s: dict = {}
        for tbl in [
            "cefr_vocab", "grammar_items", "theme_contexts",
            "liaoning_allowed_publishers", "liaoning_city_textbook_choice",
            "textbooks", "file_manifest", "nodes", "edges",
            "exam_questions", "audit_findings",
        ]:
            s[tbl] = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        s["vocab_by_level"] = dict(con.execute(
            "SELECT cefr_level, COUNT(*) FROM cefr_vocab GROUP BY cefr_level"
        ).fetchall())
        s["cities_by_publisher"] = dict(con.execute(
            "SELECT publisher_short, COUNT(*) FROM liaoning_city_textbook_choice "
            "WHERE subject = '英语' GROUP BY publisher_short"
        ).fetchall())
        s["exam_by_province"] = dict(con.execute(
            "SELECT province, COUNT(*) FROM exam_questions GROUP BY province"
        ).fetchall())
        s["audit_by_severity"] = dict(con.execute(
            "SELECT severity, COUNT(*) FROM audit_findings GROUP BY severity"
        ).fetchall())
        s["edges_by_relation"] = dict(con.execute(
            "SELECT relation, COUNT(*) FROM edges GROUP BY relation ORDER BY COUNT(*) DESC"
        ).fetchall())
        return s
    finally:
        con.close()


ROUTES = {"/api/stats": api_stats}
