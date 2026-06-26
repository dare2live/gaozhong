"""GET /api/cefr_vocab — 课标词汇表查询."""
from __future__ import annotations

from backend.api.db import db_ro, rows_to_dicts
from backend.services import word_sense


def api_cefr_vocab(qs: dict) -> list[dict]:
    level = qs.get("level", [None])[0]
    prefix = qs.get("prefix", [""])[0].lower()
    try:
        limit = min(int(qs.get("limit", ["200"])[0]), 1000)
    except ValueError:
        limit = 200
    where, args = [], []
    if level:
        where.append("cefr_level = ?"); args.append(level)
    if prefix:
        where.append("word LIKE ?"); args.append(prefix + "%")
    sql = "SELECT word, cefr_level, raw_suffix FROM cefr_vocab"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY word LIMIT ?"
    args.append(limit)
    con = db_ro()
    try:
        return rows_to_dicts(con.execute(sql, args))
    finally:
        con.close()


def api_exam_dictionary(qs: dict) -> dict:
    """考试词典查询 (Canonical 词本体; ?prefix=/stage=/source=exam 过滤; 含释义+三源provenance)."""
    prefix = qs.get("prefix", [""])[0].lower()
    stage = qs.get("stage", [None])[0]
    where, args = [], []
    if prefix:
        where.append("word LIKE ?"); args.append(prefix + "%")
    if stage:
        where.append("stage = ?"); args.append(stage)
    if qs.get("source", [None])[0] == "exam":
        where.append("in_exam")
    try:
        limit = min(int(qs.get("limit", ["300"])[0]), 2000)
    except ValueError:
        limit = 300
    sql = ("SELECT word, curriculum_level, in_textbook, in_exam, gaokao_hit_ln, stage, gloss, "
           "gloss_source, source_flags FROM exam_vocabulary")
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY gaokao_hit_ln DESC, word LIMIT ?"
    args.append(limit)
    con = db_ro()
    try:
        total = con.execute("SELECT COUNT(*) FROM exam_vocabulary").fetchone()[0]
        return {"total": total, "rows": rows_to_dicts(con.execute(sql, args))}
    finally:
        con.close()


def api_word_detail(qs: dict) -> dict:
    """GET /api/word_detail?word=X — 跨阶段多义详情 (薄壳; 计算在 services/word_sense 单算点).

    provenance=dual_model_adversarial → 前端必标'方向性参考'非真值 (守 J4)。
    """
    word = (qs.get("word", [""])[0] or "").strip()
    if not word:
        return {"error": "missing ?word"}
    con = db_ro()
    try:
        return word_sense.word_detail(con, word)
    finally:
        con.close()


ROUTES = {"/api/cefr_vocab": api_cefr_vocab, "/api/exam_dictionary": api_exam_dictionary,
          "/api/word_detail": api_word_detail}
