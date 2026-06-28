"""D0 考点 canonical 维度校验 (从 data_accuracy_check 抽出, 避 god-module Rule 8).

件2 考点 canonical + 4路桥(theme_aligns) + 学情薄弱环节考点化 纳入 D0 100% 强校验。
check 由调用方传入 (data_accuracy_check.check), 失败追加 FAILURES。
"""
from __future__ import annotations

import duckdb

from scripts.lib.d0_baselines import B


def check_exam_point(con: duckdb.DuckDBPyConnection, check) -> None:
    """考点边/4路桥/薄弱环节 5 项 D0 校验 (新数据落地必入强校验)."""
    print("\n=== (22) 考点 canonical 维度 + 4路追溯 ===")
    n_ep = con.execute("SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point'").fetchone()[0]
    check("tests_exam_point 边 ≥ 300", n_ep >= B('exam_point_min'), f"{n_ep}")
    bad_ep = con.execute(
        "SELECT COUNT(*) FROM edges e WHERE e.relation='tests_exam_point' AND ("
        "NOT EXISTS (SELECT 1 FROM nodes n WHERE n.concept_id=e.src_id AND n.node_type='question') "
        "OR NOT EXISTS (SELECT 1 FROM nodes n WHERE n.concept_id=e.dst_id AND n.node_type='exam_point'))"
    ).fetchone()[0]
    check("考点边两端有效 (无悬挂)", bad_ep == 0, f"{bad_ep} 悬挂")
    bad_prov = con.execute(
        "SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' "
        "AND json_extract_string(evidence_json,'$.provenance') NOT IN ('dual_model_agree','explicit_label')"
    ).fetchone()[0]
    check("考点边 provenance ∈ {dual_model_agree, explicit_label} (无弱provenance; cognitive_skill=教研显式标签)",
          bad_prov == 0, f"{bad_prov} 弱provenance")
    bad_ta = con.execute(
        "SELECT COUNT(*) FROM edges e WHERE e.relation='theme_aligns' AND ("
        "e.src_id NOT LIKE 'exam_point:theme%' OR e.dst_id NOT LIKE 'theme:%')").fetchone()[0]
    check("theme_aligns 桥两端有效", bad_ta == 0, f"{bad_ta} 错连")
    bad_wk = con.execute(
        "SELECT COUNT(*) FROM student_weakness WHERE concept_id NOT LIKE 'exam_point:%'").fetchone()[0]
    check("薄弱环节维度=exam_point真考点 (非word token)", bad_wk == 0, f"{bad_wk} 非考点")
    _check_no_theme_l3(con, check)
    _check_passage_dim_granularity(con, check)
    _check_evidence_json_valid(con, check)
    _check_grammar_qtype(con, check)


def _check_grammar_qtype(con: duckdb.DuckDBPyConnection, check) -> None:
    """RC1#4 防回归: tests_grammar 只落离散语法考点题型(语法填空/单选/短改); 阅读理解/完形结构上不考
    离散语法(原子串匹配致 7 条落阅读理解=误报, 污染'教此语法→高考这么考')。"""
    bad = con.execute(
        "SELECT COUNT(*) FROM edges e "
        "JOIN exam_questions q ON ('question:'||q.question_id)=e.src_id "
        "WHERE e.relation='tests_grammar' "
        "AND q.question_type NOT IN ('语法填空','单选(语法/词汇)','短文改错')").fetchone()[0]
    check("tests_grammar 仅落离散语法题型 (无阅读/完形误报)", bad == 0, f"{bad} 误报落非语法题型")


def _check_passage_dim_granularity(con: duckdb.DuckDBPyConnection, check) -> None:
    """RC1#6 防回归 (后端审计 2026-06-27): genre/theme/theme_l2 是**篇章级**维度(整篇1个体裁/主题),
    eol 2021/2022 按子题存 → 分布/共现必须排除子题级源(source_repo LIKE 'eol_xgkii%'), 否则 1 篇 N 子题
    记 N 次失真(记叙文 55.8% 子题膨胀, 篇章级真值~30%; "命题迁移+24pt"伪迁移)。
    断言: 分布数的 genre/theme 边 == 非子题级源 genre/theme 边(证明滤生效; 回归则分布数虚高 → FAIL)。"""
    from backend.services.exam_point.loader import exam_point_distribution
    dist = exam_point_distribution(con)
    dist_n = sum(x["n"] for era in dist.values()
                 for d in ("genre", "theme_context", "theme_l2") for x in era.get(d, []))
    truth_n = con.execute(
        "SELECT COUNT(*) FROM edges e "
        "JOIN exam_questions q ON ('question:'||q.question_id)=e.src_id AND q.province LIKE '辽宁%' "
        "WHERE e.relation='tests_exam_point' "
        "AND json_extract_string(e.evidence_json,'$.dimension') IN ('genre','theme_context','theme_l2') "
        "AND q.source_repo NOT LIKE 'eol_xgkii%'").fetchone()[0]
    check("genre/theme 分布=篇章级口径 (排除子题级eol源; 防记叙文子题膨胀+伪迁移回归)",
          dist_n == truth_n, f"分布数{dist_n} ≠ 篇章级真值{truth_n}")


