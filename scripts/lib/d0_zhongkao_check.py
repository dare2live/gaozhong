"""D0 中考真题入库校验 (K12 inc1; 新数据必入 D0 强校验, 坑17).

从 data_accuracy_check 抽出 (避 god-module Rule8); check 由调用方传入, 失败追加 FAILURES。
锁: 中考90题入 exam_questions_all + 不混口径(辽宁省统一) + 视图隔离(高考视图不含中考)。
"""
from __future__ import annotations

import duckdb


def check_zhongkao(con: duckdb.DuckDBPyConnection, check) -> None:
    """中考真题 DB 入库 4 项 D0 校验 (exam_type 判别维 + 视图隔离)."""
    print("\n=== (27) 中考真题入库 (exam_type 判别 + 视图隔离, K12 inc1) ===")
    n_zk = con.execute("SELECT COUNT(*) FROM exam_questions_all WHERE exam_type='中考'").fetchone()[0]
    check("中考真题 90 题入库 (2024×45 + 2025×45)", n_zk == 90, f"{n_zk}")
    by_y = dict(con.execute(
        "SELECT year, COUNT(*) FROM exam_questions_all WHERE exam_type='中考' GROUP BY year").fetchall())
    check("中考 2024/2025 各 45 题", by_y.get(2024) == 45 and by_y.get(2025) == 45, f"{by_y}")
    bad = con.execute(
        "SELECT COUNT(*) FROM exam_questions_all WHERE exam_type='中考' "
        "AND (province NOT LIKE '辽宁%' OR paper_type NOT LIKE '辽宁省统一%')").fetchone()[0]
    check("中考 province=辽宁 + paper_type=辽宁省统一 (不混口径, master §1.2)", bad == 0, f"{bad} 例口径不符")
    leak = con.execute("SELECT COUNT(*) FROM exam_questions WHERE question_id LIKE 'ZK-%'").fetchone()[0]
    zk_view = con.execute("SELECT COUNT(*) FROM zhongkao_questions").fetchone()[0]
    check("视图隔离 (高考视图 exam_questions 无中考 + zhongkao_questions=90)",
          leak == 0 and zk_view == 90, f"高考视图含中考={leak} 中考视图={zk_view}")
    # inc2: 初中节点 (单库 node_type/stage 判别)
    n_jrw = con.execute(
        "SELECT COUNT(*) FROM nodes WHERE node_type='word' AND attrs_json LIKE '%junior_curriculum%'").fetchone()[0]
    check("初中独有 word 节点入库 (~112, stage 小学/初中)", 100 <= n_jrw <= 140, f"{n_jrw}")
    n_jrg = con.execute("SELECT COUNT(*) FROM nodes WHERE concept_id LIKE 'grammar:jr:%'").fetchone()[0]
    bad_g = con.execute(
        "SELECT COUNT(*) FROM nodes WHERE concept_id LIKE 'grammar:jr:%' AND attrs_json NOT LIKE '%初中%'").fetchone()[0]
    check("初中 grammar 节点=71 (grammar:jr: 命名空间不碰高中, 全 stage=初中)",
          n_jrg == 71 and bad_g == 0, f"{n_jrg} 节点, {bad_g} 无初中标")
    n_at = con.execute("SELECT COUNT(*) FROM edges WHERE relation='at_stage'").fetchone()[0]
    check("at_stage 边连初中节点 (防孤儿 + stage 维 materialize, ≥180)", n_at >= 180, f"{n_at}")
