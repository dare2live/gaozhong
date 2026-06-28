"""课标 (普通高中英语课程标准) API.

GET /api/theme_contexts     — 主题语境 (level1/level2 层级)
GET /api/curriculum/summary — 课标库概览计数 (主题/语法/词汇按学段; 课标库页用, 轻量不拉全词表)
"""
from __future__ import annotations

from backend.api.db import db_ro, rows_to_dicts


def api_theme_contexts(_qs: dict) -> list[dict]:
    con = db_ro()
    try:
        return rows_to_dicts(con.execute(
            "SELECT theme_context_id, level1, level2 FROM theme_contexts "
            "ORDER BY level1, level2 NULLS FIRST"
        ))
    finally:
        con.close()


def api_curriculum_summary(_qs: dict) -> dict:
    """课标库概览: 主题/语法总数 + 词汇按 cefr 学段计数 (live 计数, 不 hardcode; 课标库页轻量入口)."""
    con = db_ro()
    try:
        themes = con.execute("SELECT COUNT(*) FROM theme_contexts").fetchone()[0]
        grammar = con.execute("SELECT COUNT(*) FROM grammar_items").fetchone()[0]
        vocab = dict(con.execute("SELECT cefr_level, COUNT(*) FROM cefr_vocab GROUP BY 1").fetchall())
    finally:
        con.close()
    return {
        "source": "普通高中英语课程标准 (2017年版2020年修订)",
        "themes_total": themes, "grammar_total": grammar,
        "vocab_by_level": vocab, "vocab_total": sum(vocab.values()),
    }


ROUTES = {
    "/api/theme_contexts": api_theme_contexts,
    "/api/curriculum/summary": api_curriculum_summary,
}
