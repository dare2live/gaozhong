"""词汇 exam_status 热力图聚合 (4 象限 × 首字母).

单一计算点 (Rule 1): 从 nodes.attrs.exam_status (已由 audit/exam_coverage 算好) 聚合一次;
原 inline 在 api/routes/heatmap.py 路由里写 GROUP BY (Rule 1 smell), 下沉到此 service。
"""
from __future__ import annotations

import duckdb

_LEGEND = {
    "core":     {"color": "#0a4d75", "hint": "课标+高考双印证, 必教"},
    "standard": {"color": "#7aa6c2", "hint": "课标内, 真题未出, 常规"},
    "HV_extra": {"color": "#c0392b", "hint": "超纲但考过, 必教★"},
    "LV_extra": {"color": "#bdbdbd", "hint": "超纲不考, 选学"},
}


def vocab_status_heatmap(con: duckdb.DuckDBPyConnection) -> dict:
    """词 exam_status × 首字母 → {letters, cells[letter][status], totals, legend}."""
    rows = con.execute("""
        SELECT UPPER(SUBSTR(label, 1, 1)) AS letter,
               json_extract_string(attrs_json, 'exam_status') AS status,
               COUNT(*) AS n
        FROM nodes
        WHERE node_type = 'word'
          AND json_extract_string(attrs_json, 'exam_status') IS NOT NULL
        GROUP BY letter, status
        ORDER BY letter, status
    """).fetchall()
    cells: dict[str, dict[str, int]] = {}
    totals = {"core": 0, "standard": 0, "HV_extra": 0, "LV_extra": 0}
    for letter, status, n in rows:
        cells.setdefault(letter, {})[status] = n
        totals[status] = totals.get(status, 0) + n
    return {"letters": sorted(cells), "cells": cells, "totals": totals, "legend": _LEGEND}
