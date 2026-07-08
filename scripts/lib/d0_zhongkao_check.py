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
    # 坑(2026-07-08 Phase E4 发现): 原查询靠 attrs_json.source='junior_curriculum_hujiao' 这个
    # 标记计数——但 exam_coverage.py 是 nodes.attrs_json 的**唯一writer**(坑14修复架构, 见该
    # 文件头注), 它对同时也在 cefr_vocab(国家课标, 跨学段共享)里的词会整段覆盖attrs_json,
    # 抹掉这个仅供信息展示、无任何消费者依赖的source标记(实测: german/grammar/sound等5+词
    # 验证均如此, 不是bug是架构使然)。改查**节点是否存在**(真正关心的事: 初中课标/沪教词表
    # 里的词有没有materialize成图节点), 不依赖会被单一writer覆盖的标记字段存活。
    from backend.services.data_sources.extract.junior.vocab import junior_word_stages
    jr_words = set(junior_word_stages())
    n_jrw = con.execute(
        "SELECT COUNT(*) FROM nodes n JOIN (SELECT UNNEST(?) AS w) j ON n.concept_id = 'word:' || j.w",
        [list(jr_words)],
    ).fetchone()[0] if jr_words else 0
    check("初中课标/沪教词表词 全部materialize成word节点(~1900, 含跨学段共享+初中独有两类)",
          n_jrw == len(jr_words), f"{n_jrw}/{len(jr_words)}")
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
    """答案保真 (审计 HIGH): 2024 题面/答案均已获取(2026-07-08解walled), 答案仍是历史交付重点;
    损坏(list-repr/小写/越界)须门抓.

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
    # 坑(2026-07-08 全网挖掘): 2024题面此前5渠道确认门控(walled=45), 本次找到第6渠道
    # (zhongkao.com图片版系列文章, 与既有答案图11.png同站不同文章)PaddleOCR×视觉核对补全,
    # walled状态解除(见 data/junior_high/exams/2024_liaoning/paper_structure.json stem_walled=false)。
    check("中考 2024 题面已解除 walled (2026-07-08 找到题面第6渠道, 不再是源头不可得)",
          n_walled == 0, f"{n_walled}/45")
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
    raw_question真实(非walled), 只是仅语篇填空10题answer非空; 2024年45题(2026-07-08全网
    挖掘找到题面第6渠道, 见 junior/qbank.py 模块docstring)raw_question同样转真, 且2024
    全45题答案齐全(2025缺35题答案)——故90题(2年合计, 非45题)可入question_bank+建
    tests_word边; tests_grammar仅20题语篇填空(答案+考点齐全, 2024/2025各10)可建, 样本量
    薄只报绝对数量不报占比。question:ZK-%节点须剪至有边覆盖(防孤儿)。
    """
    print("\n=== (48) 中考关联层 question_bank/tests_word/tests_grammar (Phase E3) ===")
    n_qb = con.execute("SELECT COUNT(*) FROM question_bank WHERE origin_ref LIKE 'ZK-%'").fetchone()[0]
    check("2024+2025共90题(全部真题面, 2026-07-08解2024 walled) → question_bank",
          n_qb == 90, f"{n_qb}")
    bad_stem = con.execute(
        "SELECT COUNT(*) FROM question_bank WHERE origin_ref LIKE 'ZK-%' AND stem LIKE '%walled%'"
    ).fetchone()[0]
    check("question_bank无walled占位符冒充题面 (D0诚实)", bad_stem == 0, f"{bad_stem}")
    n_tw = con.execute(
        "SELECT COUNT(*) FROM edges WHERE relation='tests_word' AND src_id LIKE 'question:ZK-%'"
    ).fetchone()[0]
    check("中考tests_word边>0 (90题题面驱动, 复用exam_vocab._lemma_tokens同口径)", n_tw > 0, f"{n_tw}")
    n_tg = con.execute(
        "SELECT COUNT(*) FROM edges WHERE relation='tests_grammar' AND src_id LIKE 'question:ZK-%'"
    ).fetchone()[0]
    check("中考tests_grammar边>=15 (20题语篇填空样本薄, 精确匹配后19/20题命中, 部分1题→2边)",
          n_tg >= 15, f"{n_tg}")
    n_orphan = con.execute(
        "SELECT COUNT(*) FROM nodes n WHERE concept_id LIKE 'question:ZK-%' "
        "AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.src_id=n.concept_id OR e.dst_id=n.concept_id)"
    ).fetchone()[0]
    check("question:ZK-%节点无孤儿 (剪除无文本/语法信号的题, 防伪完整感, 同E1 unit:节点先例)",
          n_orphan == 0, f"{n_orphan}")
    exam_type_tags = con.execute(
        "SELECT COUNT(*) FROM question_tags qt JOIN question_bank qb ON qt.qb_id=qb.qb_id "
        "WHERE qb.origin_ref LIKE 'ZK-%' AND qt.tag_id='exam_type:中考'"
    ).fetchone()[0]
    check("90题全打exam_type:中考标签 (供组卷/学情按学段过滤, 不与高考题混淆)",
          exam_type_tags == 90, f"{exam_type_tags}/90")


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
    """Phase E3b(2026-07-07起): 中考genre/theme分类 → exam_point节点+tests_exam_point边.

    数据源: 2025年8篇真实文章双独立视角分类, 只保留genre+theme完全一致的7篇(40题); 1篇
    (养老院唱歌故事)theme判断不一致诚实排除标needs_review。2026-07-08补2024年4篇(用户
    "颗粒度对标高考"拍板): B/D篇两维度完全一致入库(8题), A/C篇各有一维度分歧按同一惯例
    整篇排除。现覆盖48题(11篇一致文章), 相对90题库样本量薄, 不报占比。
    """
    print("\n=== (50) 中考genre/theme分类 exam_point (Phase E3b) ===")
    n_ep = con.execute(
        "SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' AND src_id LIKE 'question:ZK-%'"
    ).fetchone()[0]
    check("中考tests_exam_point边==144 (48题×3维度genre/theme/theme_l2, 11篇一致文章)",
          n_ep == 144, f"{n_ep}")
    n_qids = con.execute(
        "SELECT COUNT(DISTINCT src_id) FROM edges WHERE relation='tests_exam_point' "
        "AND src_id LIKE 'question:ZK-%'"
    ).fetchone()[0]
    check("覆盖48道题(11篇一致文章, 90题库里样本量薄不报占比)", n_qids == 48, f"{n_qids}")
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


