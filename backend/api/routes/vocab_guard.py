"""超纲词管理 API.

GET  /api/vocab/check?layer=G1&text=...   检查文本超纲词
GET  /api/vocab/word_info?word=achieve     查询单词年级归属
POST /api/vocab/batch_check                批量检查 {words: [...], layer: "G1"}
"""
from __future__ import annotations

import json

from backend.api.db import db_ro
from backend.services import vocab_guard


def api_vocab_check(qs: dict) -> dict:
    text = qs.get("text", [""])[0]
    layer = qs.get("layer", ["G_FINAL"])[0]
    if not text:
        return {"error": "missing ?text= parameter"}
    con = db_ro()
    try:
        return vocab_guard.check_text(con, text, layer)
    finally:
        con.close()


def api_vocab_word_info(qs: dict) -> dict:
    word = qs.get("word", [""])[0]
    if not word:
        return {"error": "missing ?word= parameter"}
    con = db_ro()
    try:
        return vocab_guard.word_info(con, word)
    finally:
        con.close()


def api_vocab_batch_check(qs: dict, body: bytes | None = None) -> dict:
    if not body:
        return {"error": "POST body required: {words: [...], layer: 'G1'}"}
    data = json.loads(body)
    words = data.get("words", [])
    layer = data.get("layer", "G_FINAL")
    con = db_ro()
    try:
        return {"results": vocab_guard.batch_word_info(con, words), "layer": layer}
    finally:
        con.close()


ROUTES = {
    "/api/vocab/check":     api_vocab_check,
    "/api/vocab/word_info": api_vocab_word_info,
}
