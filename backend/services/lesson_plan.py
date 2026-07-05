"""教案生成 — 用户 2026-05-24: 趋势研究融入教学.

给定 unit_id, 输出含以下要素的教案:
  1. 该 unit 教的 word / grammar / phrase
  2. 每个词/语法的"近 N 次真题溯源" (按 year DESC, 列 question_id + 题型)
  3. 词形变形频次 (用 derive_from edges)
  4. 趋势提示 (与 top_rising_words / question_type_trend 交叉)
  5. 教学建议 (按 4 象限 + 趋势 slope 推断)

不押题, 是"教学侧 evidence-based 建议".
"""
from __future__ import annotations

import json

import duckdb

from backend.services import vocab
from backend.services.extraction.example_text import clean_example
from backend.services.trend import scope


def _word_derived_forms(con: duckdb.DuckDBPyConnection, word: str) -> list[str]:
    rows = con.execute("""
        SELECT DISTINCT SUBSTR(dst_id, 6) AS related_word
        FROM edges WHERE relation = 'derive_from' AND src_id = ?
        ORDER BY related_word
    """, [f"word:{word}"]).fetchall()
    return [r[0] for r in rows]


def _grammar_exam_trace(con: duckdb.DuckDBPyConnection, gid: str,
                         recent_n: int = 5) -> list[dict]:
    """语法点近 N 次**辽宁卷**真题溯源 (§7 锚定; 与本视图 word/related_exams 同省, 不混外省)."""
    rows = con.execute("""
        SELECT q.question_id, q.year, q.question_type, e.evidence_json
        FROM edges e
        INNER JOIN exam_questions q ON q.question_id = SUBSTR(e.src_id, 10)
        WHERE e.relation = 'tests_grammar' AND e.dst_id = ? AND q.province LIKE '辽宁%'
        ORDER BY q.year DESC, q.question_id LIMIT ?
    """, [f"grammar:{gid}", recent_n]).fetchall()
    return [{"question_id": r[0], "year": r[1], "qtype": r[2],
              "term": _safe_term(r[3])} for r in rows]


def _safe_term(ev: str | None) -> str | None:
    if not ev:
        return None
    try: return json.loads(ev).get("term")
    except Exception: return None


def _unit_words_with_trace(con: duckdb.DuckDBPyConnection, unit_id: str,
                            recent_n: int = 3, limit: int = 25) -> list[dict]:
    """单元引入词 (带真题溯源/状态/教学建议), 按真题考查频次降序取 top N.

    词源 + 频次走 services.vocab 单一计算点 (与 alignment_summary 同源, 不再内联 unit_vocab_intro
    异源 JOIN); 频次一次批量 GROUP BY (灭 N+1)。确定性 (D0): (-freq, word) 排序后截断, 不无序 LIMIT。
    """
    from backend.services import vocab_classify
    words = sorted(set(vocab.unit_introduced_words(con, unit_id)))
    freqs = vocab.unit_word_frequencies(con, unit_id)
    scored = sorted(((w, vocab_classify.category(w), freqs.get(w, 0)) for w in words),
                    key=lambda x: (-x[2], x[0]))   # 高考频次降序, 同频字母序 (确定性)
    out = []
    for w, cat, freq in scored[:limit]:
        out.append({
            "word": w, "syllabus_category": cat,   # 走 vocab_classify (词形归并后, 非 stale node attrs)
            "recent_exam_trace": vocab.word_exam_trace(con, w, recent_n=recent_n),
            "exam_freq_count": freq,
            "derived_forms": _word_derived_forms(con, w)[:5],
            "teaching_hint": _word_teaching_hint(cat, freq),
        })
    return out


def _word_teaching_hint(cat: str, freq: int) -> str:
    if cat == "真超纲·辽宁考过":
        return "⭐ 超纲但辽宁高考考过, 必教"
    if cat == "真超纲·仅外省考过":
        return "超纲, 仅外省卷考过 (高值参考, 非辽宁确认)"
    if cat == "真超纲·未考":
        return "超纲且历年未考, 可降权 / 选学"
    if cat == "专名/碎片":
        return "专名/缩写, 非核心词汇"
    if freq >= 3:
        return "课标内, 高频考词 必背 + 配题练"
    return "课标内, 标准教学"


def _unit_related_exams(con: duckdb.DuckDBPyConnection, unit_id: str,
                        limit: int = 8) -> list[dict]:
    """备课 killer: 单元主题 → (theme_aligns) 考点 → (tests_exam_point 反) 相关辽宁真题.

    "我要教这个单元(主题=X) → 高考考过这些同主题真题" — 用 4 路追溯桥(theme_aligns)反查。
    """
    rows = con.execute(
        "SELECT DISTINCT SUBSTR(te.src_id, 10) AS qid, q.year, q.question_type, ep.label AS theme_point "
        "FROM edges tou "
        "JOIN edges ta ON ta.dst_id = tou.dst_id AND ta.relation = 'theme_aligns' "
        "JOIN nodes ep ON ep.concept_id = ta.src_id "
        "JOIN edges te ON te.dst_id = ta.src_id AND te.relation = 'tests_exam_point' "
        "JOIN exam_questions q ON q.question_id = SUBSTR(te.src_id, 10) AND q.province LIKE '辽宁%' "
        "WHERE tou.src_id = ? AND tou.relation = 'theme_of_unit' "
        "ORDER BY q.year DESC, SUBSTR(te.src_id, 10), ep.label LIMIT ?",  # 确定性 tiebreak (D0)
        [unit_id, limit],
    ).fetchall()
    return [{"question_id": r[0], "year": r[1], "question_type": r[2], "theme_point": r[3]}
            for r in rows]


