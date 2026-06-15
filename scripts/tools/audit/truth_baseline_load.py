#!/usr/bin/env python3
"""M0 真值基座核验：数据装载簇 (DB / 结构化 JSONL / verified JSONL) + 缺口入库.

读真相源 (exam_questions DB + 两份 JSONL), 产出标准化 records;
import_truth_rows 把 truth_only 缺口补回 exam_questions.
仅依赖 truth_baseline_common, 不反向 import audit 主模块.
"""
from __future__ import annotations

import json
from typing import Any

from scripts.tools.audit.truth_baseline_common import (
    STRUCTURE_PATH,
    TARGET_YEARS,
    VERIFIED_JSONL,
    _flatten_options,
    _map_qtype,
    _textify,
    _token_set,
    signature,
)


def load_db_records(con) -> list[dict[str, Any]]:
    rows = con.execute(
        """
        SELECT question_id, year, question_type, raw_question, answer, analysis,
               source_file, source_repo, source_index, province, paper_type
        FROM exam_questions
        WHERE year BETWEEN 2021 AND 2025
          AND province LIKE '辽宁%'
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
            "signature": signature(year, qtype_norm, raw or "", ans or ""),
            "token_set": _token_set(f"{raw or ''} {_textify(ans)}"),
            "row_source": "exam_questions",
        })
    return items


def load_bank_ids(con) -> set[str]:
    rows = con.execute("SELECT origin_ref FROM question_bank WHERE origin='real' AND origin_ref IS NOT NULL").fetchall()
    return {r[0] for r in rows}


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
