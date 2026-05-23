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
    "Subject:", "RSVP", "Best regards", "Kind regards", "Hi ", "Hello,",
    "Looking forward to hearing from you", "I am writing to",
    "I'd like to invite", "On behalf of",
]
NARRATIVE_MARKERS = [
    "Once upon a time", "One day", "suddenly", "moments later",
    "to my surprise", "I remember", "It happened", "when I",
    "as I", "I felt", "I saw", "I heard", "she said", "he said",
    "story", "tale",
]


def _score_narrative(text: str) -> int:
    t = text.lower()
    hits = sum(1 for m in NARRATIVE_MARKERS if m.lower() in t)
    # heuristic: past tense (-ed) density
    ed_count = len(re.findall(r"\b\w+ed\b", t)) // 30  # / 30 normalize (放松)
    return hits + ed_count


def flag_sections(con: duckdb.DuckDBPyConnection) -> dict:
    # listening (kind-based) — broaden: 任何含 Listening kind
    con.execute("UPDATE sections SET is_listening = (kind = 'Listening')")
    # applied / narrative — text-based, 阈值放松, 关键词扩
    rows = con.execute("""
        SELECT s.version_key, s.volume_key, s.unit_number, s.seq, s.kind, st.raw_text
        FROM sections s
        LEFT JOIN section_text st USING (version_key, volume_key, unit_number, seq)
    """).fetchall()
    n_applied = n_narrative = 0
    for ver, vol, un, seq, kind, text in rows:
        text = text or ""
        is_app = False; is_nar = False
        # 应用文: Writing kind 或任何 kind 含 ≥ 2 应用文 markers
        applied_hits = sum(1 for m in APPLIED_MARKERS if m in text)
        if (kind in {"Writing", "Integrated"} and applied_hits >= 1) or applied_hits >= 2:
            is_app = True; n_applied += 1
        # 叙事: Reading kind 阈值 ≥ 1 (从 2 放松)
        if kind in {"Reading", "Integrated"} and _score_narrative(text) >= 1:
            is_nar = True; n_narrative += 1
        if is_app or is_nar:
            con.execute("""
                UPDATE sections SET is_applied=?, is_narrative=?
                WHERE version_key=? AND volume_key=? AND unit_number=? AND seq=?
            """, [is_app, is_nar, ver, vol, un, seq])
    return {"sections": len(rows), "is_applied": n_applied, "is_narrative": n_narrative}
