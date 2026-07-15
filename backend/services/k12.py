"""K12 衔接派生 (域A; inc4 单一计算点). stage 分布 / 10维语法蓝图 / 中考分布.

全读已落库真相 (at_stage 边 / deepens 边 / zhongkao_questions 视图), 前端禁重算 (铁律1)。
"""
from __future__ import annotations

import duckdb

_STAGE_ORDER = ["小学", "初中", "义务教育", "高中必修", "高中选修"]


def _zhongkao_years(con: duckdb.DuckDBPyConnection) -> list[int]:
    """中考年份列表 — 读 zhongkao_questions 现算 (不 hardcode 2024/2025)."""
    return [int(y) for (y,) in con.execute(
        "SELECT DISTINCT year FROM zhongkao_questions WHERE year IS NOT NULL ORDER BY 1"
    ).fetchall()]


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


def tested_word_stage_distribution(con: duckdb.DuckDBPyConnection) -> dict:
    """辽宁高考**离散考点题型考查词(去重)** 按学段分布 — "用最少课程覆盖最大考点" 实证 (北极星 Phase B).

    口径 (D0 诚实): 考查 = tests_word 边 ∧ province 辽宁 ∧ TESTED_QTYPES (出现≠考查, 根因A);
    学段 = at_stage 边 (word→学段, 单一计算点 §7); 无 at_stage 边的词标"未分类"(校本超纲/外省词, 不估算, 坑6)。
    foundation = 小学+初中+义务教育 (≤初中), senior = 高中必修+选修。返回 {stages, total, foundation_pct, senior_pct, unclassified_pct}.
    """
    from backend.services.exam_vocab import TESTED_QTYPES
    qmarks = ",".join("?" * len(TESTED_QTYPES))
    rows = con.execute(
        "WITH tw AS ("
        "  SELECT DISTINCT SUBSTR(e.dst_id,6) AS word FROM edges e "
        "  JOIN exam_questions q ON q.question_id = SUBSTR(e.src_id,10) "
        f"  WHERE e.relation='tests_word' AND q.province LIKE '辽宁%' AND q.question_type IN ({qmarks})) "
        "SELECT COALESCE(SUBSTR(es.dst_id,7),'未分类') AS stage, COUNT(*) AS n "
        "FROM tw LEFT JOIN edges es ON 'word:'||tw.word=es.src_id AND es.relation='at_stage' GROUP BY 1",
        list(TESTED_QTYPES),
    ).fetchall()
    counts = {s: int(n) for s, n in rows}
    total = sum(counts.values())
    if total == 0:
        return {"stages": [], "total": 0, "foundation_pct": 0.0, "senior_pct": 0.0, "unclassified_pct": 0.0}
    pct = lambda n: round(100.0 * n / total, 1)
    order = _STAGE_ORDER + ["未分类"]
    # "义务教育" 残档 = 义务课标词但未细分到小学/初中 (如 april/analyse); 非与小初重叠, 显式标"未细分"避混淆 (用户反馈)
    disp = {"义务教育": "义务·未细分(小初)"}
    stages = [{"stage": disp.get(s, s), "raw_stage": s, "n": counts[s], "pct": pct(counts[s])} for s in order if counts.get(s)]
    grp = lambda ks: pct(sum(counts.get(k, 0) for k in ks))
    return {
        "stages": stages, "total": total,
        "foundation_pct": grp(["小学", "初中", "义务教育"]),  # 义务教育阶段 = 小学+初中+义务未细分 (≤初中, 入高中前已学)
        "senior_pct": grp(["高中必修", "高中选修"]),
        "unclassified_pct": pct(counts.get("未分类", 0)),
        "stage_note": "小学/初中/义务·未细分 同属义务教育阶段(入高中前已学); '义务·未细分'=义务课标词未细分到小初的残档, 非重叠。foundation=三者合计。",
    }


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
        "exam_type": "中考", "province": "辽宁", "paper": "辽宁省统一(2024起)", "years": _zhongkao_years(con),
        "by_question_type": [{"type": t, "n": n} for t, n in by_type],
        "语篇填空考点": [{"year": y, "qid": q, "考点": a} for y, q, a in kaodian],
        "语篇填空_pivot": pivot,
        "data_honesty": ("题型骨架完整, 但答案部分门控 — "
                         "2024/2025 全45题题面+答案齐全(2025答案补自教习网同步解析; 44/45主观标略); 见 content_status"),
    }


