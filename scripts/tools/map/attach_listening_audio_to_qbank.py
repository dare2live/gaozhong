"""Attach fingerprint-verified full-paper audio + transcript to existing qb rows.

Only updates rows that already exist (2021 eol listening Q1–20, 2026 section blob).
Re-runnable. Does not invent new stems.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import duckdb

TX = ROOT / "data/external/exam_sources/listening_transcripts"
DB = ROOT / "data/db/gaozhong.duckdb"


def _split_texts(md: str) -> dict[int, str]:
    parts = re.split(r"(?m)^\s*Text\s+(\d+)\s*$", md)
    out: dict[int, str] = {}
    i = 1
    while i + 1 < len(parts):
        n = int(parts[i])
        body = parts[i + 1].strip()
        body = re.split(r"(?m)^\s*Text\s+\d+\s*$", body)[0].strip()
        out[n] = body
        i += 2
    return out


# 2021 Q# → Text#
_Q_TO_TEXT_2021 = {
    1: 1, 2: 2, 3: 3, 4: 4, 5: 5,
    6: 6, 7: 6,
    8: 7, 9: 7, 10: 7,
    11: 8, 12: 8, 13: 8,
    14: 9, 15: 9, 16: 9, 17: 9,
    18: 10, 19: 10, 20: 10,
}


def attach() -> dict:
    t2021 = _split_texts((TX / "2021_xgki_ii_cpsenglish_transcript.md").read_text(encoding="utf-8"))
    t2026 = (TX / "2026_national_ii_sjds_transcript.md").read_text(encoding="utf-8")
    # strip markdown header noise for 2026 full blob
    t2026_body = re.sub(r"(?m)^#.*\n|^source:.*\n|^note:.*\n", "", t2026).strip()

    con = duckdb.connect(str(DB))
    updated = []
    try:
        for qn, text_n in _Q_TO_TEXT_2021.items():
            origin = f"eol/2021/xgkii/{qn}"
            transcript = t2021.get(text_n, "")
            if len(transcript) < 20:
                continue
            audio_id = "2021/listening/full.mp3"
            con.execute(
                """
                UPDATE question_bank
                SET has_audio = true,
                    audio_id = ?,
                    transcript = ?,
                    origin_ref = coalesce(origin_ref, ?)
                WHERE origin_ref = ? AND question_type = '听力'
                """,
                [audio_id, transcript, origin, origin],
            )
            updated.append({"origin_ref": origin, "text": text_n, "audio_id": audio_id})

        con.execute(
            """
            UPDATE question_bank
            SET has_audio = true,
                audio_id = ?,
                transcript = ?
            WHERE origin_ref = 'xgkii/2026/listening' AND question_type = '听力'
            """,
            ["2026/listening/full.mp3", t2026_body],
        )
        updated.append(
            {
                "origin_ref": "xgkii/2026/listening",
                "audio_id": "2026/listening/full.mp3",
            }
        )
        n = con.execute(
            "SELECT count(*) FROM question_bank WHERE has_audio = true"
        ).fetchone()[0]
    finally:
        con.close()
    return {"updated": updated, "has_audio_count": n}


if __name__ == "__main__":
    import json

    print(json.dumps(attach(), ensure_ascii=False, indent=2))
