"""PIT 版本注册表 + effective_version 单一计算点 (docs/kg_layer_design.md §3.1).

铁律: "按某年对齐哪版课标/教材/卷制" 只在 effective_version 算一次, 别处禁写 year 比较 (Rule1).
锚点 (必修a): exam_paper 按真题年(exam_year); textbook/curriculum/course 按考生入学年(enroll_year).
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import yaml

_ROOT = Path(__file__).resolve().parents[3]
_SEED = _ROOT / "backend" / "config" / "source_versions.yaml"

# 锚点维: 哪些 kind 按真题年对齐, 哪些按入学年 (调用方据此传 year)
_EXAM_YEAR_KINDS = {"exam_paper"}
_ENROLL_YEAR_KINDS = {"curriculum", "textbook", "course"}

_COLS = ("version_id", "kind", "variant", "label",
         "effective_from_year", "effective_to_year", "manifest_ref", "supersedes", "notes")


def version_anchor_year(kind: str) -> str:
    """该 kind 的生效年锚点语义 (供调用方知道该传 exam_year 还是 enroll_year)."""
    if kind in _EXAM_YEAR_KINDS:
        return "exam_year"
    if kind in _ENROLL_YEAR_KINDS:
        return "enroll_year"
    return "unknown"


def load_versions(con: duckdb.DuckDBPyConnection) -> dict:
    """从 source_versions.yaml 灌 source_versions 表 (init_db 调; INSERT OR REPLACE 幂等)."""
    rows = yaml.safe_load(_SEED.read_text(encoding="utf-8")).get("versions", [])
    con.executemany(
        f"INSERT OR REPLACE INTO source_versions ({','.join(_COLS)}) "
        f"VALUES ({','.join(['?'] * len(_COLS))})",
        [[r.get(c) for c in _COLS] for r in rows],
    )
    return {"source_versions": len(rows)}


def effective_version(con: duckdb.DuckDBPyConnection, kind: str, year: int,
                      variant: str | None = None) -> str | None:
    """某年生效的版本 version_id; 无匹配返 None (诚实 unknown, 不假填).

    variant 必填于并发流 kind (textbook=publisher / exam_paper=卷流 / curriculum=学段);
    单流 kind (course) 可省。同 (kind,variant) 同年唯一 (D0 门锁不变量)。
    """
    where = ["kind = ?", "effective_from_year <= ?", "COALESCE(effective_to_year, 9999) >= ?"]
    args: list = [kind, year, year]
    if variant is not None:
        where.append("variant = ?")
        args.append(variant)
    rows = con.execute(
        f"SELECT version_id FROM source_versions WHERE {' AND '.join(where)} "
        f"ORDER BY effective_from_year DESC", args).fetchall()
    return rows[0][0] if rows else None
