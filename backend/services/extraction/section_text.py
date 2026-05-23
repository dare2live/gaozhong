"""抽 section page 范围内的 raw_text 入 section_text 表 (K).

为后续:
  - phrase 抽 (E): grep section_text 找短语 / 句型
  - LLM 抽 (S4): 送 section_text 给 LLM 抽 narrative / 功能表达
"""
from __future__ import annotations

from pathlib import Path

import duckdb
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent.parent.parent
TEXTBOOK_DIR = ROOT / "data" / "textbooks"


def _page_text(reader: PdfReader, pi: int) -> str:
    try:
        return reader.pages[pi].extract_text() or ""
    except Exception:
        return ""


def extract_section_text(con: duckdb.DuckDBPyConnection) -> dict:
    rows = con.execute("""
        SELECT version_key, volume_key, unit_number, seq, page_start, page_end
        FROM sections WHERE page_start IS NOT NULL AND page_end IS NOT NULL
        ORDER BY version_key, volume_key, unit_number, seq
    """).fetchall()
    pdf_cache: dict[str, PdfReader] = {}
    inserted = 0
    con.execute("DELETE FROM section_text")
    for ver, vol, un, seq, ps, pe in rows:
        key = f"{ver}/{vol}"
        if key not in pdf_cache:
            p = TEXTBOOK_DIR / ver / f"{vol}.pdf"
            if not p.exists():
                continue
            try:
                pdf_cache[key] = PdfReader(p)
            except Exception:
                continue
        reader = pdf_cache[key]
        chunks: list[str] = []
        for pi in range(max(0, ps - 1), min(pe, len(reader.pages))):
            chunks.append(_page_text(reader, pi))
        text = "\n".join(chunks).strip()
        if not text:
            continue
        con.execute(
            "INSERT INTO section_text VALUES (?, ?, ?, ?, ?, ?)",
            [ver, vol, un, seq, text[:20000], len(text)],
        )
        inserted += 1
    return {"sections_scanned": len(rows), "rows_inserted": inserted}
