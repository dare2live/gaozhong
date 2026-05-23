"""GET /api/heatmap/vocab — 4 象限 × 首字母 词分布 (前端热力图源)."""
from __future__ import annotations

from backend.api.db import db_ro


def api_heatmap_vocab(_qs: dict) -> dict:
    con = db_ro()
    try:
        # 用 word.attrs.exam_status (已由 audit/exam_coverage 算好)
        rows = con.execute("""
            SELECT
                UPPER(SUBSTR(label, 1, 1)) AS letter,
                json_extract_string(attrs_json, 'exam_status') AS status,
                COUNT(*) AS n
            FROM nodes
            WHERE node_type='word'
              AND json_extract_string(attrs_json, 'exam_status') IS NOT NULL
            GROUP BY letter, status
            ORDER BY letter, status
        """).fetchall()
        # cells[letter][status] = n
        cells: dict[str, dict[str, int]] = {}
        totals = {"core": 0, "standard": 0, "HV_extra": 0, "LV_extra": 0}
        for letter, status, n in rows:
            cells.setdefault(letter, {})[status] = n
            totals[status] = totals.get(status, 0) + n
        return {
            "letters": sorted(cells),
            "cells": cells,
            "totals": totals,
            "legend": {
                "core":     {"color": "#0a4d75", "hint": "课标+高考双印证, 必教"},
                "standard": {"color": "#7aa6c2", "hint": "课标内, 真题未出, 常规"},
                "HV_extra": {"color": "#c0392b", "hint": "超纲但考过, 必教★"},
                "LV_extra": {"color": "#bdbdbd", "hint": "超纲不考, 选学"},
            },
        }
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
