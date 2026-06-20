"""K12 衔接派生 (域A; inc4 单一计算点). stage 分布 / 10维语法蓝图 / 中考分布.

全读已落库真相 (at_stage 边 / deepens 边 / zhongkao_questions 视图), 前端禁重算 (铁律1)。
"""
from __future__ import annotations

import duckdb

_STAGE_ORDER = ["小学", "初中", "义务教育", "高中必修", "高中选修"]


def stage_distribution(con: duckdb.DuckDBPyConnection) -> dict:
    """各 stage 的知识点数 (从 at_stage 边; 单库 stage 维 materialize)."""
    rows = con.execute(
        "SELECT e.dst_id, n.node_type, COUNT(*) FROM edges e "
        "JOIN nodes n ON n.concept_id = e.src_id "
        "WHERE e.relation='at_stage' GROUP BY e.dst_id, n.node_type"
    ).fetchall()
    out: dict[str, dict] = {}
    for dst, nt, cnt in rows:
        out.setdefault(dst.split(":", 1)[1], {})[nt] = cnt
    return {s: out[s] for s in _STAGE_ORDER if s in out}


def blueprint(con: duckdb.DuckDBPyConnection) -> dict:
    """10维语法蓝图: 初中 grammar → 高中 deepens 边 (中考语篇填空∩高考语法填空衔接)."""
    rows = con.execute(
        "SELECT sj.label, sh.label FROM edges e "
        "JOIN nodes sj ON sj.concept_id = e.src_id "
        "JOIN nodes sh ON sh.concept_id = e.dst_id "
        "WHERE e.relation='deepens' ORDER BY sj.label"
    ).fetchall()
    return {"pairs": [{"junior": j, "senior": h} for j, h in rows], "n": len(rows),
            "basis": "中考语篇填空 = 高考语法填空考点全集 (N=2 省统一卷实证, zhongkao_gaokao_alignment.md)",
            "edge": "deepens (初中语法→高中深化)"}


def zhongkao_distribution(con: duckdb.DuckDBPyConnection) -> dict:
    """中考题型分布 + 语篇填空逐空考点 + 内容完整性 (从 zhongkao_questions 视图, exam_type=中考).

    content_status 单算点暴露 (审计HIGH#8 空心诚实): 前端据此显示「题面门控/答案待补」, 不当完整渲染。
    """
    by_type = con.execute(
        "SELECT question_type, COUNT(*) FROM zhongkao_questions GROUP BY 1 ORDER BY 2 DESC").fetchall()
    kaodian = con.execute(
        "SELECT year, question_id, analysis FROM zhongkao_questions "
        "WHERE analysis IS NOT NULL AND question_type LIKE '语篇填空%' ORDER BY question_id").fetchall()
    status = dict(con.execute(
        "SELECT content_status, COUNT(*) FROM zhongkao_questions GROUP BY 1").fetchall())
    return {
        "exam_type": "中考", "province": "辽宁", "paper": "辽宁省统一(2024起)", "years": [2024, 2025],
        "by_question_type": [{"type": t, "n": n} for t, n in by_type],
        "语篇填空考点": [{"year": y, "qid": q, "考点": a} for y, q, a in kaodian],
        "content_status": status,
        "data_honesty": ("题型骨架完整, 但题面/答案部分门控 — "
                         "2024 题面免费源全门控(仅官方答案可得), 2025 部分小题答案待补; 见 content_status"),
    }
