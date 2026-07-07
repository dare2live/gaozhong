"""D0 中考真题入库校验 (K12 inc1; 新数据必入 D0 强校验, 坑17).

从 data_accuracy_check 抽出 (避 god-module Rule8); check 由调用方传入, 失败追加 FAILURES。
锁: 中考90题入 exam_questions_all + 不混口径(辽宁省统一) + 视图隔离(高考视图不含中考)。
"""
from __future__ import annotations

import duckdb

from scripts.lib.d0_baselines import B


def check_zhongkao(con: duckdb.DuckDBPyConnection, check) -> None:
    """中考真题 DB 入库 4 项 D0 校验 (exam_type 判别维 + 视图隔离)."""
    print("\n=== (27) 中考真题入库 (exam_type 判别 + 视图隔离, K12 inc1) ===")
    n_zk = con.execute("SELECT COUNT(*) FROM exam_questions_all WHERE exam_type='中考'").fetchone()[0]
    check("中考真题 90 题入库 (2024×45 + 2025×45)", n_zk == B('zhongkao_total'), f"{n_zk}")
    by_y = dict(con.execute(
        "SELECT year, COUNT(*) FROM exam_questions_all WHERE exam_type='中考' GROUP BY year").fetchall())
    check("中考 2024/2025 各 45 题", by_y.get(2024) == B('zhongkao_per_year') and by_y.get(2025) == B('zhongkao_per_year'), f"{by_y}")
    bad = con.execute(
        "SELECT COUNT(*) FROM exam_questions_all WHERE exam_type='中考' "
        "AND (province NOT LIKE '辽宁%' OR paper_type NOT LIKE '辽宁省统一%')").fetchone()[0]
    check("中考 province=辽宁 + paper_type=辽宁省统一 (不混口径, master §1.2)", bad == 0, f"{bad} 例口径不符")
    leak = con.execute("SELECT COUNT(*) FROM exam_questions WHERE question_id LIKE 'ZK-%'").fetchone()[0]
    zk_view = con.execute("SELECT COUNT(*) FROM zhongkao_questions").fetchone()[0]
    check("视图隔离 (高考视图 exam_questions 无中考 + zhongkao_questions=90)",
          leak == 0 and zk_view == 90, f"高考视图含中考={leak} 中考视图={zk_view}")
    _check_answer_fidelity(con, check)
    # inc2: 初中节点 (单库 node_type/stage 判别)
    n_jrw = con.execute(
        "SELECT COUNT(*) FROM nodes WHERE node_type='word' AND attrs_json LIKE '%junior_curriculum%'").fetchone()[0]
    check("初中独有 word 节点入库 (~112, stage 小学/初中)", 100 <= n_jrw <= 140, f"{n_jrw}")
    n_jrg = con.execute("SELECT COUNT(*) FROM nodes WHERE concept_id LIKE 'grammar:jr:%'").fetchone()[0]
    bad_g = con.execute(
        "SELECT COUNT(*) FROM nodes WHERE concept_id LIKE 'grammar:jr:%' AND attrs_json NOT LIKE '%初中%'").fetchone()[0]
    check("初中 grammar 节点=71 (grammar:jr: 命名空间不碰高中, 全 stage=初中)",
          n_jrg == B('junior_grammar') and bad_g == 0, f"{n_jrg} 节点, {bad_g} 无初中标")
    n_at = con.execute("SELECT COUNT(*) FROM edges WHERE relation='at_stage'").fetchone()[0]
    check("stage 维 materialize: at_stage 边覆盖初中+高中词 (inc2+inc3, ≥2000)", n_at >= 2000, f"{n_at}")
    # inc3: 跨阶段 deepens 边 (10维语法蓝图 K12衔接); 审计HIGH#7: 全71初中语法点都有衔接边(精确59+别名12), 无衔接孤儿
    n_jr_g = con.execute("SELECT COUNT(*) FROM nodes WHERE concept_id LIKE 'grammar:jr:%'").fetchone()[0]
    n_linked = con.execute(
        "SELECT COUNT(DISTINCT src_id) FROM edges WHERE relation='deepens' AND src_id LIKE 'grammar:jr:%'").fetchone()[0]
    check("全部初中语法点有跨阶段 deepens 衔接边 (无衔接孤儿; 别名补12时态/非谓语/定从)",
          n_jr_g == n_linked and n_jr_g == 71, f"{n_linked}/{n_jr_g} 衔接")
    _check_distribution_served(con, check)


