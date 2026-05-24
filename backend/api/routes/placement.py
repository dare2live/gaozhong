"""GET /api/placement/{spec,generate,score} — 摸底测验 API (D 用户 2026-05-25).

GET  /api/placement/spec?grade=G1
GET  /api/placement/generate?grade=G1     → 一套 spec 的真题集
POST /api/placement/score?grade=G1        → body=JSON {answers: {qb_id: 答案}}
"""
from __future__ import annotations

import json

import duckdb

from backend.api.db import DB_PATH, db_ro
from backend.services.placement import generator, loader, scorer


def api_placement_spec(qs: dict) -> dict:
    grade = qs.get("grade", [None])[0]
    if not grade:
        return {"specs": loader.load_specs(), "note": "缺 ?grade= 返全部"}
    spec = loader.get_spec(grade)
    if not spec:
        return {"error": f"unknown grade {grade}"}
    return spec


def api_placement_generate(qs: dict) -> dict:
    grade = qs.get("grade", [None])[0]
    if not grade:
        return {"error": "missing ?grade=G1|G2|G3"}
    spec = loader.get_spec(grade)
    if not spec:
        return {"error": f"unknown grade {grade}"}
    student_id = qs.get("student_id", [None])[0]   # Codex Q5: per-student seed
    con = db_ro()
    try:
        return generator.generate_paper(con, spec, student_id)
    finally:
        con.close()


def api_placement_score(qs: dict, body: bytes | None = None) -> dict:
    grade = qs.get("grade", [None])[0]
    if not grade:
        return {"error": "missing ?grade=G1|G2|G3"}
    spec = loader.get_spec(grade)
    if not spec:
        return {"error": f"unknown grade {grade}"}
    if not body:
        return {"error": "POST body required: {answers: {qb_id: '...'}}"}
    try:
        data = json.loads(body)
    except Exception as e:
        return {"error": f"bad JSON: {e}"}
    raw_answers = data.get("answers") or {}
    answers = {int(k): str(v) for k, v in raw_answers.items()}
    student_id = qs.get("student_id", [None])[0]
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        paper = generator.generate_paper(con, spec, student_id)
        return scorer.score_paper(con, paper, answers, spec)
    finally:
        con.close()


ROUTES = {
    "/api/placement/spec":     api_placement_spec,
    "/api/placement/generate": api_placement_generate,
    "/api/placement/score":    api_placement_score,
}
