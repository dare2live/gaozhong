"""应用文模板抽 (从教材 Writing section 标 is_applied 的 section_text 抽功能套句)."""
from __future__ import annotations

import re

import duckdb

from backend.services.extraction.example_text import clean_preview
from backend.services.thresholds import get_threshold   # 预览截断长度单点 (extraction 块, 接孤儿key)


def _extract_functional_chunks(text: str) -> list[dict]:
    """Find applied-letter chunks (greeting / body / closing)."""
    chunks = []
    # greeting
    for m in re.finditer(r"\b(Dear [A-Z][a-zA-Z]+|Hi [A-Z][a-zA-Z]+|Hello)\b", text):
        chunks.append({"chunk_type": "greeting", "text": m.group()})
    # opening
    for m in re.finditer(r"\bI am writing to .{5,60}", text):
        chunks.append({"chunk_type": "opening", "text": m.group()})
    for m in re.finditer(r"\bI'd like to .{5,40}", text):
        chunks.append({"chunk_type": "opening", "text": m.group()})
    # closing
    for m in re.finditer(r"\b(Looking forward to .{5,40}|Yours (sincerely|faithfully|truly)|Best regards)\b", text):
        chunks.append({"chunk_type": "closing", "text": m.group()})
    return chunks


def list_applied_templates(con: duckdb.DuckDBPyConnection) -> dict:
    rows = con.execute("""
        SELECT s.version_key, s.volume_key, s.unit_number, s.seq, st.raw_text
        FROM sections s INNER JOIN section_text st
          USING (version_key, volume_key, unit_number, seq)
        WHERE s.is_applied = TRUE
    """).fetchall()
    out = []
    by_type: dict[str, int] = {}
    for ver, vol, un, seq, text in rows:
        chunks = _extract_functional_chunks(text or "")
        for c in chunks:
            out.append({"source": f"unit:{ver}/{vol}/U{un}/sec_{seq}", **c})
            by_type[c["chunk_type"]] = by_type.get(c["chunk_type"], 0) + 1
    return {"sections": len(rows), "chunks": len(out),
            "by_type": by_type, "samples": out[:50]}


def list_narrative_passages(con: duckdb.DuckDBPyConnection) -> dict:
    # 预览截断长度读 extraction.applied_preview_chars (注: 该key名含applied, 实际唯一消费点是此 narrative 预览; 值不变)
    _prev = get_threshold("extraction.applied_preview_chars", 400)
    # 坑(2026-07-05 根因审计, LOW): 原定长 SUBSTR 无边界意识; SQL 端多留 200 字缓冲, clean_preview
    # 裁到 _prev 内最近句末标点(此端点当前无存活前端调用方, 仍按 Rule5 补齐一致性, 不留技术债).
    rows = con.execute(f"""
        SELECT s.version_key, s.volume_key, s.unit_number, s.seq, st.n_chars,
               SUBSTR(st.raw_text, 1, {_prev + 200}) AS preview
        FROM sections s INNER JOIN section_text st
          USING (version_key, volume_key, unit_number, seq)
        WHERE s.is_narrative = TRUE
        ORDER BY st.n_chars DESC
    """).fetchall()
    return {"count": len(rows),
            "passages": [{"source": f"unit:{r[0]}/{r[1]}/U{r[2]}/sec_{r[3]}",
                           "n_chars": r[4], "preview": clean_preview(r[5], _prev)} for r in rows]}