def _check_distribution_served(con, check) -> None:
    """zhongkao_distribution as-served (坑17): service 输出口径闭合 —
    by_question_type 求和==90 全量 / 语篇填空考点 20 行 / _kaodian_pivot 逐空 reshape 不丢。"""
    from backend.services import k12
    d = k12.zhongkao_distribution(con)
    n_bt = sum(x["n"] for x in d["by_question_type"])
    check("中考分布 by_question_type 求和==90 (as-served 全量不丢)", n_bt == B('zhongkao_total'), f"{n_bt}")
    kd = d["语篇填空考点"]
    check("语篇填空逐空考点 20 行 (2年×10空, analysis 非空)", len(kd) == B('zhongkao_kaodian'), f"{len(kd)}")
    pv = d["语篇填空_pivot"]
    filled = sum(1 for r in pv["rows"] for y in pv["years"] if r["考点"].get(y))
    check("_kaodian_pivot reshape 无丢 (非空格==考点行数)", filled == len(kd),
          f"pivot填充{filled} vs 考点{len(kd)}")


def _check_answer_fidelity(con, check) -> None:
    """答案保真 (审计 HIGH): 2024 题面 walled, 答案是核心交付; 损坏(list-repr/小写/越界)须门抓.

    按题型作用域 — 只对 MCQ(选项字母答案)断言; 语法填空/开放问答/书面表达是自由词不约束 (坑16 防套错 schema)。
    """
    bad_ad = con.execute(
        "SELECT question_id, answer FROM exam_questions_all WHERE exam_type='中考' "
        "AND question_type IN ('完形填空', '阅读理解(四选一)') "
        "AND answer IS NOT NULL AND TRIM(answer) <> '' AND TRIM(answer) NOT IN ('A','B','C','D')"
    ).fetchall()
    check("中考 MCQ(四选一/完形) 答案 ∈ {A-D} (保真; 防小写/list-repr/越界E污染)",
          not bad_ad, f"{bad_ad[:5]}")
    bad_e = con.execute(
        "SELECT question_id, answer FROM exam_questions_all WHERE exam_type='中考' "
        "AND question_type LIKE '阅读理解(五选四%' "
        "AND answer IS NOT NULL AND TRIM(answer) <> '' AND TRIM(answer) NOT IN ('A','B','C','D','E')"
    ).fetchall()
    check("中考 五选四 答案 ∈ {A-E} (保真)", not bad_e, f"{bad_e[:5]}")
    n_2024 = con.execute(
        "SELECT COUNT(*) FROM exam_questions_all WHERE exam_type='中考' AND year=2024 "
        "AND answer IS NOT NULL AND TRIM(answer) <> ''").fetchone()[0]
    check("中考 2024 全 45 题答案非空 (answer-key-driven, 答案=唯一交付不能丢)", n_2024 == 45, f"{n_2024}/45")
    _check_content_status(con, check)


