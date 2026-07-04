"""D0 主题特征词汇关联性校验 (件3 词汇↔主题; 坑17 新关系入门; 坑5/坑12 防伪关联).

锁: characterizes_theme 两端(word→theme) + 区分度∈[阈,1] + provenance诚实标启发式 +
辽宁锚定 + plastic→环境保护 样本(防关联退化) + 词必在考试词典(real exam word)。
"""
from __future__ import annotations

import duckdb

from scripts.lib.d0_baselines import B


def check_theme_vocab(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (36) 主题特征词汇关联性 characterizes_theme (词汇↔主题) ===")
    n = con.execute("SELECT COUNT(*) FROM edges WHERE relation='characterizes_theme'").fetchone()[0]
    check("characterizes_theme 边 ≥30 (主题特征词入图)", n >= B('theme_vocab_min'), f"{n}")
    bad = con.execute(
        "SELECT COUNT(*) FROM edges e WHERE e.relation='characterizes_theme' AND ("
        "NOT EXISTS (SELECT 1 FROM nodes WHERE concept_id=e.src_id AND node_type='word') "
        "OR e.dst_id NOT LIKE 'exam_point:theme%')").fetchone()[0]
    check("characterizes_theme 两端 word→theme (无悬挂)", bad == 0, f"{bad}")
    # 区分度 ∈ [0.6, 1] (co/total)
    bad_d = con.execute(
        "SELECT COUNT(*) FROM edges WHERE relation='characterizes_theme' AND (weight < 0.6 OR weight > 1.0)"
    ).fetchone()[0]
    check("区分度 weight∈[0.6,1] (功能词处处现→低区分度已滤, 坑5)", bad_d == 0, f"{bad_d}")
    # provenance 诚实标启发式 (非权威, 教研未逐词标主题)
    bad_p = con.execute(
        "SELECT COUNT(*) FROM edges WHERE relation='characterizes_theme' "
        "AND json_extract_string(evidence_json,'$.provenance')<>'distinctiveness_heuristic'").fetchone()[0]
    check("provenance=distinctiveness_heuristic (诚实标启发式非权威)", bad_p == 0, f"{bad_p}")
    # 词必在考试词典 (real exam word, 滤噪声)
    not_dict = con.execute(
        "SELECT COUNT(*) FROM edges e WHERE e.relation='characterizes_theme' "
        "AND NOT EXISTS (SELECT 1 FROM exam_vocabulary ev WHERE 'word:'||ev.word=e.src_id)").fetchone()[0]
    check("特征词必在考试词典 (real exam word)", not_dict == 0, f"{not_dict}")
    # plastic→环境保护 样本 (防关联退化)
    s = con.execute(
        "SELECT COUNT(*) FROM edges e JOIN nodes n ON n.concept_id=e.dst_id "
        "WHERE e.relation='characterizes_theme' AND e.src_id='word:plastic' AND n.label='环境保护'").fetchone()[0]
    check("plastic→环境保护 特征词样本 (辽宁命题模式)", s == 1, f"{s}")


def check_theme_of_unit(con: duckdb.DuckDBPyConnection, check) -> None:
    """D0 单元↔主题 theme_of_unit (坑17: 此关系此前 D0/moth 零覆盖, 全数据审计 2026-07-04 补).

    锁: 两端有效(unit/theme 均存在) + 短关键词(<4字符)词边界匹配防子串误配
    (links_extra.py._hint_matches; 实锤: 'ART'子串曾误命中'st-ART'/'e-ARTh')。
    """
    print("\n=== (37) 单元↔主题 theme_of_unit (unit→theme, 短关键词词边界防子串误配) ===")
    bad = con.execute(
        "SELECT COUNT(*) FROM edges e WHERE e.relation='theme_of_unit' AND ("
        "NOT EXISTS (SELECT 1 FROM nodes WHERE concept_id=e.src_id AND node_type='unit') "
        "OR NOT EXISTS (SELECT 1 FROM nodes WHERE concept_id=e.dst_id AND node_type='theme'))"
    ).fetchone()[0]
    check("theme_of_unit 两端 unit→theme (无悬挂)", bad == 0, f"{bad}")
    false_positive_units = [
        "unit:waiyan/bixiu_1/U1",   # "A new start" — 曾被 'ART' 子串误配 st-ART
        "unit:waiyan/bixiu_2/U6",   # "Earth first" — 曾被 'ART' 子串误配 e-ARTh
    ]
    still_tagged = con.execute(
        f"SELECT src_id FROM edges WHERE relation='theme_of_unit' AND src_id IN "
        f"({','.join('?' * len(false_positive_units))}) AND dst_id LIKE '%文学、艺术与体育%'",
        false_positive_units).fetchall()
    check("已知'ART'子串误配单元不再挂'文学、艺术与体育' (防回归)",
          not still_tagged, f"仍误配: {still_tagged}")