def _check_evidence_json_valid(con: duckdb.DuckDBPyConnection, check) -> None:
    """RC1#5 防回归: 全边 evidence_json 须合法 JSON (手拼含 \\x7f/制表符=非法, 全表 json_extract 崩)。"""
    bad = con.execute(
        "SELECT COUNT(*) FROM edges WHERE evidence_json IS NOT NULL "
        "AND TRIM(evidence_json) <> '' AND NOT json_valid(evidence_json)").fetchone()[0]
    check("全边 evidence_json 合法JSON (防手拼控制字符致全表json_extract崩)", bad == 0, f"{bad} 非法")


def _check_no_theme_l3(con: duckdb.DuckDBPyConnection, check) -> None:
    """防回归锁 (2026-06-21 真值核验): 课标主题语境官方仅 L1/L2 可枚举, 无"第三级子主题"。
    曾有 35 个杜撰 theme_l3(extract_curriculum _reader 不读PDF 直接塞 + dual_model 贴标签) → 已废。
    正向断言三件套 (坑1: 锁住'无', 防 extract 重建静默塞回; 配 ThemeTruthChecker 真值锚)。"""
    n_l3_edge = con.execute(
        "SELECT COUNT(*) FROM edges WHERE dst_id LIKE 'exam_point:theme_l3:%' "
        "OR src_id LIKE 'exam_point:theme_l3:%'").fetchone()[0]
    check("无杜撰 theme_l3 边 (官方主题语境仅L1/L2; 亲验PDF表2)", n_l3_edge == 0, f"{n_l3_edge} 残留")
    n_l3_ctx = con.execute(
        "SELECT COUNT(*) FROM theme_contexts WHERE level3 IS NOT NULL AND TRIM(level3)<>''").fetchone()[0]
    check("theme_contexts.level3 全空 (官方无可枚举第三级)", n_l3_ctx == 0, f"{n_l3_ctx} 残留")
    # theme 叶节点不得有 depth2 (2斜杠 = 杜撰子主题命名空间)
    n_l3_node = con.execute(
        "SELECT COUNT(*) FROM nodes WHERE node_type='theme' "
        "AND length(concept_id)-length(replace(concept_id,'/',''))>=2").fetchone()[0]
    check("无 theme depth2 叶节点 (杜撰子主题命名空间已废)", n_l3_node == 0, f"{n_l3_node} 残留")


def check_coverage(con: duckdb.DuckDBPyConnection, check) -> None:
    """L3 覆盖模型 correctness (北极星 Phase C). 跨源核验: service 各轴权重 == 独立SQL重算 (as-served, 非同源重言);
    高产出集 ≤ 全集 (单调); 词轴非空 (考查词存在)。防覆盖口径漂移 (如丢省份/边类型)。"""
    print("\n=== (33) L3 覆盖模型 correctness (course.coverage_model 跨源) ===")
    from backend.services.course.coverage import coverage_model
    from backend.services.exam_vocab import TESTED_QTYPES
    m = coverage_model(con)
    ax = m["axes"]
    # 词轴权重独立重算 (tests_word ∧ 辽宁 ∧ 离散 边数)
    qm = ",".join("?" * len(TESTED_QTYPES))
    w_indep = con.execute(
        "SELECT COUNT(*) FROM edges e JOIN exam_questions q ON q.question_id=SUBSTR(e.src_id,10) "
        f"WHERE e.relation='tests_word' AND q.province LIKE '辽宁%' AND q.question_type IN ({qm})",
        list(TESTED_QTYPES)).fetchone()[0]
    check("词轴 weight_total == 独立SQL重算 (as-served==源, 非重言)", ax["word"]["weight_total"] == w_indep, f"svc={ax['word']['weight_total']} sql={w_indep}")
    # 题材轴权重独立重算 (tests_exam_point genre ∧ 辽宁)
    g_indep = con.execute(
        "SELECT COUNT(*) FROM edges e JOIN exam_questions q ON q.question_id=SUBSTR(e.src_id,10) "
        "WHERE e.relation='tests_exam_point' AND e.dst_id LIKE 'exam_point:genre:%' AND q.province LIKE '辽宁%'").fetchone()[0]
    check("题材轴 weight_total == 独立SQL重算 (跨源)", ax["genre"]["weight_total"] == g_indep, f"svc={ax['genre']['weight_total']} sql={g_indep}")
    check("词轴非空 (辽宁考查词存在)", ax["word"]["n_total"] > 0, f"{ax['word']['n_total']}")
    bad = [k for k, a in ax.items() if a["high_yield_n"] > a["n_total"]]
    check("各轴 高产出集 ≤ 全集 (覆盖单调, 无越界)", not bad, f"越界轴={bad}")


