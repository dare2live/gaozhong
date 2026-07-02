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