def _check_content_status(con, check) -> None:
    """空心诚实标记 (审计 HIGH#8): zhongkao_questions.content_status 显式标题面/答案完整性, 无静默空心.

    前端/分析据此显示「题面门控/答案待补」徽章, 不把空心记录当完整渲染。
    """
    n_null = con.execute(
        "SELECT COUNT(*) FROM zhongkao_questions WHERE content_status IS NULL").fetchone()[0]
    check("中考全题有 content_status (无静默空心; 派生于 raw_question+answer)", n_null == 0, f"{n_null} 题无状态")
    mismark = con.execute(
        "SELECT COUNT(*) FROM zhongkao_questions WHERE content_status='complete' "
        "AND (raw_question LIKE 'walled%' OR answer IS NULL OR TRIM(answer)='')").fetchone()[0]
    check("content_status='complete' 必真完整 (无空心冒充完整)", mismark == 0, f"{mismark} 误标")
    n_walled = con.execute(
        "SELECT COUNT(*) FROM zhongkao_questions WHERE year=2024 AND content_status='stem_walled'").fetchone()[0]
    check("中考 2024 全 45 题题面诚实标 walled (免费源门控, 不伪造题面)", n_walled == 45, f"{n_walled}/45")
    # 坑(2026-07-04 全数据审计): 2025 年 15 题(21-30完形填空+31-40语篇填空+41-45阅读表达/作文)
    # 曾因 extract_zhongkao.py._set_stem 条件写反(旧版要求options非空, 开放题/完形填空
    # 均不满足)被静默漏转录, 误标 stem_walled 冒充"题面门控"——实际 exam_ocr.txt 早有完整
    # 原文(manifest.json/paper_structure.json 均自述 2025="题干完整"), 非源头不可得。
    # 补 _parse_yupian_tiankong/_parse_wanxing 共享段落解析后, 2025 应=0 题 stem_walled
    # (与 paper_structure.json 自述"2025=题干完整(无答案key)"一致, 不同于2024真实源头门控)。
    n_walled_2025 = con.execute(
        "SELECT COUNT(*) FROM zhongkao_questions WHERE year=2025 AND content_status='stem_walled'").fetchone()[0]
    check("中考 2025 题面0 stem_walled (题面本已采集到, 非2024式源头不可得)", n_walled_2025 == 0, f"{n_walled_2025}/45")


def check_qbank_grammar_link(con: duckdb.DuckDBPyConnection, check) -> None:
    """Phase E3 中考关联层(2026-07-07): question_bank镶入 + tests_word/tests_grammar边.

    直接查库核实(非委托agent臆测)纠正此前"仅20题可用"的过度悲观结论: 2025年45题(全6题型)
    raw_question真实(非walled), 只是仅语篇填空10题answer非空——故45题(非20题)可入
    question_bank+建tests_word边; tests_grammar仅20题语篇填空(答案+考点齐全, 2024/2025各10)
    可建, 样本量薄只报绝对数量不报占比。question:ZK-%节点须剪至有边覆盖(防孤儿)。
    """
    print("\n=== (48) 中考关联层 question_bank/tests_word/tests_grammar (Phase E3) ===")
    n_qb = con.execute("SELECT COUNT(*) FROM question_bank WHERE origin_ref LIKE 'ZK-%'").fetchone()[0]
    check("2025年45题(全部真题面, 2024全walled不入库) → question_bank", n_qb == 45, f"{n_qb}")
    bad_stem = con.execute(
        "SELECT COUNT(*) FROM question_bank WHERE origin_ref LIKE 'ZK-%' AND stem LIKE '%walled%'"
    ).fetchone()[0]
    check("question_bank无walled占位符冒充题面 (D0诚实)", bad_stem == 0, f"{bad_stem}")
    n_tw = con.execute(
        "SELECT COUNT(*) FROM edges WHERE relation='tests_word' AND src_id LIKE 'question:ZK-%'"
    ).fetchone()[0]
    check("中考tests_word边>0 (45题题面驱动, 复用exam_vocab._lemma_tokens同口径)", n_tw > 0, f"{n_tw}")
    n_tg = con.execute(
        "SELECT COUNT(*) FROM edges WHERE relation='tests_grammar' AND src_id LIKE 'question:ZK-%'"
    ).fetchone()[0]
    check("中考tests_grammar边>=15 (20题语篇填空样本薄, 精确匹配后17/20题命中, 部分1题→2边)",
          n_tg >= 15, f"{n_tg}")
    n_orphan = con.execute(
        "SELECT COUNT(*) FROM nodes n WHERE concept_id LIKE 'question:ZK-%' "
        "AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.src_id=n.concept_id OR e.dst_id=n.concept_id)"
    ).fetchone()[0]
    check("question:ZK-%节点无孤儿 (剪除38题无文本/语法信号的题, 防伪完整感, 同E1 unit:节点先例)",
          n_orphan == 0, f"{n_orphan}")
    exam_type_tags = con.execute(
        "SELECT COUNT(*) FROM question_tags qt JOIN question_bank qb ON qt.qb_id=qb.qb_id "
        "WHERE qb.origin_ref LIKE 'ZK-%' AND qt.tag_id='exam_type:中考'"
    ).fetchone()[0]
    check("45题全打exam_type:中考标签 (供组卷/学情按学段过滤, 不与高考题混淆)",
          exam_type_tags == 45, f"{exam_type_tags}/45")


