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
