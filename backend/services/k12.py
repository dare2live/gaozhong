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


def stage_unstaged_disclosure(con: duckdb.DuckDBPyConnection) -> dict:
    """未分阶 word 披露 (审计MEDIUM 防静默截断): stage 分布只覆盖有 at_stage 边的词;
    校本超纲(LV/HV_extra)+课标变形(词形变体) 无标准阶段 — 显式告知, 不当'全词覆盖'。"""
    total = con.execute("SELECT COUNT(*) FROM nodes WHERE node_type='word'").fetchone()[0]
    # 只数 word 节点的 at_stage (at_stage 也连 grammar→stage; 混算会让 staged 虚高, unstaged≠by_reason 求和)
    staged = con.execute(
        "SELECT COUNT(DISTINCT e.src_id) FROM edges e JOIN nodes n ON n.concept_id = e.src_id "
        "WHERE e.relation='at_stage' AND n.node_type='word'").fetchone()[0]
    by_reason = dict(con.execute(
        "SELECT CASE WHEN json_extract_string(attrs_json,'stage')='课标变形' THEN '课标变形' "
        "            ELSE '校本超纲' END AS reason, COUNT(*) "
        "FROM nodes n WHERE n.node_type='word' "
        "AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.relation='at_stage' AND e.src_id=n.concept_id) "
        "GROUP BY 1").fetchall())
    return {"total_words": total, "staged": staged, "unstaged": total - staged,
            "unstaged_by_reason": by_reason,
            "note": "stage 分布覆盖有标准阶段的词; 校本超纲/课标变形词无标准阶段, 不计入(诚实非静默)"}


def blueprint(con: duckdb.DuckDBPyConnection) -> dict:
    """10维语法蓝图: 初中 grammar → 高中 deepens 边 (中考语篇填空∩高考语法填空衔接)."""
    rows = con.execute(
        "SELECT sj.label, sh.label FROM edges e "
        "JOIN nodes sj ON sj.concept_id = e.src_id "
        "JOIN nodes sh ON sh.concept_id = e.dst_id "
        "WHERE e.relation='deepens' ORDER BY sj.label"
    ).fetchall()
    return {"pairs": [{"junior": j, "senior": h} for j, h in rows], "n": len(rows),
            # 后端审计#8 诚实化: deepens 边是初中课标语法附录按术语匹配高中同名/别名点(全71对, 含自映射+别名),
            # 非"高考语法填空考点全集 N=2实证"——50/71 在中考语篇填空10空之外, 属通用语法taxonomy衔接。
            "basis": "初中↔高中 同名/别名语法点衔接 (deepens; 初中课标语法附录按术语匹配高中同名点, 71对)。"
                     "注: 非'高考语法填空考点全集'——多数在中考语篇填空10空之外, 为通用语法 taxonomy 衔接。",
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
    pivot = _kaodian_pivot(kaodian)  # 逐空 pivot (空号×年) 单算点, 前端禁重pivot (铁律1)
    return {
        "exam_type": "中考", "province": "辽宁", "paper": "辽宁省统一(2024起)", "years": [2024, 2025],
        "by_question_type": [{"type": t, "n": n} for t, n in by_type],
        "语篇填空考点": [{"year": y, "qid": q, "考点": a} for y, q, a in kaodian],
        "语篇填空_pivot": pivot,
        "data_honesty": ("题型骨架完整, 但题面/答案部分门控 — "
                         "2024 题面免费源全门控(仅官方答案可得), 2025 部分小题答案待补; 见 content_status"),
    }


def _kaodian_pivot(kaodian: list) -> dict:
    """语篇填空逐空 pivot: 空号(qid末段) × 年 → 考点. 单算点 reshape (前端禁重pivot, 铁律1).

    辽宁中考语篇填空固定每年 10 空(31-40), 每空 1 语法考点。年列从数据派生(不 hardcode); 缺空留空串.
    后端审计#8: 行键=空号仅为呈现, **同一空号逐年语法维度可不同**(非"同空逐年考同点"); "换词不换维"
    只在维度集合层成立(2024/2025 维度 ∩=10)。中考语篇填空≈高考语法填空考点全集(N=2 实证, 高考侧仅2021有逐空标签).
    """
    by_blank: dict[str, dict] = {}
    for y, q, a in kaodian:
        blank = q.rsplit("-", 1)[-1]
        by_blank.setdefault(blank, {})[str(y)] = a
    years = sorted({str(y) for y, _, _ in kaodian})
    blanks = sorted(by_blank, key=lambda b: int(b) if b.isdigit() else 0)
    return {
        "years": years,
        "rows": [{"blank": b, "考点": {yr: by_blank[b].get(yr, "") for yr in years}} for b in blanks],
        # 审计#8 诚实化: 逐空逐年考点(同空号逐年维度可不同, 行键仅呈现); "换词不换维"是维度集合层(∩=10), 非逐空。
        "basis": "辽宁中考语篇填空逐空逐年考点 (N=2: 2024/2025 省统一卷)。注: 同一空号逐年语法维度可不同, "
                 "'换词不换维'在维度集合层成立(两年∩=10维); ≈高考语法填空考点全集(高考侧仅2021逐空标签)。",
    }