def check_zhongkao_exam_focus(con: duckdb.DuckDBPyConnection, check) -> None:
    """Phase F2(2026-07-08, 用户拍板"中考自成体系, 颗粒度对标高考的考点分析, 不复刻设问思维"):
    k12.zhongkao_exam_point_summary 只读聚合已有边(genre/theme_l2/tests_grammar/tests_word),
    验output结构闭合, 不重复验底层边正确性(已由check_junior_exam_point/check_qbank_grammar_link覆盖)。
    """
    print("\n=== (51) 中考考查重点 zhongkao_exam_point_summary (Phase F2) ===")
    from backend.services.k12 import zhongkao_exam_point_summary
    r = zhongkao_exam_point_summary(con)
    check("genre_分布非空且总和==48(同check_junior_exam_point已锁的48题)",
          sum(x["n"] for x in r["genre_分布"]) == 48, f"{sum(x['n'] for x in r['genre_分布'])}")
    check("theme_l2_分布非空且总和==48", sum(x["n"] for x in r["theme_l2_分布"]) == 48,
          f"{sum(x['n'] for x in r['theme_l2_分布'])}")
    check("语法考查重点非空(≥1条, 复用已有tests_grammar边)", len(r["语法考查重点"]) > 0,
          f"{len(r['语法考查重点'])}")
    check("高频实词非空(≥1条, 复用已有tests_word边)", len(r["高频实词"]) > 0,
          f"{len(r['高频实词'])}")
    check("scope_note含4项诚实声明(sample_type/genre_theme_coverage/grammar_coverage/vocab_coverage)",
          set(r["scope_note"].keys()) == {"sample_type", "genre_theme_coverage",
                                           "grammar_coverage", "vocab_coverage"},
          f"{list(r['scope_note'].keys())}")
