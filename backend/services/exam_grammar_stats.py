"""语法考点 + 固定搭配/句型/表达方式 统计 (北极星 真题特点扩展; 按小初高词同标准: 统计+热点+分析).

两源, 诚实分层 (坑16/坑12):
1. **语法考查 (真值)**: tests_grammar 边 ∧ 辽宁前缀 → grammar_items 课标层级第二级子类 (主从复合句/被动语态/
   非谓语/时态/句型/词法...)。锚官方课标层级 (不杜撰类别), 辽宁命题频次 = 热点。覆盖用户"句型/时态/复杂从句"。
2. **教材搭配/表达库 (出现非考查)**: phrases 表 (verb_phrase 固定搭配 / sentence_pattern 句型 / function_expression
   表达方式·功能意念)。**无短语级真题考查边 → 是教材出现库, 不冒充考查频次** (诚实标; 短语级考查标注=未来标注任务)。

全读已落库边/表 (铁律1)。数据真值, 算不出标 unknown。
"""
from __future__ import annotations

import duckdb

from backend.services.trend import scope

# phrase_type → 展示分组 (前缀匹配 function_expression:*)
_PHRASE_GROUP = (
    ("固定搭配 (动词短语)", "verb_phrase"),
    ("句型 (sentence pattern)", "sentence_pattern"),
    ("表达方式 (功能意念)", "function_expression"),
)

# 单一计算点 (Rule 5 可复用): 教材库出现非考查的诚实标注, phrase_library_stats + 教材单元视图共用同一句话。
PHRASE_LIB_NOTE = ("教材固定搭配/句型/表达方式库 (来自教材单元提取); **出现非考查** — "
                   "无短语级真题考查边, 不冒充考查频次(坑12); 短语级考查标注=未来任务。")


def grammar_category_pct(con: duckdb.DuckDBPyConnection, era: str | None = None) -> dict[str, float]:
    """{课标第二级子类 label: 辽宁卷考查占比%} — 供教材单元视图给某语法点标"考察重点"用.

    坑(2026-07-04 全数据审计坑12): 教材单元教的是**当前**课标, "考察重点"该反映当前卷制
    (era=scope.ERA_NEW, 2021+新高考II)而非默认混入历史(2015-2020旧课标II)数据。2026-07-09
    全网挖掘补齐2024/2025/2026语法填空题真实教研解析后(此前analysis字段空/机器占位文本,
    build_tests_grammar搜不到语法关键词无法建边), 2021+现有15条tests_grammar边(2024:4/
    2025:5/2026:6), eras_missing已归零, 本函数从"诚实返回空dict"状态转为serve真实占比;
    era=None(默认)=当前卷制; 未来若某卷制again无覆盖仍会诚实返回空dict(逻辑本身不变,
    只是当前实际有数据了), 不冒用历史占比。
    单一计算点: 复用 grammar_exam_stats 已算的 by_era (不重跑聚合 SQL, Rule 1)。
    """
    era = era or scope.ERA_NEW
    block = grammar_exam_stats(con)["by_era"].get(era)
    return {c["category"]: c["pct"] for c in block["by_category"]} if block else {}


def _grammar_stats_rows(con: duckdb.DuckDBPyConnection) -> tuple[list, dict]:
    """建边层无关的独立查询(单一计算点抽出, 降 grammar_exam_stats CC): 逐题×era×课标类目
    频次明细行 + era 去重题数。"""
    rows = con.execute(
        f"WITH tg AS ("
        f"  SELECT SUBSTR(e.dst_id, LENGTH('grammar:')+1) AS gid, e.src_id AS qid, "
        f"         {scope.era_sql('q.year')} AS era "
        f"  FROM edges e JOIN exam_questions q ON q.question_id = SUBSTR(e.src_id,10) "
        f"  WHERE e.relation='tests_grammar' AND q.province LIKE '辽宁%') "
        f"SELECT tg.era, cat.label AS category, gi.label AS item, COUNT(*) AS n "
        f"FROM tg JOIN grammar_items gi ON gi.grammar_item_id = tg.gid "
        f"LEFT JOIN grammar_items cat ON cat.grammar_item_id = "
        f"  CASE WHEN instr(tg.gid,'/')>0 THEN split_part(tg.gid,'/',1)||'/'||split_part(tg.gid,'/',2) ELSE tg.gid END "
        f"GROUP BY 1, 2, 3"
    ).fetchall()
    n_q_by_era = dict(con.execute(
        f"SELECT {scope.era_sql('q.year')} AS era, COUNT(DISTINCT e.src_id) "
        f"FROM edges e JOIN exam_questions q ON q.question_id = SUBSTR(e.src_id,10) "
        f"WHERE e.relation='tests_grammar' AND q.province LIKE '辽宁%' GROUP BY 1"
    ).fetchall())
    return rows, n_q_by_era


