#!/usr/bin/env python3
"""M0 真值基座核验脚本：对齐 exam_questions 与公开真值源（2021-2025）.
⚠️ DEPRECATED (2026-06-20): 一次性软匹配脚本, 已被模块化 backend/services/truth_baseline/ + CLI scripts/tools/truth_check 取代(验内容匹配第一手源+self-test+接D0门). 保留仅因 truth_baseline_common 含 moth 用的路径常量. 勿在新代码引用.

公开 API + CLI 入口. 装载簇 / 报告簇 / 共享底层工具已抽到 sibling 模块
(truth_baseline_load / truth_baseline_report / truth_baseline_common),
此处 re-export 以保持对外符号稳定 (e.g. milestone_b_rebuild 引用路径不变).
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import duckdb

# 直接以文件路径运行时 (python3 scripts/tools/audit/truth_baseline_audit.py),
# 项目根不在 sys.path, 下面的 scripts.* 绝对导入会失败; 先 bootstrap.
_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.tools.audit.truth_baseline_common import (  # noqa: E402,F401  re-export
    DB_PATH,
    QTYPE_MAP,
    REPORT_DIR,
    ROOT,
    STRUCTURE_PATH,
    TARGET_MIN_COUNT,
    TARGET_YEARS,
    VERIFIED_JSONL,
    _flatten_options,
    _map_qtype,
    _overlap_score,
    _textify,
    _token_set,
    manifest_hash,
    normalize_text,
    now_iso,
    signature,
)
from scripts.tools.audit.truth_baseline_load import (  # noqa: E402,F401  re-export
    import_truth_rows,
    load_bank_ids,
    load_db_records,
    load_structured_records,
    load_verified_jsonl,
)
from scripts.tools.audit.truth_baseline_report import (  # noqa: E402,F401  re-export
    build_findings,
    overall_status,
    write_markdown_report,
    write_report,
)


def build_reconciliation(db_rows: list[dict[str, Any]], truth_rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_qtype = defaultdict(list)
    for row in db_rows:
        by_qtype[(row["year"], row["question_type"])].append(row)

    used_db_ids: set[str] = set()
    matched_rows: list[dict[str, Any]] = []
    db_only_rows: list[dict[str, Any]] = []
    truth_only_rows: list[dict[str, Any]] = []

    for truth in truth_rows:
        bucket = by_qtype.get((truth["year"], truth["question_type"]), [])
        best = None
        best_score = 0.0
        for db in bucket:
            if db["item_id"] in used_db_ids:
                continue
            score = _overlap_score(db["token_set"], truth["token_set"])
            if score > best_score:
                best_score = score
                best = db
            if score >= 0.35:
                break
        if best and best_score >= 0.2:
            used_db_ids.add(best["item_id"])
            matched_rows.append({"status": "matched", "year": truth["year"], "db": best, "truth": truth, "match_score": round(best_score, 3)})
        else:
            truth_only_rows.append(truth)

    for row in db_rows:
        if row["item_id"] not in used_db_ids:
            db_only_rows.append(row)

    return {"matched": matched_rows, "db_only": db_only_rows, "truth_only": truth_only_rows}


def make_year_summary(recon: dict[str, Any], bank_ids: set[str]) -> dict[int, dict[str, Any]]:
    summary: dict[int, dict[str, Any]] = {y: {"db_count": 0, "truth_count": 0, "matched": 0, "db_only": 0, "truth_only": 0} for y in TARGET_YEARS}
    for item in recon["matched"]:
        y = item["year"]
        summary[y]["db_count"] += 1
        summary[y]["truth_count"] += 1
        summary[y]["matched"] += 1
    for item in recon["db_only"]:
        y = item["year"]
        summary[y]["db_count"] += 1
        summary[y]["db_only"] += 1
    for item in recon["truth_only"]:
        y = item["year"]
        summary[y]["truth_count"] += 1
        summary[y]["truth_only"] += 1
    for y, s in summary.items():
        s["target_min"] = TARGET_MIN_COUNT.get(y)
        s["gap_to_target"] = (TARGET_MIN_COUNT[y] - s["truth_count"]) if y in TARGET_MIN_COUNT else None
        s["db_have_question_bank"] = 0
        for row in recon["matched"]:
            if row["year"] != y:
                continue
            if row["db"].get("item_id") in bank_ids:
                s["db_have_question_bank"] += 1
        for row in recon["db_only"]:
            if row["year"] != y:
                continue
            if row.get("item_id") in bank_ids:
                s["db_have_question_bank"] += 1
        s["db_question_bank_total"] = 0
        for row in recon["matched"]:
            if row["year"] == y:
                s["db_question_bank_total"] += 1
        for row in recon["db_only"]:
            if row["year"] == y:
                s["db_question_bank_total"] += 1
        s["coverage"] = round(100 * s["matched"] / max(s["truth_count"], 1), 2)
    return summary


def build_audit_rows(recon: dict[str, Any], bank_ids: set[str]) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for group in ("matched", "db_only", "truth_only"):
        for item in recon[group]:
            if group == "matched":
                db_item = item["db"]
                truth_item = item["truth"]
                lines.append({
                    "year": db_item["year"],
                    "status": "mapped",
                    "source": f"{db_item['source_repo']} ↔ {truth_item['source_repo']}",
                    "question_id": db_item["item_id"],
                    "source_file": db_item["source_file"],
                    "truth_source_file": truth_item["source_file"],
                    "truth_row": truth_item["item_id"],
                    "question_type": db_item["question_type"],
                    "question_bank_mapped": db_item["item_id"] in bank_ids,
                    "signature": db_item["signature"],
                    "match_score": item.get("match_score", 1.0),
                })
            elif group == "db_only":
                db_item = item
                lines.append({
                    "year": db_item["year"],
                    "status": "in_exam_questions_only",
                    "source": db_item["source_repo"],
                    "question_id": db_item["item_id"],
                    "source_file": db_item["source_file"],
                    "truth_source_file": None,
                    "truth_row": None,
                    "question_type": db_item["question_type"],
                    "question_bank_mapped": db_item["item_id"] in bank_ids,
                    "signature": db_item["signature"],
                    "note": "缺少可复核结构化样本",
                })
            else:
                truth_item = item
                lines.append({
                    "year": truth_item["year"],
                    "status": "in_truth_source_only",
                    "source": truth_item["source_repo"],
                    "question_id": None,
                    "source_file": truth_item["source_file"],
                    "truth_source_file": truth_item["source_file"],
                    "truth_row": truth_item["item_id"],
                    "question_type": truth_item["question_type"],
                    "question_bank_mapped": False,
                    "signature": truth_item["signature"],
                    "note": "DB 中缺失，当前可判定为未入库缺口",
                })
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--import-missing", action="store_true", help="是否把结构化真值缺口补入 exam_questions")
    parser.add_argument("--report", type=Path, default=REPORT_DIR / "truth_baseline_2021_2025.json")
    parser.add_argument("--markdown", type=Path, default=REPORT_DIR / "truth_baseline_2021_2025.md")
    parser.add_argument("--strict", action="store_true", help="存在真值缺口/污染候选/question_bank 映射缺口时返回非 0")
    args = parser.parse_args()

    db_records = []
    truth_records: list[dict[str, Any]] = []
    con = duckdb.connect(str(DB_PATH), read_only=not args.import_missing)
    try:
        db_records = load_db_records(con)
        bank_ids = load_bank_ids(con)
        truth_records.extend(load_structured_records())
        truth_records.extend(load_verified_jsonl())
        if args.import_missing:
            con.close()
            con = duckdb.connect(str(DB_PATH))
    finally:
        pass

    recon = build_reconciliation(db_records, truth_records)
    summary = make_year_summary(recon, bank_ids)
    rows = build_audit_rows(recon, bank_ids)

    inserted_question_ids: list[str] = []
    if args.import_missing:
        missing_truth_rows = recon["truth_only"]
        if missing_truth_rows:
            inserted_question_ids = import_truth_rows(con, missing_truth_rows)

    # 复核后重新读取一遍，用于报告的最终计数
    db_records_after = db_records if not args.import_missing else load_db_records(con)
    bank_ids_after = bank_ids if not args.import_missing else load_bank_ids(con)
    recon_after = build_reconciliation(db_records_after, truth_records)
    summary_after = make_year_summary(recon_after, bank_ids_after)
    rows_after = build_audit_rows(recon_after, bank_ids_after)

    data_gap = {y: s for y, s in summary_after.items() if (s["target_min"] and s["truth_count"] < s["target_min"])}
    open_gap = [item for item in rows_after if item["status"] == "in_truth_source_only"]

    pollution = [
        item for item in rows_after
        if item["status"] == "in_exam_questions_only" and item["source"] != "local_pdf"
    ]
    findings = build_findings(summary_after, rows_after)
    status = overall_status(findings)
    run_id, manifest = manifest_hash()
    cross_base = args.report.parent / "cross_verify_2021_2025.json"
    cross_gap = args.report.parent / "cross_verify_gaps_2021_2025.json"

    report = {
        "generated_at": now_iso(),
        "run_id": run_id,
        "status": status,
        "manifest": manifest,
        "years": TARGET_YEARS,
        "db_path": str(DB_PATH),
        "structured_path": str(STRUCTURE_PATH),
        "verified_jsonl": str(VERIFIED_JSONL),
        "totals": {
            "db_rows": len(db_records_after),
            "truth_rows": len(truth_records),
            "matched_rows": len([r for r in rows_after if r["status"] == "mapped"]),
            "truth_only": len(open_gap),
            "db_only": len([r for r in rows_after if r["status"] == "in_exam_questions_only"]),
            "bank_mapped_count": len([r for r in rows_after if r.get("question_bank_mapped")]),
        },
        "summary_by_year": summary_after,
        "gaps_to_target": data_gap,
        "pollution_candidates": pollution,
        "findings": findings,
        "import": {"enabled": args.import_missing, "inserted_rows": len(inserted_question_ids), "inserted_question_ids": inserted_question_ids},
        "audit_rows": rows_after,
    }

    out = write_report(report, args.report)
    md_out = write_markdown_report(report, args.markdown)
    write_report({
        "run_id": run_id,
        "manifest": manifest,
        "year_range": "2021-2025",
        "source": "truth_baseline_audit",
        "total": len(rows_after),
        "records": [r for r in rows_after if r["status"] in {"mapped", "in_exam_questions_only", "in_truth_source_only"}],
    }, cross_base)
    write_report({
        "run_id": run_id,
        "manifest": manifest,
        "year_range": "2021-2025",
        "source": "truth_baseline_audit",
        "gaps": [r for r in rows_after if r["status"] == "in_truth_source_only"],
        "summary_by_year": {
            y: s for y, s in summary_after.items()
            if y in (2021, 2022) or s["gap_to_target"]
        },
    }, cross_gap)
    print(f"Truth baseline report: {out}")
    print(f"Truth baseline markdown: {md_out}")
    print(f"  status={status}")
    print(f"  db_rows={report['totals']['db_rows']} truth_rows={report['totals']['truth_rows']}")
    print(f"  mapped={report['totals']['matched_rows']} truth_only={report['totals']['truth_only']} db_only={report['totals']['db_only']}")
    print(f"  pollution_candidates={findings['pollution_candidate_count']} question_bank_missing={findings['question_bank_missing_count']}")
    if args.import_missing:
        print(f"  inserted={len(inserted_question_ids)}")
    if data_gap:
        for y, s in sorted(data_gap.items()):
            print(f"  Year {y}: truth_count={s['truth_count']} target={s['target_min']} gap={s['gap_to_target']}")
    if args.strict and status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
