"""GET /api/heatmap/vocab — 4 象限 × 首字母 词分布 (前端热力图源).

单一计算点 (Rule 1): 聚合下沉 backend.services.heatmap.vocab_status_heatmap, API 只读不重算。
"""
from __future__ import annotations

from backend.api.db import db_ro
from backend.services.heatmap import vocab_status_heatmap


def api_heatmap_vocab(_qs: dict) -> dict:
    con = db_ro()
    try:
        return vocab_status_heatmap(con)
    finally:
        con.close()


def api_heatmap_words_by_status(qs: dict) -> list[dict]:
    """Drill-down: 按 status 列出 word 详情."""
    status = qs.get("status", ["HV_extra"])[0]
    letter = qs.get("letter", [None])[0]
    try:
        limit = min(int(qs.get("limit", ["100"])[0]), 500)
    except ValueError:
        limit = 100
    where = ["node_type='word'",
             "json_extract_string(attrs_json, 'exam_status')=?"]
    args = [status]
    if letter:
        where.append("UPPER(SUBSTR(label, 1, 1))=?")
        args.append(letter.upper())
    con = db_ro()
    try:
        sql = ("SELECT label AS word, attrs_json FROM nodes WHERE "
               + " AND ".join(where) + " ORDER BY label LIMIT ?")
        args.append(limit)
        rows = con.execute(sql, args).fetchall()
        return [{"word": r[0], "attrs": r[1]} for r in rows]
    finally:
        con.close()


ROUTES = {
    "/api/heatmap/vocab": api_heatmap_vocab,
    "/api/heatmap/words_by_status": api_heatmap_words_by_status,
}