def _exam_point_dim_dist(con: duckdb.DuckDBPyConnection, dimension: str) -> list[dict]:
    """中考 tests_exam_point 边按维度(genre/theme_l2)分布 (Rule1: 只读聚合已有边, 不重分类)."""
    rows = con.execute(
        "SELECT n.label, COUNT(DISTINCT e.src_id) FROM edges e JOIN nodes n ON n.concept_id = e.dst_id "
        "WHERE e.relation='tests_exam_point' AND e.src_id LIKE 'question:ZK-%' "
        "AND json_extract_string(e.evidence_json, '$.dimension') = ? "
        "GROUP BY n.label ORDER BY 2 DESC", [dimension],
    ).fetchall()
    return [{"label": lb, "n": n} for lb, n in rows]


def _grammar_focus(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """中考 tests_grammar 边命中的初中语法点 (Rule1: 只读聚合, 复用 junior/grammar.py 已建边)."""
    rows = con.execute(
        "SELECT n.label, COUNT(*) FROM edges e JOIN nodes n ON n.concept_id = e.dst_id "
        "WHERE e.relation='tests_grammar' AND e.src_id LIKE 'question:ZK-%' "
        "GROUP BY n.label ORDER BY 2 DESC",
    ).fetchall()
    return [{"grammar_item": lb, "n": n} for lb, n in rows]


def _vocab_focus(con: duckdb.DuckDBPyConnection, top_n: int = 30) -> list[dict]:
    """中考 tests_word 边命中的高频实词 (Rule1: 只读聚合 junior/qbank.py 已建边, 不重新分词)."""
    rows = con.execute(
        "SELECT split_part(dst_id, ':', 2) AS word, COUNT(*) AS n FROM edges "
        "WHERE relation='tests_word' AND src_id LIKE 'question:ZK-%' "
        "GROUP BY word ORDER BY n DESC LIMIT ?", [top_n],
    ).fetchall()
    return [{"word": w, "n": n} for w, n in rows]


def zhongkao_exam_point_summary(con: duckdb.DuckDBPyConnection) -> dict:
    """中考考查重点(Phase F2, 2026-07-08用户拍板"颗粒度对标高考的考点分析, 不复刻设问思维").

    设计原则: 不照搬高考cognitive_skill(设问思维)维度——中考题型结构与高考不同, 生搬会失真;
    改用中考实际能支撑的三条已有边做"考什么"的静态分布(非趋势): genre/theme_l2(题材主题,
    覆盖48/90题, 见exam_point.py)+ tests_grammar(语篇填空语法点, 20题样本)+ tests_word
    (高频实词, 90题全覆盖)。全部只读聚合已有边(Rule1), 不重新分类/分词。

    样本量诚实(坑12): 2024/2025共2年, 只做"分布"结论(同卷制静态占比), 不做逐年"趋势"
    (需≥5年每年≥10题, 现远不够, 见 docs/RESUME.md 中考子系统scope note); genre/theme_l2
    基数48题(11篇一致文章)相对90题库是部分覆盖, 不代表全部90题题材分布, 显式标注避免过度外推。
    """
    return {
        "exam_type": "中考", "province": "辽宁", "years": _zhongkao_years(con),
        "genre_分布": _exam_point_dim_dist(con, "genre"),
        "theme_l2_分布": _exam_point_dim_dist(con, "theme_l2"),
        "语法考查重点": _grammar_focus(con),
        "高频实词": _vocab_focus(con),
        "scope_note": {
            "sample_type": "分布(distribution), 非趋势(trend) — 仅2年数据, 不支持逐年趋势结论",
            "genre_theme_coverage": "48/90题(11篇双独立视角一致的文章), 非全部90题题材覆盖",
            "grammar_coverage": "20题语篇填空样本, 相对71个课标语法点是验证性附注非频次代表",
            "vocab_coverage": "90题全覆盖(tests_word边基于全部真实题面), 已排除功能词(见stopwords.py)",
        },
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
