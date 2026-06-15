#!/usr/bin/env python3
"""M0 真值基座核验脚本：对齐 exam_questions 与公开真值源（2021-2025）."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]

import duckdb

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"
REPORT_DIR = ROOT / "data" / "reports"
STRUCTURE_PATH = Path("/Users/dp/Documents/M/gaokao/data/structured/english_xgkii_2021_2025.jsonl")
VERIFIED_JSONL = ROOT / "data" / "gaokao_verified_xgkii_2023_2024.jsonl"

TARGET_YEARS = [2021, 2022, 2023, 2024, 2025]
TARGET_MIN_COUNT = {2021: 55, 2022: 55}
QTYPE_MAP = {
    "reading_comprehension": "阅读理解",
    "grammar_fill": "语法填空",
    "cloze_fill_in_blanks": "完形填空",
    "seven_choose_five": "完形填空(七选五/语篇)",
    "error_correction": "短文改错",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_text(value: str) -> str:
    text = re.sub(r"\s+", " ", (value or "").strip().lower())
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return text.strip()


def _textify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    if isinstance(value, (list, tuple)):
        return " ".join(_textify(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def signature(year: int | None, qtype: str, text: str, answer: Any = "") -> str:
    norm = normalize_text(f"{qtype or ''}||{text or ''}||{_textify(answer)}")
    digest = hashlib.sha1((norm or str(year or "")).encode("utf-8")).hexdigest()
    return digest


def _token_set(text: Any) -> set[str]:
    if isinstance(text, list):
        text = " ".join(str(x) for x in text)
    if isinstance(text, (dict, tuple)):
        text = json.dumps(text, ensure_ascii=False)
    return {w for w in re.findall(r"[a-z0-9]+", normalize_text(str(text))) if len(w) > 2}


def _overlap_score(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def manifest_hash() -> tuple[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    parts: list[str] = []
    for label, path in {
        "db": DB_PATH,
        "structured": STRUCTURE_PATH,
        "verified_jsonl": VERIFIED_JSONL,
    }.items():
        if not path.exists():
            entries[label] = {"path": str(path), "exists": False}
            continue
        st = path.stat()
        sig = f"{path}|{st.st_size}|{int(st.st_mtime_ns)}"
        entries[label] = {
            "path": str(path),
            "exists": True,
            "size": st.st_size,
            "mtime_ns": int(st.st_mtime_ns),
            "signature": hashlib.sha1(sig.encode("utf-8")).hexdigest(),
        }
        parts.append(entries[label]["signature"])
    run_id = hashlib.sha1(("|".join(parts) + "|" + now_iso()).encode("utf-8")).hexdigest()[:16]
    return run_id, entries


def load_db_records(con) -> list[dict[str, Any]]:
    rows = con.execute(
        """
        SELECT question_id, year, question_type, raw_question, answer, analysis,
               source_file, source_repo, source_index, province, paper_type
        FROM exam_questions
        WHERE year BETWEEN 2021 AND 2025
          AND province LIKE '%辽宁%'
        ORDER BY year, question_id
        """
    ).fetchall()
    items = []
    for qid, year, qtype, raw, ans, anl, source_file, source_repo, source_index, prov, paper_type in rows:
        if year is None:
            continue
        qtype_norm = (qtype or "").strip()
        items.append({
            "item_id": qid,
            "year": int(year),
            "question_type": qtype_norm,
            "raw_question": raw or "",
            "answer": ans or "",
            "analysis": anl or "",
            "source_file": source_file,
            "source_repo": source_repo,
            "source_index": source_index,
            "province": prov,
            "paper_type": paper_type,
            "answer": ans or "",
            "signature": signature(year, qtype_norm, raw or "", ans or ""),
            "token_set": _token_set(f"{raw or ''} {_textify(ans)}"),
            "row_source": "exam_questions",
        })
    return items


def load_bank_ids(con) -> set[str]:
    rows = con.execute("SELECT origin_ref FROM question_bank WHERE origin='real' AND origin_ref IS NOT NULL").fetchall()
    return {r[0] for r in rows}


def _map_qtype(qtype: str) -> str:
    return QTYPE_MAP.get((qtype or "").strip(), qtype or "")


def _flatten_options(options: Any) -> str:
    if not isinstance(options, dict):
        return ""
    parts: list[str] = []
    for key in sorted(options.keys()):
        parts.append(f"{key}:{options[key]}")
    return " ".join(parts)


def load_structured_records() -> list[dict[str, Any]]:
    if not STRUCTURE_PATH.exists():
        return []
    items: list[dict[str, Any]] = []
    for idx, line in enumerate(STRUCTURE_PATH.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        year = payload.get("year")
        try:
            year = int(year)
        except Exception:
            continue
        if year not in TARGET_YEARS:
            continue
        qtype = _map_qtype(payload.get("question_type", ""))
        stem = (payload.get("stem") or "").strip()
        if not stem:
            continue
        options = _flatten_options(payload.get("options", {}))
        answer_text = _textify(payload.get("answer", ""))
        qtext = f"{stem}\n{options}" if options else stem
        item_id = payload.get("id") or f"structured-xgkii-{year}-{idx:03d}"
        items.append({
            "item_id": str(item_id),
            "year": year,
            "question_type": qtype,
            "raw_question": qtext,
            "answer": payload.get("answer", "") or "",
            "analysis": payload.get("analysis", "") or "",
            "source_file": payload.get("source_file", STRUCTURE_PATH.name),
            "source_repo": payload.get("source", "gaokao_structured_xgkii"),
            "source_index": payload.get("question_number"),
            "province": payload.get("province", "辽宁"),
            "paper_type": payload.get("paper_type", "新课标 II 卷"),
            "signature": signature(year, qtype, qtext, answer_text),
            "token_set": _token_set(f"{qtext} {answer_text}"),
            "row_source": "structured_xgkii_jsonl",
            "source_order": idx,
        })
    return items


def load_verified_jsonl() -> list[dict[str, Any]]:
    if not VERIFIED_JSONL.exists():
        return []
    items: list[dict[str, Any]] = []
    for idx, line in enumerate(VERIFIED_JSONL.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        year = payload.get("year")
        try:
            year = int(year)
        except Exception:
            continue
        if year not in TARGET_YEARS:
            continue
        qtype = payload.get("question_type", "")
        stem = (payload.get("question") or "").strip()
        if not stem:
            continue
        answer_text = _textify(payload.get("answer", ""))
        source = payload.get("source", "gaokao_verified")
        source_file = payload.get("source_file", "gaokao_verified_xgkii_2023_2024.jsonl")
        item_id = f"{source_file}:{source}:{year}:{idx}"
        items.append({
            "item_id": item_id,
            "year": year,
            "question_type": qtype,
            "raw_question": stem,
            "answer": payload.get("answer", "") or "",
            "analysis": payload.get("analysis", "") or "",
            "source_file": source_file,
            "source_repo": source,
            "source_index": payload.get("index"),
            "province": payload.get("province", "辽宁"),
            "paper_type": payload.get("paper_type", "新课标 II 卷"),
            "signature": signature(year, qtype, stem, answer_text),
            "token_set": _token_set(f"{stem} {answer_text}"),
            "row_source": "gaokao_verified_jsonl",
            "source_order": idx,
        })
    return items


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


def import_truth_rows(con, rows: list[dict[str, Any]]) -> list[str]:
    inserted_ids: list[str] = []
    existing = {r[0] for r in con.execute("SELECT question_id FROM exam_questions").fetchall()}
    to_insert = []
    for row in rows:
        qid = row.get("item_id") or ""
        if not qid:
            qid = f"{row.get('source_file')}/{row.get('year')}/{row.get('question_type')}/{row.get('source_index')}"
        if qid in existing:
            continue
        to_insert.append((
            qid,
            int(row["year"]),
            row.get("province") or "辽宁 (新课标 II 卷, 2021+)",
            row.get("paper_type") or "新课标 II 卷",
            row.get("question_type") or "阅读理解",
            row.get("raw_question") or "",
            row.get("answer") or "",
            row.get("analysis") or "",
            row.get("source_file") or STRUCTURE_PATH.name,
            row.get("source_index"),
            row.get("source_repo") or "gaokao_structured_xgkii",
        ))

    if to_insert:
        con.executemany(
            """
            INSERT INTO exam_questions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            to_insert
        )
        inserted_ids = [r[0] for r in to_insert]
    return inserted_ids


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
