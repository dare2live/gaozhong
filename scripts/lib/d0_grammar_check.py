"""D0 (3) 语法基石校验 — 从 data_accuracy_check.py 抽出 (2026-07-08, 该文件超400行god-module阈值).

check 由调用方传入(与其余 scripts/lib/d0_*.py 同一约定, 失败追加调用方的 FAILURES)。
"""
from __future__ import annotations

import duckdb

from scripts.lib.d0_baselines import B


def _audit_ok(con: duckdb.DuckDBPyConnection, kind: str) -> bool:
    rows = con.execute(
        "SELECT severity FROM audit_findings WHERE audit_kind LIKE ? OR audit_kind = ?",
        [f"%{kind}%", kind],
    ).fetchall()
    return bool(rows) and all(r[0] == "OK" for r in rows)


def check_grammar(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (3) 语法 ===")
    n_g = con.execute("SELECT COUNT(*) FROM grammar_items").fetchone()[0]
    n_orphan = con.execute(
        "SELECT COUNT(*) FROM grammar_items WHERE parent_id IS NOT NULL "
        "AND parent_id NOT IN (SELECT grammar_item_id FROM grammar_items)"
    ).fetchone()[0]
    check("grammar_items 行 == 108", n_g == B('grammar_items'), f"{n_g}")  # 106→108: 补限制性/非限制性定语从句(原_skip_line误杀)
    check("grammar DAG 无环 (audit OK)", _audit_ok(con, "grammar_dag"))
    check("grammar parent_id 引用完整", n_orphan == 0, f"orphan={n_orphan}")
    n_occ = con.execute("SELECT COUNT(*) FROM grammar_occurrences").fetchone()[0]  # §1.2 语法per-unit
    # version_key='hujiao'(初中) 用 grammar:jr: 节点校验, 其余(高中)用 grammar_items 表校验
    # (2026-07-08 Phase E4 补初中lineage后发现: 原查询未按version_key分流, 把初中rows误判FK悬挂)
    bad_occ_senior = con.execute(
        "SELECT COUNT(*) FROM grammar_occurrences WHERE version_key != 'hujiao' "
        "AND grammar_item_id NOT IN (SELECT grammar_item_id FROM grammar_items)").fetchone()[0]
    bad_occ_junior = con.execute("""
        SELECT COUNT(*) FROM grammar_occurrences go WHERE go.version_key='hujiao'
        AND NOT EXISTS (SELECT 1 FROM nodes n WHERE n.concept_id = 'grammar:jr:' || go.grammar_item_id)
    """).fetchone()[0]
    check("grammar_occurrences 已填(§1.2 语法per-unit)", n_occ >= B('grammar_occ_min'), f"{n_occ}")
    check("grammar_occurrences FK 有效(高中→grammar_items, 初中→grammar:jr:节点, 分流校验)",
          bad_occ_senior == 0 and bad_occ_junior == 0, f"高中悬挂={bad_occ_senior} 初中悬挂={bad_occ_junior}")
