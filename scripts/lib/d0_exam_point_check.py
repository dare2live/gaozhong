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
        "AND json_extract_string(evidence_json,'$.provenance') NOT IN "
        "('dual_model_agree','explicit_label','cross_verified',"
        "'curriculum_aligned_stem','curriculum_aligned_task',"
        "'human_curriculum_verified')"
    ).fetchone()[0]
    check("考点边 provenance ∈ {dual_model_agree, explicit_label, cross_verified, curriculum_aligned_*, human_curriculum_verified} (无弱provenance; 坑16)",
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
    _check_grammar_coverage_floor(con, check)
    check_genre_truth(con, check)
    check_theme_human_verified(con, check)
    check_theme_layers(con, check)
    check_quality_standards(con, check)
    check_grammar_point_rollup(con, check)


def _check_grammar_coverage_floor(con: duckdb.DuckDBPyConnection, check) -> None:
    """2026-07-07 知识点颗粒度审查缺口2b: TERM_TO_LABEL_KEYWORD 从26词扩到36词(补冠词/介词/
    连词/名词/形容词/副词/序数词/情态动词/人称代词/一般过去, 均实测真解析文本命中+grammar_items
    有label完全相等对应行), tests_grammar 边 18→84, 覆盖官方108项语法从8→22项。锁新地板防
    未来误删这些词条静默回退(坑17新数据落地必入D0强校验)。"""
    n = con.execute("SELECT COUNT(*) FROM edges WHERE relation='tests_grammar'").fetchone()[0]
    check("tests_grammar 边 ≥ 84 (2026-07-07 补10词后地板)", n >= B('tests_grammar_min'), f"{n}")
    n_items = con.execute(
        "SELECT COUNT(DISTINCT dst_id) FROM edges WHERE relation='tests_grammar'").fetchone()[0]
    check("tests_grammar 覆盖官方108项语法 ≥ 22项", n_items >= B('tests_grammar_items_min'), f"{n_items}")


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


def check_grammar_stats(con: duckdb.DuckDBPyConnection, check) -> None:
    """语法/搭配统计 correctness (北极星 真题特点扩展). 跨源: 语法考查 total==独立SQL(tests_grammar∧辽宁);
    各类求和==total; 教材搭配库 total==phrases表; 语法类别全锚 grammar_items(不杜撰)。"""
    print("\n=== (35) 语法考查 + 教材搭配统计 correctness (exam_grammar_stats 跨源) ===")
    from backend.services.exam_grammar_stats import expression_stats
    s = expression_stats(con)
    ge = s["grammar_exam"]
    indep = con.execute(
        "SELECT COUNT(*) FROM edges e JOIN exam_questions q ON q.question_id=SUBSTR(e.src_id,10) "
        "JOIN grammar_items gi ON gi.grammar_item_id=SUBSTR(e.dst_id,LENGTH('grammar:')+1) "
        "WHERE e.relation='tests_grammar' AND q.province LIKE '辽宁%'").fetchone()[0]
    check("语法考查 total==独立SQL(tests_grammar∧辽宁∧有grammar_items, as-served)", ge["total"] == indep, f"svc={ge['total']} sql={indep}")
    check("语法各类频次求和==total (无丢)", sum(c["n"] for c in ge["by_category"]) == ge["total"], "sum≠total")
    # 坑17 (g): n_questions(去重题数) vs n_edges(边数) 口径分离, 各锁独立SQL
    nq_indep = con.execute(
        "SELECT COUNT(DISTINCT e.src_id) FROM edges e JOIN exam_questions q ON q.question_id=SUBSTR(e.src_id,10) "
        "WHERE e.relation='tests_grammar' AND q.province LIKE '辽宁%'").fetchone()[0]
    check("语法考查 n_questions==独立SQL(去重题数; 与 n_edges 边数口径显式分离)",
          ge.get("n_questions") == nq_indep and ge.get("n_edges") == ge["total"],
          f"svc={ge.get('n_questions')} sql={nq_indep}")
    # 坑17 (e): by_category 类别全锚 grammar_items 官方项, 无兜底'其他'(新 gid 前缀不匹配会落'其他'被静默吞)
    g_labels = {r[0] for r in con.execute("SELECT label FROM grammar_items").fetchall()}
    bad_cats = [c["category"] for c in ge["by_category"] if c["category"] == "其他" or c["category"] not in g_labels]
    check("语法类别全锚 grammar_items 官方项 (无'其他'兜底/无杜撰类别)", not bad_cats, f"未锚: {bad_cats[:5]}")
    nph = con.execute("SELECT COUNT(*) FROM phrases").fetchone()[0]
    check("教材搭配库 total==phrases表 (as-served)", s["textbook_expr"]["total"] == nph, f"svc={s['textbook_expr']['total']} db={nph}")
    # 坑17 (d): by_group 求和==total (新 phrase_type 前缀不匹配 _PHRASE_GROUP 会被静默丢出分组)
    grp_sum = sum(g["n"] for g in s["textbook_expr"]["by_group"])
    check("搭配库 sum(by_group)==total (无 phrase_type 前缀漏匹配被静默丢)",
          grp_sum == s["textbook_expr"]["total"], f"sum={grp_sum} total={s['textbook_expr']['total']}")
    # 坑(2026-07-04 全数据审计): build_tests_grammar 旧版无 province 过滤(88%非辽宁题的边混入
    # edges表, 靠每个消费者各自 WHERE province LIKE '辽宁%' 打补丁); 现改为建边层本身就锁死
    # 辽宁口径(单一计算点, Rule1), 锁 edges 表里 tests_grammar 关系压根不该有非辽宁行。
    non_ln = con.execute(
        "SELECT COUNT(*) FROM edges e JOIN exam_questions q ON q.question_id=SUBSTR(e.src_id,10) "
        "WHERE e.relation='tests_grammar' AND (q.province IS NULL OR q.province NOT LIKE '辽宁%')"
    ).fetchone()[0]
    check("tests_grammar 边表本身即辽宁口径 (建边层过滤, 非消费者各自打补丁)", non_ln == 0, f"{non_ln} 条非辽宁边")
    # 坑同源: 父子节点共享同一关键词子串时(如"定语从句"同时命中限制性/非限制性子节点),
    # 旧版子串命中就全挂, 68/360(18.9%)~192/360(53.3%)边过度归因; 现只挑blob文本真正支持的
    # 最具体节点。锁: 若某父节点(如三/10/(3))和其任一子节点(三/10/(3)/a或/b)对**同一道题**
    # 同时有边, 除非该题blob确实同时提到两个子类目的区分文本(理论上不该发生, 因_most_specific_
    # grammar_match 设计为每题每term只挑1个最具体节点), 否则视为过度归因回归。
    parent_child_dup = con.execute("""
        SELECT e1.src_id FROM edges e1 JOIN edges e2
          ON e1.src_id = e2.src_id AND e1.relation='tests_grammar' AND e2.relation='tests_grammar'
        WHERE e2.dst_id LIKE e1.dst_id || '/%'
    """).fetchall()
    check("tests_grammar 无同题父子节点同时命中 (过度归因防回归)",
          not parent_child_dup, f"{len(parent_child_dup)} 例: {parent_child_dup[:3]}")


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
    # P2-4 (坑17): 语法轴 top 编码→人话标签全锚 grammar_items 官方项 — id 可查 + label==官方 label 非空, 无杜撰
    g_lbl = dict(con.execute("SELECT grammar_item_id, label FROM grammar_items").fetchall())
    bad_lbl = [t.get("id") for t in ax["grammar"]["top"]
               if not t.get("label") or g_lbl.get(t.get("id")) != t.get("label")]
    check("语法轴 top 人话标签全锚 grammar_items (id可查+label==官方非空, 无杜撰)", not bad_lbl, f"未锚={bad_lbl[:3]}")


def _check_syl_segments(con: duckdb.DuckDBPyConnection, lessons: list, check) -> None:
    """段级: content 仅 review=pass 试点可非 null + covers_exam_points 无孤儿/有考查边(§3.2)."""
    bad_content = []
    n_content = 0
    for l in lessons:
        c = l.get("content")
        if c is None:
            continue
        n_content += 1
        rev = (c.get("review") or {}).get("status")
        if rev != "pass" or not c.get("body_en"):
            bad_content.append(l.get("seq"))
    check(
        "段 content 仅 review=pass 试点非 null (其余 null; Phase D §6)",
        not bad_content,
        f"非法 content 节={bad_content[:5]} n_with={n_content}",
    )
    pts = {p for l in lessons for p in l["covers_exam_points"]}
    real = {r[0] for r in con.execute("SELECT concept_id FROM nodes WHERE concept_id LIKE 'exam_point:%'").fetchall()}
    edged = {r[0] for r in con.execute("SELECT DISTINCT dst_id FROM edges WHERE relation='tests_exam_point'").fetchall()}
    check("段考点焦点全指向真实 exam_point (无孤儿节点)", not (pts - real), f"孤儿={list(pts - real)[:3]}")
    check("段考点焦点全有 tests_exam_point 考查边 (§3.2 存在于L2)", not (pts - edged), f"无考查边={list(pts - edged)[:3]}")


def _check_syl_alloc(con: duckdb.DuckDBPyConnection, lessons: list, check) -> None:
    """分配=最大余数法(防 rich-get-richer 回归) + trend_weight 份额求和=主题频次(坑12 防重复计权)."""
    import collections as _c
    from backend.services.course.syllabus import _alloc
    from backend.services.course.coverage import _ln_freq_by_point
    themes = _ln_freq_by_point(con, "theme_l2")
    want = _alloc(themes, len(lessons))
    got = [sum(1 for l in lessons if l["focus"] == t) for t, _ in themes]
    check("课节分配=最大余数法比例 (无 rich-get-richer 偏差)", want == got, f"got={got} want={want}")
    wsum = _c.defaultdict(float)
    for l in lessons:
        wsum[l["focus"]] += l.get("trend_weight", 0)
    drift = [t for t, f in themes if abs(wsum[t] - f) > 1.0]
    check("trend_weight 份额按主题求和≈频次 (坑12: 多节不重复计全额)", not drift, f"漂移主题={drift[:3]}")


def _check_syl_homework(con: duckdb.DuckDBPyConnection, lessons: list, check) -> None:
    """作业真题全可溯源(source) 且为辽宁真题(非生成 坑14)."""
    qids = [q["question_id"] for l in lessons for q in l["evidence_questions"]]
    no_src = sum(1 for l in lessons for q in l["evidence_questions"] if not q.get("source"))
    check("作业真题全有溯源 (source, 无孤儿)", no_src == 0, f"{no_src} 题无溯源")
    if not qids:
        return
    ph = ",".join("?" * len(qids))
    ln_real = con.execute(
        f"SELECT COUNT(*) FROM exam_questions WHERE question_id IN ({ph}) AND province LIKE '辽宁%'", qids).fetchone()[0]
    check("作业真题全为辽宁真题 (非生成 非外省, 坑14)", ln_real == len(qids), f"{ln_real}/{len(qids)} 辽宁")


def check_syllabus(con: duckdb.DuckDBPyConnection, check) -> None:
    """L3 教学提纲 correctness: 段级可溯源/无孤儿 + content 仅 review=pass 试点 + 分配真比例 + 作业辽宁真题."""
    print("\n=== (34) L3 教学提纲 correctness (course.syllabus 段级可溯源 + Phase D 试点 content) ===")
    from backend.services.course.syllabus import syllabus
    lessons = syllabus(con)["lessons"]
    check("有课节 (n_lessons>0)", len(lessons) > 0, f"{len(lessons)}")
    if not lessons:
        return
    _check_syl_segments(con, lessons, check)
    _check_syl_alloc(con, lessons, check)
    _check_syl_homework(con, lessons, check)


def check_genre_truth(con: duckdb.DuckDBPyConnection, check) -> None:
    """坑16: analysis 显式体裁句交叉验证 + cross_verified 升档地板."""
    from backend.services.exam_point.genre_truth import analysis_genre_crosscheck
    r = analysis_genre_crosscheck(con)
    check("genre analysis 交叉验证 0 conflict", r["n_conflict"] == 0, f"conflict={r['n_conflict']} samples={r['conflict_samples'][:2]}")
    check("genre analysis 显式体裁句 ≥15", r["n_analysis_explicit"] >= 15, f"{r['n_analysis_explicit']}")
    check("genre cross_verified 边 ≥15 (analysis 一致升档)", r["n_cross_verified_edges"] >= 15, f"{r['n_cross_verified_edges']}")


def check_theme_human_verified(con: duckdb.DuckDBPyConnection, check) -> None:
    """theme_l2: 禁假 analysis-cross; 人工课标核验 ≥15."""
    from backend.services.exam_point.theme_truth import analysis_theme_crosscheck
    r = analysis_theme_crosscheck(con)
    check("theme 无假升 analysis-cross_verified", r["n_cross_verified_edges"] == 0, f"{r['n_cross_verified_edges']}")
    check("theme 人工课标核验边 ≥15", r["n_human_verified_edges"] >= 15,
          f"{r['n_human_verified_edges']} status={r['status']}")
    check("theme_truth pass", r["pass"], r.get("note", ""))


def check_quality_standards(con: duckdb.DuckDBPyConnection, check) -> None:
    """课标学业质量: 3水平+42描述 + 辽宁高考卷级→水平二; 禁题目级细边."""
    from backend.services.exam_point.quality_standards import quality_standards_summary
    s = quality_standards_summary(con)
    check("学业质量水平节点 == 3", s["n_quality_levels"] == 3, f"{s['n_quality_levels']}")
    check("学业质量描述节点 == 42", s["n_descriptors"] == 42, f"{s['n_descriptors']}")
    check("辽宁高考卷级对齐水平二边存在", s["aligned_edge_present"], "")
    check("学业质量 descriptors 可浏览列表非空", len(s.get("descriptors") or []) == 3, f"{len(s.get('descriptors') or [])}")
    check("学业质量 forbid_item_level_edges", s.get("forbid_item_level_edges") is True, "")
    n_item = con.execute(
        "SELECT COUNT(*) FROM edges WHERE relation='aligned_to_quality_level' "
        "AND src_id LIKE 'question:%'"
    ).fetchone()[0]
    check("无题目级 quality 对齐边 (禁发明细映射)", n_item == 0, f"{n_item}")


def check_theme_layers(con: duckdb.DuckDBPyConnection, check) -> None:
    """theme provenance 分层: layers 求和==边数; cross=0; mixed_forbidden."""
    from backend.services.exam_point.loader import theme_distribution_layers
    layers = theme_distribution_layers(con)
    check("theme_layers 非空", bool(layers), str(layers)[:80])
    n_sql = con.execute(
        "SELECT COUNT(*) FROM edges e "
        "JOIN exam_questions q ON ('question:'||q.question_id)=e.src_id AND q.province LIKE '辽宁%' "
        "WHERE e.relation='tests_exam_point' "
        "AND json_extract_string(e.evidence_json,'$.dimension')='theme_l2' "
        "AND q.source_repo NOT LIKE 'eol_xgkii%'"
    ).fetchone()[0]
    n_layers = 0
    for era, dims in layers.items():
        pack = dims.get("theme_l2") or {}
        h = pack.get("honesty") or {}
        check(f"theme_l2 {era} mixed_forbidden", h.get("mixed_forbidden") is True, str(h))
        check(f"theme_l2 {era} cross==0", h.get("analysis_cross_verified") == 0, str(h))
        for _name, rows in (pack.get("layers") or {}).items():
            n_layers += sum(r["n"] for r in rows)
    check("theme_l2 layers 求和 == 篇章级边数", n_layers == n_sql, f"layers={n_layers} sql={n_sql}")


def check_grammar_point_rollup(con: duckdb.DuckDBPyConnection, check) -> None:
    """九桶只读派生; 平行考查边=0; 对账 tests_grammar."""
    from backend.services.exam_point.grammar_point_rollup import grammar_point_rollup
    import yaml
    from pathlib import Path
    tax = yaml.safe_load(Path("backend/config/exam_point_taxonomy.yaml").read_text(encoding="utf-8"))
    gp = None
    # taxonomy 可能是 {dimensions: {grammar_point: ...}} 或扁平
    for root in (tax, tax.get("dimensions") or {}, tax.get("exam_point_dimensions") or {}):
        if isinstance(root, dict) and isinstance(root.get("grammar_point"), dict):
            gp = root["grammar_point"]
            break
    st = (gp or {}).get("status")
    check("taxonomy grammar_point status ∈ {derived_rollup,pending}",
          st in ("derived_rollup", "pending"), f"status={st}")
    r = grammar_point_rollup(con)
    check("rollup derived_from=tests_grammar", r["derived_from"] == "tests_grammar", "")
    check("rollup parallel exam_point grammar_point 边==0", r["parallel_exam_point_edges"] == 0, str(r["parallel_exam_point_edges"]))
    check("rollup parallel tests_grammar_point 边==0", r["parallel_tests_grammar_point_edges"] == 0, str(r["parallel_tests_grammar_point_edges"]))
    check("rollup assigned+unbucketed == n_tests_grammar_edges_read",
          r["n_edges_assigned_to_buckets"] + r["n_edges_unbucketed"] == r["n_tests_grammar_edges_read"],
          f"{r['n_edges_assigned_to_buckets']}+{r['n_edges_unbucketed']} vs {r['n_tests_grammar_edges_read']}")
    check("rollup report_as 绝对计数", r["report_as"] == "absolute_count_not_percentage", r["report_as"])
