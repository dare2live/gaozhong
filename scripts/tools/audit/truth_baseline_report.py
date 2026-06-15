#!/usr/bin/env python3
"""M0 真值基座核验：发现归类 + 状态判定 + JSON/Markdown 报告输出.

从对账结果 (summary + audit_rows) 派生 findings / 总状态, 并落 JSON / MD 报告.
仅依赖 truth_baseline_common, 不反向 import audit 主模块.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.tools.audit.truth_baseline_common import TARGET_YEARS


def write_report(report: dict[str, Any], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def build_findings(summary: dict[int, dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    db_target_gaps = {
        str(year): {
            "db_count": values["db_count"],
            "target_min": values["target_min"],
            "gap": values["target_min"] - values["db_count"],
        }
        for year, values in summary.items()
        if values["target_min"] and values["db_count"] < values["target_min"]
    }
    truth_target_gaps = {
        str(year): {
            "truth_count": values["truth_count"],
            "target_min": values["target_min"],
            "gap": values["target_min"] - values["truth_count"],
        }
        for year, values in summary.items()
        if values["target_min"] and values["truth_count"] < values["target_min"]
    }
    truth_only = [row for row in rows if row["status"] == "in_truth_source_only"]
    pollution = [
        row for row in rows
        if row["status"] == "in_exam_questions_only" and row["source"] != "local_pdf"
    ]
    bank_missing = [
        row for row in rows
        if row["status"] in {"mapped", "in_exam_questions_only"}
        and not row.get("question_bank_mapped")
    ]
    return {
        "db_target_gaps": db_target_gaps,
        "truth_target_gaps": truth_target_gaps,
        "truth_only_count": len(truth_only),
        "pollution_candidate_count": len(pollution),
        "question_bank_missing_count": len(bank_missing),
        "truth_only_sample": truth_only[:20],
        "pollution_candidate_sample": pollution[:20],
        "question_bank_missing_sample": bank_missing[:20],
    }


def overall_status(findings: dict[str, Any]) -> str:
    if findings["db_target_gaps"]:
        return "FAIL"
    if findings["truth_target_gaps"]:
        return "FAIL"
    if findings["truth_only_count"]:
        return "FAIL"
    if findings["pollution_candidate_count"]:
        return "FAIL"
    if findings["question_bank_missing_count"]:
        return "FAIL"
    return "PASS"


def write_markdown_report(report: dict[str, Any], out_path: Path) -> Path:
    lines = [
        "# Truth Baseline Audit 2021-2025",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Run ID: `{report['run_id']}`",
        f"- Status: `{report['status']}`",
        f"- DB: `{report['db_path']}`",
        f"- Structured truth source: `{report['structured_path']}`",
        f"- Verified JSONL: `{report['verified_jsonl']}`",
        "",
        "## Summary by Year",
        "",
        "| Year | DB rows | Truth rows | Matched | DB only | Truth only | QB mapped | Target min | Gap |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for year in TARGET_YEARS:
        values = report["summary_by_year"][str(year)] if str(year) in report["summary_by_year"] else report["summary_by_year"][year]
        target = values["target_min"] if values["target_min"] is not None else ""
        gap = values["gap_to_target"] if values["gap_to_target"] is not None else ""
        lines.append(
            f"| {year} | {values['db_count']} | {values['truth_count']} | {values['matched']} | "
            f"{values['db_only']} | {values['truth_only']} | {values['db_have_question_bank']} | {target} | {gap} |"
        )
    findings = report["findings"]
    lines.extend([
        "",
        "## Findings",
        "",
        f"- DB target gaps: `{len(findings['db_target_gaps'])}`",
        f"- Truth-source target gaps: `{len(findings['truth_target_gaps'])}`",
        f"- Truth-only rows: `{findings['truth_only_count']}`",
        f"- Pollution candidates: `{findings['pollution_candidate_count']}`",
        f"- Missing question_bank real mappings: `{findings['question_bank_missing_count']}`",
        "",
        "## Interpretation",
        "",
    ])
    if report["status"] == "PASS":
        lines.append("- PASS: `exam_questions`, truth source, and `question_bank` mapping are aligned for the configured target scope.")
    else:
        lines.extend([
            "- FAIL: M0 truth baseline is not closed for the configured target scope.",
            "- Do not treat Phase A / M0 as complete until DB target gaps, truth-only rows, pollution candidates, and question_bank mapping gaps are resolved or explicitly re-scoped.",
        ])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
