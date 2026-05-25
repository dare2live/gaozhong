"""摸底测验 API (D 用户 2026-05-25).

GET  /api/placement/spec?grade=G1
GET  /api/placement/generate?grade=G1     → 一套 spec 的真题集
POST /api/placement/score?grade=G1        → body=JSON {answers: {qb_id: 答案}}
POST /api/placement/followup              → body=JSON {wrong_qids, all_qids, grade}
POST /api/placement/final_score           → body=JSON {first_result, followup_answers, followup_questions}
"""
from __future__ import annotations

import json

import duckdb

from backend.api.db import DB_PATH, db_ro
from backend.services.placement import generator, loader, scorer, followup


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


def api_placement_followup(qs: dict, body: bytes | None = None) -> dict:
    """POST: 根据一阶段错题抽 3-5 题追问 (Codex Q6)."""
    if not body:
        return {"error": "POST body required: {wrong_qids, all_qids, grade}"}
    try:
        data = json.loads(body)
    except Exception as e:
        return {"error": f"bad JSON: {e}"}
    wrong_qids = [int(x) for x in (data.get("wrong_qids") or [])]
    all_qids = [int(x) for x in (data.get("all_qids") or [])]
    if not wrong_qids:
        return {"questions": [], "n_questions": 0, "note": "no wrong answers, no followup needed"}
    n = min(max(int(data.get("n", 5)), 3), 5)
    con = db_ro()
    try:
        return followup.pick_followup_questions(con, wrong_qids, all_qids, n)
    finally:
        con.close()


def api_placement_final_score(qs: dict, body: bytes | None = None) -> dict:
    """POST: 综合两阶段评分 → 最终 verdict (Codex Q6)."""
    if not body:
        return {"error": "POST body required: {first_result, followup_answers, followup_questions}"}
    try:
        data = json.loads(body)
    except Exception as e:
        return {"error": f"bad JSON: {e}"}
    first_result = data.get("first_result") or {}
    followup_answers = {int(k): str(v) for k, v in (data.get("followup_answers") or {}).items()}
    followup_questions = data.get("followup_questions") or []
    return followup.compute_final_score(first_result, followup_answers, followup_questions)


ROUTES = {
    "/api/placement/spec":        api_placement_spec,
    "/api/placement/generate":    api_placement_generate,
    "/api/placement/score":       api_placement_score,
    "/api/placement/followup":    api_placement_followup,
    "/api/placement/final_score": api_placement_final_score,
}
