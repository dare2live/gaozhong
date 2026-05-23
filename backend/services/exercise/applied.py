"""应用文模板抽 (从教材 Writing section 标 is_applied 的 section_text 抽功能套句)."""
from __future__ import annotations

import re

import duckdb


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
    rows = con.execute("""
        SELECT s.version_key, s.volume_key, s.unit_number, s.seq, st.n_chars,
               SUBSTR(st.raw_text, 1, 400) AS preview
        FROM sections s INNER JOIN section_text st
          USING (version_key, volume_key, unit_number, seq)
        WHERE s.is_narrative = TRUE
        ORDER BY st.n_chars DESC
    """).fetchall()
    return {"count": len(rows),
            "passages": [{"source": f"unit:{r[0]}/{r[1]}/U{r[2]}/sec_{r[3]}",
                           "n_chars": r[4], "preview": r[5]} for r in rows]}