def check_k12_grammar_bridge(con: duckdb.DuckDBPyConnection, check) -> None:
    """Phase E5(2026-07-07) K12衔接视图: 初中语法点→高中deepens→高考exam_status+中考印证.

    只读聚合已有边(deepens/tests_grammar)+已有attrs(exam_status), 本检查验output结构闭合
    (records逐条字段齐全+summary计数与records重新聚合一致), 不重复验底层边正确性(那些已由
    check_zhongkao自身的deepens/tests_grammar断言覆盖)。
    """
    print("\n=== (49) K12衔接视图 junior_senior_grammar_bridge (Phase E5) ===")
    from backend.services.exam_point import junior_senior_grammar_bridge
    r = junior_senior_grammar_bridge(con)
    recs = r["records"]
    check("records覆盖全部71个初中语法点 (无衔接孤儿, 同check_zhongkao已锁的71)",
          len(recs) == 71, f"{len(recs)}")
    bad = [x for x in recs if not x.get("senior_grammar_id")]
    check("records全部有senior_grammar_id (deepens 100%覆盖, 无衔接孤儿)", not bad, f"{len(bad)}条缺失")
    n_verified_recompute = sum(1 for x in recs if x["zhongkao_verified"])
    check("summary.n_junior_items_with_zhongkao_verification 与records重新聚合一致",
          r["summary"]["n_junior_items_with_zhongkao_verification"] == n_verified_recompute,
          f"summary={r['summary']['n_junior_items_with_zhongkao_verification']} recompute={n_verified_recompute}")
    check("summary.report_as='absolute_count_not_percentage' (样本量薄不报占比, 同坑12)",
          r["summary"].get("report_as") == "absolute_count_not_percentage", f"{r['summary'].get('report_as')}")
    check("scope_note含zhongkao_coverage_limit+dimension_isolation两项诚实声明",
          set(r["scope_note"].keys()) == {"zhongkao_coverage_limit", "dimension_isolation"},
          f"{list(r['scope_note'].keys())}")


def check_junior_exam_point(con: duckdb.DuckDBPyConnection, check) -> None:
    """Phase E3b(2026-07-07): 中考genre/theme分类 → exam_point节点+tests_exam_point边.

    数据源: 2025年8篇真实文章双独立视角分类, 只保留genre+theme完全一致的7篇(40题); 1篇
    (养老院唱歌故事)theme判断不一致诚实排除标needs_review。样本量薄(40/90题), 不报占比。
    """
    print("\n=== (50) 中考genre/theme分类 exam_point (Phase E3b) ===")
    n_ep = con.execute(
        "SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND src_id LIKE 'question:ZK-%'"
    ).fetchone()[0]
    check("中考tests_exam_point边==120 (40题×3维度genre/theme/theme_l2, 7篇一致文章)",
          n_ep == 120, f"{n_ep}")
    n_qids = con.execute(
        "SELECT COUNT(DISTINCT src_id) FROM edges WHERE relation='tests_exam_point' "
        "AND src_id LIKE 'question:ZK-%'"
    ).fetchone()[0]
    check("覆盖40道题(7篇一致文章, 90题库里样本量薄不报占比)", n_qids == 40, f"{n_qids}")
    bad_genre = con.execute(
        "SELECT COUNT(*) FROM nodes WHERE concept_id LIKE 'exam_point:genre:%' "
        "AND label NOT IN ('议论文','应用文','书评介绍','新闻报道','记叙文','说明文')"
    ).fetchone()[0]
    check("genre值域未越界(复用高中6值域, 未发明新词)", bad_genre == 0, f"{bad_genre}")
    bad_l2 = con.execute(
        "SELECT COUNT(*) FROM nodes WHERE concept_id LIKE 'exam_point:theme_l2:%' "
        "AND label NOT IN ('生活与学习','做人与做事','社会服务与人际沟通','文学、艺术与体育',"
        "'历史、社会与文化','科学与技术','自然生态','环境保护','灾害防范','宇宙探索')"
    ).fetchone()[0]
    check("theme_l2值域未越界(义务教育课标2022官方10主题群, PDF p.21逐字核实, 未发明)",
          bad_l2 == 0, f"{bad_l2}")
