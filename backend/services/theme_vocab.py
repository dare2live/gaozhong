"""主题特征词汇关联性 (件3 知识点关联性扩展; docs/kg_layer_design §2 词汇维↔主题维).

把 4441 词的词汇层接到主题维: 哪些词是某主题的**特征词**(辽宁真题里区分度高)。
单一计算点 build_theme_vocabulary → characterizes_theme 边。
- 区分度 = co(w,t)/total(w): 词 w 的出现里, 落在主题 t 的比例 (功能词 get/make 处处出现→区分度低→滤除, 坑5)。
- §7 辽宁锚定 + co≥3 守门(防一次性) + 词必在考试词典(real exam word, 滤噪声)。
- provenance=distinctiveness_heuristic: 启发式非权威(教研未逐词标主题), 诚实标记。
"""
from __future__ import annotations

import json

import duckdb

_SQL = """
WITH lnq AS (SELECT 'question:' || question_id AS qid FROM exam_questions WHERE province LIKE '辽宁%'),
wt AS (SELECT tw.dst_id AS w, te.dst_id AS t, COUNT(DISTINCT tw.src_id) AS co
       FROM edges tw JOIN edges te ON tw.src_id = te.src_id AND te.relation = 'tests_exam_point'
       JOIN lnq ON lnq.qid = tw.src_id
       WHERE tw.relation = 'tests_word' AND te.dst_id LIKE 'exam_point:theme_l2%'
       GROUP BY 1, 2),
tot AS (SELECT tw.dst_id AS w, COUNT(DISTINCT tw.src_id) AS total
        FROM edges tw JOIN lnq ON lnq.qid = tw.src_id WHERE tw.relation = 'tests_word' GROUP BY 1)
SELECT wt.w, wt.t, wt.co, ROUND(wt.co * 1.0 / tot.total, 3) AS dist
FROM wt JOIN tot ON tot.w = wt.w
WHERE wt.co >= ? AND wt.co * 1.0 / tot.total >= ?
  AND EXISTS (SELECT 1 FROM exam_vocabulary ev WHERE 'word:' || ev.word = wt.w)
"""


def build_theme_vocabulary(con: duckdb.DuckDBPyConnection, min_co: int = 3,
                           min_dist: float = 0.6) -> dict:
    """主题特征词 → characterizes_theme 边 (辽宁区分度, 单一计算点)."""
    con.execute("DELETE FROM edges WHERE relation = 'characterizes_theme'")
    rows = con.execute(_SQL, [min_co, min_dist]).fetchall()
    for w, t, co, dist in rows:
        con.execute(
            "INSERT INTO edges (src_id, dst_id, relation, weight, evidence_json) VALUES (?, ?, ?, ?, ?)",
            [w, t, "characterizes_theme", float(dist),
             json.dumps({"co": co, "dist": dist, "provenance": "distinctiveness_heuristic",
                         "scope": "辽宁卷"}, ensure_ascii=False)])
    n_theme = con.execute(
        "SELECT COUNT(DISTINCT dst_id) FROM edges WHERE relation='characterizes_theme'").fetchone()[0]
    return {"characterizes_theme 边": len(rows), "覆盖主题数": n_theme, "min_co": min_co, "min_dist": min_dist}
