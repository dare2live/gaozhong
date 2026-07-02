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

# phrase_type → 展示分组 (前缀匹配 function_expression:*)
_PHRASE_GROUP = (
    ("固定搭配 (动词短语)", "verb_phrase"),
    ("句型 (sentence pattern)", "sentence_pattern"),
    ("表达方式 (功能意念)", "function_expression"),
)


def grammar_exam_stats(con: duckdb.DuckDBPyConnection) -> dict:
    """辽宁语法考查 按课标第二级子类 + 频次热点 + 每类 top 考点 (考查真值).

    口径 (D0 坑17): total/n_edges = tests_grammar∧辽宁 **边数** (一题可考多语法点, 频次口径);
    n_questions = COUNT(DISTINCT src_id) **去重题数** (题级口径)。两口径显式分离, 不混用。
    total 保留 = n_edges (兼容旧消费方)。
    """
    rows = con.execute(
        "WITH tg AS ("
        "  SELECT SUBSTR(e.dst_id, LENGTH('grammar:')+1) AS gid "
        "  FROM edges e JOIN exam_questions q ON q.question_id = SUBSTR(e.src_id,10) "
        "  WHERE e.relation='tests_grammar' AND q.province LIKE '辽宁%') "
        "SELECT cat.label AS category, gi.label AS item, COUNT(*) AS n "
        "FROM tg JOIN grammar_items gi ON gi.grammar_item_id = tg.gid "
        "LEFT JOIN grammar_items cat ON cat.grammar_item_id = "
        "  CASE WHEN instr(tg.gid,'/')>0 THEN split_part(tg.gid,'/',1)||'/'||split_part(tg.gid,'/',2) ELSE tg.gid END "
        "GROUP BY 1, 2"
    ).fetchall()
    by_cat: dict[str, dict] = {}
    for cat, item, n in rows:
        c = by_cat.setdefault(cat or "其他", {"n": 0, "items": []})
        c["n"] += int(n)
        c["items"].append({"label": item, "n": int(n)})
    total = sum(c["n"] for c in by_cat.values())
    n_questions = con.execute(
        "SELECT COUNT(DISTINCT e.src_id) FROM edges e "
        "JOIN exam_questions q ON q.question_id = SUBSTR(e.src_id,10) "
        "WHERE e.relation='tests_grammar' AND q.province LIKE '辽宁%'"
    ).fetchone()[0]
    pct = lambda n: round(100.0 * n / total, 1) if total else 0.0
    cats = sorted(by_cat.items(), key=lambda kv: kv[1]["n"], reverse=True)
    return {
        "total": total,           # 兼容旧消费方; 语义 = n_edges (边数)
        "n_edges": total,         # 边数口径 (一题可考多语法点)
        "n_questions": int(n_questions),  # 去重题数口径 (tests_grammar∧辽宁 DISTINCT src_id)
        "by_category": [
            {"category": k, "n": v["n"], "pct": pct(v["n"]),
             "top": sorted(v["items"], key=lambda x: x["n"], reverse=True)[:4]}
            for k, v in cats],
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
        "note": "教材固定搭配/句型/表达方式库 (来自教材单元提取); **出现非考查** — 无短语级真题考查边, 不冒充考查频次(坑12); 短语级考查标注=未来任务。",
    }


def expression_stats(con: duckdb.DuckDBPyConnection) -> dict:
    """合并: 语法考查(真值) + 教材搭配/表达库(出现非考查) — 真题特点页"语法/搭配/句型/时态/从句"扩展统计."""
    return {
        "scope": "辽宁卷语法考查(tests_grammar 真值) + 教材搭配/句型/表达库(phrases 出现非考查)",
        "grammar_exam": grammar_exam_stats(con),
        "textbook_expr": phrase_library_stats(con),
        "note": "语法考查=辽宁命题频次真值(锚课标第二级子类, 覆盖时态/从句/句型/词法); 搭配/表达=教材库(出现非考查, 诚实分层)。",
    }
