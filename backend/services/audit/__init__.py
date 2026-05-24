"""Audit package — 数据治理 (完整性 + 准确性 + 关联图谱) 单一入口.

子模块按治理维度切, 每个文件 < 100 行:
  _common.py      共享 helper (sha256/now)
  file_integrity  文件 SHA + manifest 一致
  curriculum      课标 vocab/grammar 召回
  cross_source    课标 vs 外部源 (mahavivo) cross check
  textbook        教材 PDF page / unit 抽取召回
  publisher       辽宁 14 地市 + 8 允许版本 一致性
  graph           ⭐ 图谱治理 (孤儿节点 / DAG 校验 / relation 字典)

新增审计模块只需:
  1. 在子模块写 `def audit_xxx(con) -> list[dict]`
  2. 在 __init__.collect_findings 列表加一行
"""
from __future__ import annotations

from datetime import datetime, timezone

import duckdb

from . import (codequality, cross_source, curriculum, exam_coverage,
               extracurricular, file_integrity, frontend_dupe, grammar_4q,
               graph, publisher, textbook)

# Order = report order; severity sorting happens later
AUDIT_FNS = [
    file_integrity.audit_file_sha,
    curriculum.audit_curriculum_vocab,
    curriculum.audit_grammar_hierarchy,
    publisher.audit_publisher_coverage,
    cross_source.audit_cross_source_vocab,
    textbook.audit_textbook_pages,
    textbook.audit_textbook_units,
    textbook.audit_vocab_curriculum_alignment,
    extracurricular.audit_extracurricular_in_exam,
    exam_coverage.audit_vocab_4q_classification,
    grammar_4q.audit_grammar_exam_coverage,
    graph.audit_node_orphans,
    graph.audit_edge_validity,
    graph.audit_relation_dictionary,
    graph.audit_grammar_dag,
    codequality.audit_code_complexity,
    codequality.audit_code_size,
    frontend_dupe.audit_frontend_inline_blocks,
    frontend_dupe.audit_frontend_duplicate_fetch,
]


def run_all(con: duckdb.DuckDBPyConnection) -> dict:
    """Run all audits, persist findings, return {kind: {OK,WARN,FAIL}}."""
    con.execute("DELETE FROM audit_findings")
    findings: list[dict] = []
    for fn in AUDIT_FNS:
        try:
            findings.extend(fn(con))
        except Exception as e:
            findings.append({
                "audit_kind": fn.__module__.rsplit(".", 1)[-1] + "/" + fn.__name__,
                "severity": "FAIL",
                "target": "(audit fn exception)",
                "actual": str(e),
            })

    if findings:
        now = datetime.now(timezone.utc).isoformat()
        for i, f in enumerate(findings):
            f["finding_id"] = i + 1
        con.executemany(
            "INSERT INTO audit_findings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(f["finding_id"], f["audit_kind"], f["severity"], f.get("target"),
              f.get("expected"), f.get("actual"), f.get("delta"), f.get("note"), now)
             for f in findings],
        )

    summary: dict = {}
    for f in findings:
        sev_map = summary.setdefault(f["audit_kind"], {"OK": 0, "WARN": 0, "FAIL": 0})
        sev_map[f["severity"]] = sev_map.get(f["severity"], 0) + 1
    return summary
