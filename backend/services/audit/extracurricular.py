"""超纲词 × 高考真题 cross-check — **只产 OBS finding, 不写 nodes** (用户 2026-05-23 + #14 整改).

定义 (辽宁卷口径, §7):
  - 超纲词 (extracurricular) = unit_vocab_intro NOT IN cefr_vocab 的 word.
  - 高价值超纲 (HV-extra) = 超纲词 ∧ 出现在 ≥ 1 道辽宁真题里.
  - 低价值超纲 (LV-extra) = 超纲词 ∧ 不出现在任何辽宁真题中.

教学意义: HV-extra 必教; LV-extra 可降权/选学.

#14 整改: 原本本模块也整段 UPDATE nodes.attrs_json (在 run_all 里 idx39 先跑),
被后跑的 exam_coverage (idx40) 整段覆盖 → gaokao_hit_count_ln 0 个节点留存。
现在 **nodes.attrs_json 的唯一 writer 是 exam_coverage** (一次写全含 gaokao_hit_count_ln/all
+ teaching_priority); 本模块只读 exam_vocab 单点出命中数, 产 OBS 统计 finding, 不再写 nodes。
"""
from __future__ import annotations

import duckdb

from backend.services.exam_vocab import word_exam_hits_from_edges
from backend.services.vocab_classify import is_real_over

from ._common import finding


def _load_extracurricular(con: duckdb.DuckDBPyConnection) -> set[str]:
    """真超纲词 (textbook − cefr, 且 is_real_over: 排课标屈折/派生/专名; 与 exam_coverage 同口径)."""
    try:
        raw = {row[0] for row in con.execute("""
            SELECT DISTINCT v.word FROM unit_vocab_intro v
            INNER JOIN units u
              ON u.version_key=v.version_key AND u.volume_key=v.volume_key AND u.unit_number=v.unit_number
            LEFT JOIN cefr_vocab c ON c.word = v.word
            WHERE c.word IS NULL
        """).fetchall()}
    except duckdb.CatalogException:
        return set()
    return {w for w in raw if is_real_over(w)}   # 真超纲单一判定点 (3 源一致)


def audit_extracurricular_in_exam(con: duckdb.DuckDBPyConnection) -> list[dict]:
    extra = _load_extracurricular(con)
    if not extra:
        return [finding("extracurricular_vs_exam", "OK", target="extracurricular set",
                        expected="N", actual="0", note="无超纲词 (extractor 未跑或全在课标内)")]
    hits = word_exam_hits_from_edges(con)   # 唯一真相=tests_word 边 (辽宁/全部命中)
    hv_ln = {w for w in extra if hits.get(w, {}).get("ln", 0) > 0}    # 辽宁口径 HV
    hv_all = {w for w in extra if hits.get(w, {}).get("all", 0) > 0}  # 含外省命中
    lv = extra - hv_all
    return [
        finding("extracurricular_vs_exam", "OK",
                target="超纲词 ∩ 高考真题 (辽宁口径, exam_vocab 单点 lemmatize 命中)",
                expected="HV_ln > 0",
                actual=f"HV_ln={len(hv_ln)} HV_all={len(hv_all)} LV={len(lv)}",
                note=f"超纲词总 {len(extra)}; HV_ln 比例 {len(hv_ln)/len(extra):.1%}"),
        finding("extracurricular_vs_exam", "OK",
                target="教学优先级建议 (OBS 描述)", expected="HV_extra 标星",
                actual=f"HV_ln={len(hv_ln)}",
                note="OBS 统计描述; teaching_priority/gaokao_hit_count 由 exam_coverage 单一 writer 写入 nodes (Rule1, 本模块不写)"),
    ]