def _grammar_stats_block(cats: dict[str, dict], n_questions: int) -> dict:
    """一个 era(或跨era合并)切片 → {total,n_edges,n_questions,by_category}."""
    total = sum(c["n"] for c in cats.values())
    pct = lambda n: round(100.0 * n / total, 1) if total else 0.0
    ranked = sorted(cats.items(), key=lambda kv: kv[1]["n"], reverse=True)
    return {
        "total": total, "n_edges": total, "n_questions": int(n_questions),
        "by_category": [
            {"category": k, "n": v["n"], "pct": pct(v["n"]),
             "top": sorted(v["items"], key=lambda x: x["n"], reverse=True)[:4]}
            for k, v in ranked],
    }


def _grammar_stats_note(eras_covered: list[str], eras_missing: list[str]) -> str:
    if not eras_missing:
        return "全部卷制 era 均有覆盖。"
    return (f"辽宁语法考查真值目前仅覆盖 {'、'.join(eras_covered) or '无'}; "
            f"{'、'.join(eras_missing)} 暂无 tests_grammar 边(诚实标缺口, 非估算)。"
            f"上方 total/by_category 是跨全部有数据 era 的合并参考量, 精确到具体卷制"
            f"用 by_era 字段, 教材单元'考察重点'徽章按 grammar_category_pct(默认当前卷制) 取值。")


def grammar_exam_stats(con: duckdb.DuckDBPyConnection) -> dict:
    """辽宁语法考查 按卷制 era 分层 + 课标第二级子类 + 频次热点 + 每类 top 考点 (考查真值).

    坑(2026-07-04 全数据审计坑12分析诚实红线): 旧版不分 era 聚合全历史, 前端却展示不限 era
    的"真值"百分比, 与本项目其它维度(cognitive_skill/exam_point 分布)已有的 era 分层+
    缺口披露标准不一致, 改按 scope.era_sql() 分 era 各自算。2026-07-09: 此前2021+因
    build_tests_grammar对2024/2025/2026语法填空题的空/占位analysis文本关键词匹配结构性
    缺席(2021/2022自身也是EOL答案核验占位文本, 非真解析, 已确认结构性天花板不追), 全网
    挖掘补齐2024/2025/2026真实教研解析后2021+现有15条边, eras_missing已归零。顶层字段
    (total/by_category等)是**跨全部有数据的era合并**参考量, 要精确到具体卷制请用
    by_era[era]; eras_missing 诚实列出暂无覆盖的卷制(逻辑保留, 现为空列表), 不静默吞掉。

    口径 (D0 坑17): total/n_edges = tests_grammar∧辽宁 **边数** (一题可考多语法点, 频次口径);
    n_questions = COUNT(DISTINCT src_id) **去重题数** (题级口径)。两口径显式分离, 不混用。
    """
    rows, n_q_by_era = _grammar_stats_rows(con)
    by_era_raw: dict[str, dict[str, dict]] = {}
    for era, cat, item, n in rows:
        cats = by_era_raw.setdefault(era, {})
        c = cats.setdefault(cat or "其他", {"n": 0, "items": []})
        c["n"] += int(n)
        c["items"].append({"label": item, "n": int(n)})

    by_era = {era: _grammar_stats_block(cats, n_q_by_era.get(era, 0)) for era, cats in by_era_raw.items()}
    eras_covered = sorted(by_era.keys())
    eras_missing = [e for e in (scope.ERA_OLD, scope.ERA_NEW) if e not in eras_covered]
    combined_cats: dict[str, dict] = {}
    for cats in by_era_raw.values():
        for cat, v in cats.items():
            c = combined_cats.setdefault(cat, {"n": 0, "items": []})
            c["n"] += v["n"]
            c["items"].extend(v["items"])
    combined = _grammar_stats_block(combined_cats, sum(n_q_by_era.values()))
    return {
        **combined,
        "by_era": by_era,
        "eras_covered": eras_covered,
        "eras_missing": eras_missing,
        "note": _grammar_stats_note(eras_covered, eras_missing),
    }


def phrase_library_stats(con: duckdb.DuckDBPyConnection) -> dict:
    """教材固定搭配/句型/表达方式库 按类型分组 (出现非考查, 诚实标)."""
    raw = dict(con.execute("SELECT phrase_type, COUNT(*) FROM phrases GROUP BY 1").fetchall())
    groups = []
    for label, prefix in _PHRASE_GROUP:
        n = sum(v for k, v in raw.items() if (k or "").startswith(prefix))
        if n:
            groups.append({"group": label, "n": n})
    return {
        "total": sum(raw.values()),
        "by_group": groups,
        "note": PHRASE_LIB_NOTE,
    }


def expression_stats(con: duckdb.DuckDBPyConnection) -> dict:
    """合并: 语法考查(真值) + 教材搭配/表达库(出现非考查) — 真题特点页"语法/搭配/句型/时态/从句"扩展统计."""
    return {
        "scope": "辽宁卷语法考查(tests_grammar 真值) + 教材搭配/句型/表达库(phrases 出现非考查)",
        "grammar_exam": grammar_exam_stats(con),
        "textbook_expr": phrase_library_stats(con),
        "note": "语法考查=辽宁命题频次真值(锚课标第二级子类, 覆盖时态/从句/句型/词法); 搭配/表达=教材库(出现非考查, 诚实分层)。",
    }
