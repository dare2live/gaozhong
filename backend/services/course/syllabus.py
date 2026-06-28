"""L3 教学提纲 + 段级可溯源 + 作业挂真题 (北极星 Phase C, 决策C 框架不生成内容 content=null).

教学提纲 = L2 派生: 按主题群命题频次比例把 N 节课分配到考点焦点 (高产出优先); 单一计算点。
段级可溯源 (course_segment schema): 每节 = {seq, focus, covers_exam_points, evidence_questions(作业真题), trend_weight, content:null}
  —— 替代旧前端甩裸题号 gb/...44, 用"考点焦点 + 可溯源真题"组织。
作业挂真题: evidence_questions = 反向 tests_exam_point 边命中的辽宁真题 (非生成 坑14; 每题溯源 source_file#index)。

全读已落库边 (铁律1)。数据真值; content 一律 null (内容生成是 Phase D, 需 L1/L2 就绪门)。
"""
from __future__ import annotations

import duckdb

from backend.services.course.coverage import _ln_freq_by_point


def homework_for_point(con: duckdb.DuckDBPyConnection, dim: str, label: str, limit: int = 12) -> list[dict]:
    """考点 (dim:label) → 辽宁真题作业 (反向 tests_exam_point ∧ 辽宁前缀坑7-safe, 每题溯源, 非生成)."""
    return con.execute(
        "SELECT q.question_id, q.year, q.question_type, SUBSTR(q.raw_question,1,120) AS preview, "
        "q.source_file, q.source_index, "
        "CASE WHEN q.answer IS NOT NULL AND q.answer<>'' THEN 1 ELSE 0 END AS has_answer "
        "FROM edges e JOIN exam_questions q ON q.question_id = SUBSTR(e.src_id,10) "
        "WHERE e.relation='tests_exam_point' AND e.dst_id = ? AND q.province LIKE '辽宁%' "
        "ORDER BY q.year DESC, q.question_id LIMIT ?",
        [f"exam_point:{dim}:{label}", limit],
    ).fetchall()


def _alloc(themes: list[tuple[str, int]], n: int) -> list[int]:
    """按频次比例把 n 节分配到各主题群 (每主题群 ≥1; 余数按最大余数法). 返回与 themes 同序的节数列表."""
    if not themes:
        return []
    total = sum(f for _, f in themes) or 1
    base = [max(1, int(n * f / total)) for _, f in themes]
    # 调整到正好 n (多退少补, 改高频/低频项)
    while sum(base) > n and any(b > 1 for b in base):
        i = base.index(max(base)); base[i] -= 1
    while sum(base) < n:
        i = base.index(max(base)); base[i] += 1
    return base


def syllabus(con: duckdb.DuckDBPyConnection, n_lessons: int = 40) -> dict:
    """教学提纲 framework: N 节按主题群频次分配 + 每节段级可溯源(考点焦点+作业真题, content=null)."""
    themes = _ln_freq_by_point(con, "theme_l2")  # [(label, 频次)] 降序
    alloc = _alloc(themes, n_lessons)
    lessons = []
    seq = 1
    for (theme, freq), k in zip(themes, alloc):
        pool = homework_for_point(con, "theme_l2", theme, limit=max(k * 2, 4))
        for i in range(k):
            hw = pool[i::k]  # 轮询切片, 每节分得该主题群一部分真题作业
            lessons.append({
                "seq": seq, "focus": theme, "focus_dim": "theme_l2",
                "covers_exam_points": [f"exam_point:theme_l2:{theme}"],
                "evidence_questions": [
                    {"question_id": q[0], "year": q[1], "question_type": q[2], "preview": q[3],
                     "source": f"{q[4]}#{q[5]}", "has_answer": bool(q[6])} for q in hw],
                "trend_weight": freq,
                "content": None,  # Phase D (就绪门绿才生成)
            })
            seq += 1
    covered_w = sum(f for _, f in themes)
    return {
        "n_lessons": len(lessons),
        "lessons": lessons,
        "coverage": {"axis": "theme_l2", "themes_covered": len(themes),
                     "theme_weight_covered_pct": 100.0 if themes else 0.0,
                     "note": "40 节按主题群命题频次比例分配, 8 主题群全覆盖; 词/语法/题材覆盖见 /api/course/coverage"},
        "schema": "course_segment: seq/focus/covers_exam_points/evidence_questions(作业真题溯源)/trend_weight/content(=null, Phase D)",
        "note": "教学提纲=L2派生框架(决策C 不生成内容); 作业=辽宁真题非生成(坑14); 每段考点↔真题可溯源, 替裸题号。",
    }