def _unit_grammar_with_trace(con: duckdb.DuckDBPyConnection, ver: str, vol: str,
                             unit_n: int, recent_n: int = 5) -> list[dict]:
    """单元语法点 (地基第四轴 grammar_occurrences) + 课标项标签 + 真题溯源.

    真相源 = grammar_occurrences (教材 Grammar section curated 映射的课标项, 诚实跳过不命中);
    每项挂 tests_grammar 边的近 N 次真题, 让"教此语法 → 高考这么考"可追溯。
    """
    rows = con.execute(
        "SELECT g.grammar_item_id, gi.label, gi.category, g.example_sentence "
        "FROM grammar_occurrences g "
        "JOIN grammar_items gi ON gi.grammar_item_id = g.grammar_item_id "
        "WHERE g.version_key = ? AND g.volume_key = ? AND g.unit_number = ? "
        "ORDER BY g.grammar_item_id, g.occ_id",
        [ver, vol, unit_n],
    ).fetchall()
    return [{
        "grammar_item_id": gid, "label": label, "category": cat,
        # 坑(2026-07-05 根因审计): 原 (ex or "")[:120] 是与 textbook_content.py._grammar 重复的
        # 独立硬截逻辑, 收口到共享 clean_example (无 a/b/c 例句模式则诚实返回 None, 不假填).
        "example": clean_example(ex),
        "recent_exam_trace": _grammar_exam_trace(con, gid, recent_n=recent_n),
    } for gid, label, cat, ex in rows]


def _unit_vocab_profile(con: duckdb.DuckDBPyConnection, unit_id: str) -> dict:
    """单元词汇越纲分层画像 (§1.2 不偏离学校) — 走 vocab_classify 单一计算点.

    超纲判定经词形归并(复数/被动/时态还原)+派生还原+专名过滤+高考核对分层 (artifact);
    越纲率只算**真超纲**(排除"实为课标词变形/派生"和专名/碎片, 不再虚高)。真超纲分三层:
    辽宁考过(必教) / 仅外省考过(高值参考) / 未考(选学)。
    """
    from backend.services import vocab_classify
    words = sorted(set(vocab.unit_introduced_words(con, unit_id)))
    return vocab_classify.unit_over_profile(words)


def _trend_honesty(con: duckdb.DuckDBPyConnection) -> dict:
    """命题趋势可信度 live banner (件1 分析诚实) — 不写死 slope, 读 scope.diagnose 单一计算点."""
    d = scope.diagnose(con)
    return {
        "province_scope": d["province_scope"],
        "distribution_reliable": d["distribution_reliable"],
        "trend_reliable": d["trend_reliable"],
        "note": ("考点分布(占比)可报; 逐年斜率样本不足不外推" if d["distribution_reliable"]
                 and not d["trend_reliable"]
                 else ("分布与逐年趋势均达样本量门槛" if d["trend_reliable"]
                       else "样本量不足, 分布与趋势均谨慎")),
    }


def generate_lesson_plan(con: duckdb.DuckDBPyConnection, unit_id: str) -> dict:
    """完整教案输出 — 备课整合一体视图 (unit → 词/语法/主题考点/真题对齐, 单一计算点收口)."""
    # unit 基础
    parts = unit_id.split(":", 1)[1].split("/")
    ver, vol, u_str = parts[0], parts[1], parts[2]
    unit_n = int(u_str.lstrip("U"))
    unit = con.execute("""
        SELECT title_en, page_start, page_end FROM units
        WHERE version_key=? AND volume_key=? AND unit_number=?
    """, [ver, vol, unit_n]).fetchone()
    title = unit[0] if unit else "(未知)"

    # 主题 (多边时取字典序首, 确定性)
    theme = con.execute("""
        SELECT dst_id FROM edges WHERE src_id=? AND relation='theme_of_unit'
        ORDER BY dst_id LIMIT 1
    """, [unit_id]).fetchone()

    # phrases (确定性排序后截断)
    phrases = con.execute("""
        SELECT canonical, phrase_type, evidence FROM phrases
        WHERE version_key=? AND volume_key=? AND unit_number=?
        ORDER BY canonical, phrase_type, evidence LIMIT 10
    """, [ver, vol, unit_n]).fetchall()

    return {
        "unit_id": unit_id, "title": title,
        "theme": theme[0] if theme else None,
        "page_range": (unit[1], unit[2]) if unit else (None, None),
        "vocab_profile": _unit_vocab_profile(con, unit_id),  # 越纲率画像 (§1.2 不偏离学校)
        "words": _unit_words_with_trace(con, unit_id),
        "grammar": _unit_grammar_with_trace(con, ver, vol, unit_n),  # 地基第四轴 + 真题溯源
        "phrases": [{"canonical": p[0], "type": p[1], "evidence": p[2][:100]}
                     for p in phrases],
        "related_exams": _unit_related_exams(con, unit_id),  # 同主题高考真题 (4路桥反查)
        "alignment_summary": vocab.unit_word_exam_alignment(con, unit_id),  # 词∩真题汇总 (单一计算点)
        "trend_honesty": _trend_honesty(con),  # 命题趋势 live 可信度 (件1, 不写死 slope)
        "teaching_notes": {
            "评估说明": ("words.recent_exam_trace 列出每词近 N 次高考真题考查"
                          " (question_id 含 year + 题型, 老师可点查原题)"),
            "趋势说明": ("题型分布大体由考纲蓝图固定; 命题趋势以 /api/trend (辽宁卷锚定 + 样本量护栏)"
                          " live 结果为准, 薄样本年标'样本不足'不外推 (件1 分析诚实, 不写死 slope)"),
            "教学建议": ("HV_extra ⭐ 必教 / core 高频 必背 / "
                          "LV_extra 选学; 配套 graph cross-link 见 /api/recommend/"),
        },
    }