def check_syllabus(con: duckdb.DuckDBPyConnection, check) -> None:
    """L3 教学提纲 correctness (北极星 Phase C, 决策C 框架). 无孤儿内容(段↔考点↔真题可溯源) +
    content 一律 null(不生成 L3 内容) + 作业=辽宁真题(非生成). 防框架塞生成内容或挂孤儿/非辽宁题。"""
    print("\n=== (34) L3 教学提纲 correctness (course.syllabus 段级可溯源/无孤儿/content=null) ===")
    from backend.services.course.syllabus import syllabus
    s = syllabus(con)
    lessons = s["lessons"]
    check("有课节 (n_lessons>0)", len(lessons) > 0, f"{len(lessons)}")
    # 1. content 一律 null (决策C: 不生成 L3 内容, Phase D 才填)
    n_content = sum(1 for l in lessons if l.get("content") is not None)
    check("所有段 content==null (决策C 框架不生成内容)", n_content == 0, f"{n_content} 段已有内容(违决策C)")
    # 2. 无孤儿: 每节 covers_exam_points 指向真实 exam_point 节点 **且有 tests_exam_point 边** (§3.2: 存在于L2考查边, 非仅节点)
    pts = {p for l in lessons for p in l["covers_exam_points"]}
    real = {r[0] for r in con.execute("SELECT concept_id FROM nodes WHERE concept_id LIKE 'exam_point:%'").fetchall()}
    edged = {r[0] for r in con.execute("SELECT DISTINCT dst_id FROM edges WHERE relation='tests_exam_point'").fetchall()}
    orphan_pt = pts - real
    no_edge = pts - edged
    check("段考点焦点全指向真实 exam_point (无孤儿节点)", not orphan_pt, f"孤儿={list(orphan_pt)[:3]}")
    check("段考点焦点全有 tests_exam_point 考查边 (§3.2 存在于L2, 非空考点)", not no_edge, f"无考查边={list(no_edge)[:3]}")
    # 2b. 分配=最大余数法 (防回归到贪心 rich-get-richer 偏差); trend_weight 份额求和=主题频次 (坑12 防重复计权)
    from backend.services.course.syllabus import _alloc
    from backend.services.course.coverage import _ln_freq_by_point
    themes = _ln_freq_by_point(con, "theme_l2")
    want = _alloc(themes, len([l for l in lessons]))
    got = [sum(1 for l in lessons if l["focus"] == t) for t, _ in themes]
    check("课节分配=最大余数法比例 (无 rich-get-richer 偏差)", want == got, f"got={got} want={want}")
    import collections as _c
    wsum = _c.defaultdict(float)
    for l in lessons:
        wsum[l["focus"]] += l.get("trend_weight", 0)
    drift = [t for t, f in themes if abs(wsum[t] - f) > 1.0]
    check("trend_weight 份额按主题求和≈频次 (坑12: 多节不重复计全额)", not drift, f"漂移主题={drift[:3]}")
    # 3. 作业真题全可溯源 (source) 且为辽宁真题 (非生成)
    qids = [q["question_id"] for l in lessons for q in l["evidence_questions"]]
    no_src = sum(1 for l in lessons for q in l["evidence_questions"] if not q.get("source"))
    check("作业真题全有溯源 (source, 无孤儿)", no_src == 0, f"{no_src} 题无溯源")
    if qids:
        ph = ",".join("?" * len(qids))
        ln_real = con.execute(
            f"SELECT COUNT(*) FROM exam_questions WHERE question_id IN ({ph}) AND province LIKE '辽宁%'", qids).fetchone()[0]
        check("作业真题全为辽宁真题 (非生成 非外省, 坑14)", ln_real == len(qids), f"{ln_real}/{len(qids)} 辽宁")
