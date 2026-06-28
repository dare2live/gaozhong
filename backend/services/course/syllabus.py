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


def _adjust(base: list[int], raw: list[float], n: int) -> list[int]:
    """把 base 调到 sum==n: 缺额按小数余数降序补 (最大余数法); 超额(min=1地板致)从最大且>1项退回."""
    deficit = n - sum(base)
    if deficit > 0:
        order = sorted(range(len(base)), key=lambda i: raw[i] - int(raw[i]), reverse=True)
        for i in order[:deficit]:
            base[i] += 1
        return base
    big = sorted(range(len(base)), key=lambda i: base[i], reverse=True)
    k = 0
    while deficit < 0 and k < len(big) * 20:
        i = big[k % len(big)]
        if base[i] > 1:
            base[i] -= 1; deficit += 1
        k += 1
    return base


def _alloc(themes: list[tuple[str, int]], n: int) -> list[int]:
    """按频次比例把 n 节分配到各主题群 (每主题群 ≥1; 名额按**最大余数法**, 非贪心 rich-get-richer)."""
    if not themes:
        return []
    total = sum(f for _, f in themes) or 1
    raw = [n * f / total for _, f in themes]
    base = [max(1, int(r)) for r in raw]
    return _adjust(base, raw, n)


def _coverage_proof(con: duckdb.DuckDBPyConnection) -> dict:
    """从 coverage_model 拉各轴覆盖证明 (高产出集/全集/长尾) — 北极星§4 '覆盖证明' 硬底气, 诚实标长尾非全覆盖."""
    from backend.services.course.coverage import coverage_model
    cov = coverage_model(con)
    return {
        "target_pct": cov["target_pct"],
        "axes": {k: {"n_total": a["n_total"], "high_yield_n": a["high_yield_n"], "tail_n": a["tail_n"]}
                 for k, a in cov["axes"].items()},
        "note": "覆盖证明: 各可教轴达 target% 考查权重的最少考点数(高产出集)+长尾缺口; 词轴长尾大→结合小初高(75.7%基础阶)高中实攻~18% delta。诚实非字面全覆盖(§7)。",
    }


def syllabus(con: duckdb.DuckDBPyConnection, n_lessons: int = 40) -> dict:
    """教学提纲 framework: N 节按主题群频次**最大余数法**分配 + 每节段级可溯源(考点焦点+作业真题, content=null).

    课节分配维度 = theme_l2 主题群 (主组织轴); 题材/词/语法的覆盖见 coverage_proof, 其逐节映射待 Phase D 内容生成 (决策C)。
    """
    themes = _ln_freq_by_point(con, "theme_l2")  # [(label, 频次)] 降序
    alloc = _alloc(themes, n_lessons)
    theme_total_w = sum(f for _, f in themes) or 1
    lessons = []
    seq = 1
    for (theme, freq), k in zip(themes, alloc):
        pool = homework_for_point(con, "theme_l2", theme, limit=max(k * 2, 4))
        lesson_w = round(freq / k, 1) if k else freq  # 坑12: 每节权重=该主题频次/节数(份额), 多节不重复计全额
        for i in range(k):
            hw = pool[i::k]  # 轮询切片, 每节分得该主题群一部分真题作业
            lessons.append({
                "seq": seq, "segment_id": f"seg-{seq:02d}", "course_id": seq,  # §3.2 schema: seq↔courses.course_id 1-40
                "focus": theme, "focus_dim": "theme_l2",
                "covers_exam_points": [f"exam_point:theme_l2:{theme}"],
                "evidence_questions": [
                    {"question_id": q[0], "year": q[1], "question_type": q[2], "preview": q[3],
                     "source": f"{q[4]}#{q[5]}", "has_answer": bool(q[6])} for q in hw],
                "trend_weight": lesson_w,   # 本节命题权重份额 (该主题频次/节数; 跨本主题各节求和=主题频次, 不重复计)
                "theme_total_weight": freq,  # 该主题群总频次 (供前端区分份额 vs 总额)
                "content": None,  # Phase D (就绪门绿才生成)
            })
            seq += 1
    return {
        "n_lessons": len(lessons),
        "lessons": lessons,
        "coverage": {
            "alloc_axis": "theme_l2",
            "themes_total": len(themes),
            "themes_allocated": len({l["focus"] for l in lessons}),
            "theme_axis_covered_pct": round(100.0 * sum(f for t, f in themes if t in {l["focus"] for l in lessons}) / theme_total_w, 1),
            "note": "课节按主题群命题频次最大余数法分配; 此 pct 仅 theme_l2 主题轴(每主题≥1节, 全分配)。题材/词/语法轴覆盖见 coverage_proof, 其逐节映射待 Phase D。非字面全考点覆盖(§7)。",
        },
        "coverage_proof": _coverage_proof(con),
        "schema": "course_segment: seq/segment_id/course_id/focus/covers_exam_points/evidence_questions(作业真题溯源)/trend_weight(份额)/theme_total_weight/content(=null,Phase D)",
        "note": "教学提纲=L2派生框架(决策C 不生成内容 content=null); 课节按主题群分配(主组织轴); 作业=辽宁真题非生成(坑14); 每段考点↔真题可溯源替裸题号。",
    }
