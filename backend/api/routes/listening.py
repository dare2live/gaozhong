"""Phase 7.2 /api/listening/* — 听力题查询 + transcript.

endpoints:
  /api/listening/list     -> 听力题列表 (has_audio=true)
  /api/listening/detail   -> 单题详情 (含 transcript + speakers)
"""
from __future__ import annotations

import json

from backend.api.db import db_ro


def api_listening_list(qs: dict) -> dict:
    section = (qs.get("section", [None])[0] or "").strip()
    con = db_ro()
    try:
        sql = ("SELECT qb_id, question_type, difficulty, "
               "SUBSTR(stem, 1, 80) AS stem_preview, "
               "audio_id, audio_duration, origin_ref "
               "FROM question_bank WHERE has_audio = true")
        args: list = []
        if section:
            type_map = {"short": "听力短对话", "dialog": "听力长对话", "passage": "听力独白"}
            qt = type_map.get(section, section)
            sql += " AND question_type = ?"
            args.append(qt)
        sql += " ORDER BY qb_id"
        rows = con.execute(sql, args).fetchall()
        return {
            "questions": [
                {"qb_id": r[0], "question_type": r[1], "difficulty": r[2],
                 "stem_preview": r[3], "audio_id": r[4],
                 "audio_duration": r[5], "origin_ref": r[6]}
                for r in rows
            ],
            "count": len(rows),
        }
    finally:
        con.close()


def api_listening_detail(qs: dict) -> dict:
    raw = qs.get("id", [None])[0]
    if not raw:
        return {"error": "missing ?id"}
    try:
        qb_id = int(raw)
    except (TypeError, ValueError):
        return {"error": "invalid id"}
    con = db_ro()
    try:
        r = con.execute(
            "SELECT qb_id, question_type, stem, answer, difficulty, "
            "analysis, transcript, audio_id, audio_speakers, audio_duration, "
            "origin_ref "
            "FROM question_bank WHERE qb_id = ? AND has_audio = true",
            [qb_id],
        ).fetchone()
        if not r:
            return {"error": f"listening question {qb_id} not found"}
        speakers = []
        if r[8]:
            try:
                speakers = json.loads(r[8])
            except (json.JSONDecodeError, TypeError):
                pass
        return {
            "qb_id": r[0], "question_type": r[1], "stem": r[2],
            "answer": r[3], "difficulty": r[4], "analysis": r[5],
            "transcript": r[6], "audio_id": r[7],
            "speakers": speakers, "audio_duration": r[9],
            "origin_ref": r[10],
        }
    finally:
        con.close()


ROUTES = {
    "/api/listening/list":   api_listening_list,
    "/api/listening/detail": api_listening_detail,
}
