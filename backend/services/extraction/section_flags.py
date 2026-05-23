"""标 section 的 is_narrative / is_applied / is_listening (I).

依据:
  - is_listening = sections.kind == 'Listening'
  - is_applied   = sections.kind == 'Writing' AND section_text 含应用文模板词
                   (eg "Dear", "Yours sincerely", "Subject:", "RSVP")
  - is_narrative = sections.kind == 'Reading' AND section_text 叙事性高
                   (eg 含 "once upon a time", "one day", "suddenly", 大量过去时)
"""
from __future__ import annotations

import re

import duckdb

APPLIED_MARKERS = [
    "Dear ", "Sincerely", "Yours faithfully", "Yours truly",
    "Subject:", "RSVP", "Best regards", "Kind regards",
    "Looking forward to hearing from you",
]
NARRATIVE_MARKERS = [
    "Once upon a time", "One day", "suddenly", "moments later",
    "to my surprise", "I remember", "It happened",
]


def _score_narrative(text: str) -> int:
    t = text.lower()
    hits = sum(1 for m in NARRATIVE_MARKERS if m.lower() in t)
    # heuristic: many past tense verbs (-ed)
    ed_count = len(re.findall(r"\b\w+ed\b", t)) // 50  # / 50 normalize
    return hits + ed_count


def flag_sections(con: duckdb.DuckDBPyConnection) -> dict:
    # listening
    n_lst = con.execute("""
        UPDATE sections SET is_listening = (kind = 'Listening')
    """).fetchone()
    # need text-based for applied / narrative
    rows = con.execute("""
        SELECT s.version_key, s.volume_key, s.unit_number, s.seq, s.kind, st.raw_text
        FROM sections s
        LEFT JOIN section_text st USING (version_key, volume_key, unit_number, seq)
    """).fetchall()
    n_applied = n_narrative = 0
    for ver, vol, un, seq, kind, text in rows:
        text = text or ""
        is_app = False; is_nar = False
        if kind == "Writing" and any(m in text for m in APPLIED_MARKERS):
            is_app = True; n_applied += 1
        if kind == "Reading" and _score_narrative(text) >= 2:
            is_nar = True; n_narrative += 1
        if is_app or is_nar:
            con.execute("""
                UPDATE sections SET is_applied=?, is_narrative=?
                WHERE version_key=? AND volume_key=? AND unit_number=? AND seq=?
            """, [is_app, is_nar, ver, vol, un, seq])
    return {"sections": len(rows), "is_applied": n_applied, "is_narrative": n_narrative}
