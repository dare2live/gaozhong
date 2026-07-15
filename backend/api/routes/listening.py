"""Phase 7.2 /api/listening/* — 听力题查询 + 第三方核验音频目录/播放.

endpoints:
  /api/listening/list     -> 听力题列表 (has_audio=true)
  /api/listening/detail   -> 单题详情 (含 transcript + speakers)
  /api/listening/catalog  -> years_with_audio 文件清单 (单一计算点 audio_catalog)
  /api/listening/file     -> 返回文件元数据; 二进制由 main.py 直出
"""
from __future__ import annotations

import json
from pathlib import Path

from backend.api.db import db_ro
from backend.services.extraction.example_text import clean_preview
from backend.services.listening.audio_catalog import catalog, resolve_audio_file

# 坑(2026-07-05 根因审计复核): 用户追问"深层根因是否真修完"后复扫发现的漏网实例 — 本文件读
# question_bank.stem 时仍是原始 SUBSTR(...,1,80) 无边界截断, 与已收口的 example_text.py 不一致
# (第 8 处独立截断)。补齐防数据到位后复现同一 bug 类。
_STEM_PREVIEW_LEN = 80
ROOT = Path(__file__).resolve().parents[3]


def api_listening_list(qs: dict) -> dict:
    section = (qs.get("section", [None])[0] or "").strip()
    con = db_ro()
    try:
        sql = ("SELECT qb_id, question_type, difficulty, "
               f"SUBSTR(stem, 1, {_STEM_PREVIEW_LEN + 100}) AS stem_preview, "
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
                 "stem_preview": clean_preview(r[3], _STEM_PREVIEW_LEN), "audio_id": r[4],
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


def api_listening_catalog(qs: dict) -> dict:
    """可教档音频清单 — 读 audio_config + 磁盘, 不重算指纹."""
    return catalog()


def api_listening_file_meta(qs: dict) -> dict:
    """JSON 元数据; 实际 mp3 字节流由 main._try_listening_audio 提供."""
    year_raw = (qs.get("year", [None])[0] or "").strip()
    file_id = (qs.get("id", [None])[0] or "").strip()
    if not year_raw or not file_id:
        return {"error": "missing ?year=&id="}
    try:
        year = int(year_raw)
    except ValueError:
        return {"error": "invalid year"}
    try:
        path = resolve_audio_file(year, file_id)
    except ValueError as e:
        return {"error": str(e)}
    if not path.is_file():
        return {"error": "not found", "year": year, "id": file_id}
    return {
        "year": year,
        "id": file_id if file_id.endswith(".mp3") else f"{file_id}.mp3",
        "path": str(path.relative_to(ROOT)),
        "bytes": path.stat().st_size,
        "content_type": "audio/mpeg",
        "stream_url": f"/api/listening/file?year={year}&id={file_id}",
        "binary": True,
        "note": "GET same URL returns audio/mpeg body (handled in main.py)",
    }


ROUTES = {
    "/api/listening/list": api_listening_list,
    "/api/listening/detail": api_listening_detail,
    "/api/listening/catalog": api_listening_catalog,
    "/api/listening/file": api_listening_file_meta,
}
