#!/usr/bin/env python3
"""M0 真值基座核验：数据装载簇 (DB / 结构化 JSONL / verified JSONL) + 缺口入库.
⚠️ DEPRECATED (2026-06-20): 一次性软匹配脚本, 已被模块化 backend/services/truth_baseline/ + CLI scripts/tools/truth_check 取代(验内容匹配第一手源+self-test+接D0门). 保留仅因 truth_baseline_common 含 moth 用的路径常量. 勿在新代码引用.

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
from backend.services.trend import scope   # G3: province标签单点


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


def _parse_jsonl_payload(line: str) -> dict[str, Any] | None:
    """空行/JSON 解析失败返回 None, 母函数据此 skip."""
    if not line.strip():
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def _parse_target_year(payload: dict[str, Any]) -> int | None:
    """year 字段缺失/非法/不在 TARGET_YEARS 内返回 None."""
    year = payload.get("year")
    try:
        year = int(year)
    except Exception:
        return None
    if year not in TARGET_YEARS:
        return None
    return year


def _build_structured_item(payload: dict[str, Any], year: int, idx: int) -> dict[str, Any] | None:
    qtype = _map_qtype(payload.get("question_type", ""))
    stem = (payload.get("stem") or "").strip()
    if not stem:
        return None
    options = _flatten_options(payload.get("options", {}))
    answer_text = _textify(payload.get("answer", ""))
    qtext = f"{stem}\n{options}" if options else stem
    item_id = payload.get("id") or f"structured-xgkii-{year}-{idx:03d}"
    return {
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
        "paper_type": payload.get("paper_type", scope.PAPER_XGKII),
        "signature": signature(year, qtype, qtext, answer_text),
        "token_set": _token_set(f"{qtext} {answer_text}"),
        "row_source": "structured_xgkii_jsonl",
        "source_order": idx,
    }


def load_structured_records() -> list[dict[str, Any]]:
    if not STRUCTURE_PATH.exists():
        return []
    items: list[dict[str, Any]] = []
    for idx, line in enumerate(STRUCTURE_PATH.read_text(encoding="utf-8").splitlines()):
        payload = _parse_jsonl_payload(line)
        if payload is None:
            continue
        year = _parse_target_year(payload)
        if year is None:
            continue
        item = _build_structured_item(payload, year, idx)
        if item is None:
            continue
        items.append(item)
    return items


def _build_verified_item(payload: dict[str, Any], year: int, idx: int) -> dict[str, Any] | None:
    qtype = payload.get("question_type", "")
    stem = (payload.get("question") or "").strip()
    if not stem:
        return None
    answer_text = _textify(payload.get("answer", ""))
    source = payload.get("source", "gaokao_verified")
    source_file = payload.get("source_file", "gaokao_verified_xgkii_2023_2024.jsonl")
    item_id = f"{source_file}:{source}:{year}:{idx}"
    return {
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
        "paper_type": payload.get("paper_type", scope.PAPER_XGKII),
        "signature": signature(year, qtype, stem, answer_text),
        "token_set": _token_set(f"{stem} {answer_text}"),
        "row_source": "gaokao_verified_jsonl",
        "source_order": idx,
    }


def load_verified_jsonl() -> list[dict[str, Any]]:
    if not VERIFIED_JSONL.exists():
        return []
    items: list[dict[str, Any]] = []
    for idx, line in enumerate(VERIFIED_JSONL.read_text(encoding="utf-8").splitlines()):
        payload = _parse_jsonl_payload(line)
        if payload is None:
            continue
        year = _parse_target_year(payload)
        if year is None:
            continue
        item = _build_verified_item(payload, year, idx)
        if item is None:
            continue
        items.append(item)
    return items


def _resolve_row_qid(row: dict[str, Any]) -> str:
    qid = row.get("item_id") or ""
    if not qid:
        qid = f"{row.get('source_file')}/{row.get('year')}/{row.get('question_type')}/{row.get('source_index')}"
    return qid


def _row_to_insert_tuple(qid: str, row: dict[str, Any]) -> tuple:
    return (
        qid,
        int(row["year"]),
        row.get("province") or scope.LIAONING_XGKII_2021,   # G3: 收口 scope 单点
        row.get("paper_type") or scope.PAPER_XGKII,
        row.get("question_type") or "阅读理解",
        row.get("raw_question") or "",
        row.get("answer") or "",
        row.get("analysis") or "",
        row.get("source_file") or STRUCTURE_PATH.name,
        row.get("source_index"),
        row.get("source_repo") or "gaokao_structured_xgkii",
    )


def _insert_exam_questions_all(con, to_insert: list[tuple]) -> None:
    con.executemany(
        """
        INSERT INTO exam_questions_all (question_id, year, province, paper_type, question_type,
          raw_question, answer, analysis, source_file, source_index, source_repo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        to_insert
    )


def import_truth_rows(con, rows: list[dict[str, Any]]) -> list[str]:
    inserted_ids: list[str] = []
    existing = {r[0] for r in con.execute("SELECT question_id FROM exam_questions").fetchall()}
    to_insert = []
    for row in rows:
        qid = _resolve_row_qid(row)
        if qid in existing:
            continue
        to_insert.append(_row_to_insert_tuple(qid, row))

    if to_insert:
        _insert_exam_questions_all(con, to_insert)
        inserted_ids = [r[0] for r in to_insert]
    return inserted_ids
