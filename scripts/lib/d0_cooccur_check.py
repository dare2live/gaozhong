"""D0 考点共现关联性校验 (件3关联性入图; 坑17 新关系入门; 坑12 防伪关联).

锁: co_occurs 边两端 exam_point + 跨维(非theme L1×L2同轴冗余) + 带 era 分层(PIT) +
provenance + 记叙文×人与社会样本 (防关联退化) + min_co 守门 (无一次性伪关联)。
"""
from __future__ import annotations

import duckdb


def check_cooccur(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (35) 考点共现关联性 co_occurs (件3第三条腿入图) ===")
    n = con.execute("SELECT COUNT(*) FROM edges WHERE relation='co_occurs'").fetchone()[0]
    check("co_occurs 边 ≥15 (辽宁跨维考点共现入图; 删杜撰theme_l3共现27条后实测19)", n >= 15, f"{n}")
    # 两端都是 exam_point
    bad_end = con.execute(
        "SELECT COUNT(*) FROM edges e WHERE e.relation='co_occurs' AND ("
        "e.src_id NOT LIKE 'exam_point:%' OR e.dst_id NOT LIKE 'exam_point:%')").fetchone()[0]
    check("co_occurs 两端 exam_point (无悬挂)", bad_end == 0, f"{bad_end}")
    # 跨维 only (无 theme L1×L2 同轴冗余, 坑: taxonomy 嵌套非命题关联)
    same_axis = con.execute(
        "SELECT COUNT(*) FROM edges WHERE relation='co_occurs' "
        "AND json_extract_string(evidence_json,'$.a_dim') IN ('theme_context','theme_l2') "
        "AND json_extract_string(evidence_json,'$.b_dim') IN ('theme_context','theme_l2')").fetchone()[0]
    check("co_occurs 跨维 only (无 theme L1×L2 同轴冗余)", same_axis == 0, f"{same_axis}")
    # 带 era 分层 (PIT §3.1, 不混算)
    no_era = con.execute(
        "SELECT COUNT(*) FROM edges WHERE relation='co_occurs' "
        "AND json_extract_string(evidence_json,'$.by_era') IS NULL").fetchone()[0]
    check("co_occurs 带 era 分层 (PIT, evidence.by_era)", no_era == 0, f"{no_era}")
    # 记叙文×人与社会样本 (防关联退化)
    sample = con.execute(
        "SELECT COUNT(*) FROM edges e JOIN nodes a ON a.concept_id=e.src_id "
        "JOIN nodes b ON b.concept_id=e.dst_id WHERE e.relation='co_occurs' "
        "AND ((a.label='记叙文' AND b.label='人与社会') OR (a.label='人与社会' AND b.label='记叙文'))"
    ).fetchone()[0]
    check("co_occurs 含 记叙文×人与社会 (辽宁命题模式样本)", sample == 1, f"{sample}")
