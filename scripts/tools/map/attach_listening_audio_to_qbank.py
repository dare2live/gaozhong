"""Attach fingerprint-verified audio + transcript to listening qb rows.

Covers:
  2021 eol Q1–20 → full.mp3 + Text N transcript
  2022–24 listening/{year}/xgkii/{n} → kekenet segment files + Text N
  2025 listening/2025/xgkii/{n} → full.mp3 + full transcript
  2026 section blob → full.mp3

Re-runnable. Does not invent stems.
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

# Standard XGKII listening: Text1–5 short → Q1–5; Text6→Q6–7; Text7→Q8–10;
# Text8→Q11–13; Text9→Q14–17; Text10→Q18–20.
_Q_TO_TEXT = {
    1: 1,
    2: 2,
    3: 3,
    4: 4,
    5: 5,
    6: 6,
    7: 6,
    8: 7,
    9: 7,
    10: 7,
    11: 8,
    12: 8,
    13: 8,
    14: 9,
    15: 9,
    16: 9,
    17: 9,
    18: 10,
    19: 10,
    20: 10,
}

# kekenet promote_map segment ids for Text N (2022–24)
_TEXT_TO_AUDIO_SEGMENT = {
    1: "short_all",
    2: "short_all",
    3: "short_all",
    4: "short_all",
    5: "short_all",
    6: "dialog_01",
    7: "dialog_02",
    8: "dialog_03",
    9: "dialog_04",
    10: "passage_01",
}

_TX_FILES = {
    2021: "2021_xgki_ii_cpsenglish_transcript.md",
    2022: "2022_xgki_ii_cpsenglish_transcript.md",
    2023: "2023_xgki_ii_listening_transcript.md",
    2024: "2024_xgkii_netease_transcript.md",
    # renrendoc uses Text1..; newdu analysis also embeds Text blocks
    2025: "2025_xgkii_renrendoc_transcript.md",
}


def _split_texts(md: str) -> dict[int, str]:
    # Accept "Text 1" / "Text1" / "Text\t1"
    parts = re.split(r"(?mi)^\s*Text\s*(\d+)\s*$", md)
    out: dict[int, str] = {}
    i = 1
    while i + 1 < len(parts):
        n = int(parts[i])
        body = parts[i + 1].strip()
        body = re.split(r"(?mi)^\s*Text\s*\d+\s*$", body)[0].strip()
        out[n] = body
        i += 2
    return out


def _strip_md_meta(md: str) -> str:
    return re.sub(r"(?m)^#.*\n|^source:.*\n|^note:.*\n", "", md).strip()


def _update(
    con: duckdb.DuckDBPyConnection,
    origin_ref: str,
    audio_id: str,
    transcript: str,
) -> bool:
    if len(transcript) < 20:
        return False
    con.execute(
        """
        UPDATE question_bank
        SET has_audio = true,
            audio_id = ?,
            transcript = ?,
            origin_ref = coalesce(origin_ref, ?)
        WHERE origin_ref = ? AND question_type = '听力'
        """,
        [audio_id, transcript, origin_ref, origin_ref],
    )
    return True


def attach() -> dict:
    updated: list[dict] = []
    con = duckdb.connect(str(DB))
    try:
        # --- 2021 eol ---
        t2021 = _split_texts((TX / _TX_FILES[2021]).read_text(encoding="utf-8"))
        for qn, text_n in _Q_TO_TEXT.items():
            origin = f"eol/2021/xgkii/{qn}"
            if _update(con, origin, "2021/listening/full.mp3", t2021.get(text_n, "")):
                updated.append(
                    {"origin_ref": origin, "text": text_n, "audio_id": "2021/listening/full.mp3"}
                )

        # --- 2022–24 segmented ---
        for year in (2022, 2023, 2024):
            texts = _split_texts((TX / _TX_FILES[year]).read_text(encoding="utf-8"))
            for qn, text_n in _Q_TO_TEXT.items():
                origin = f"listening/{year}/xgkii/{qn}"
                seg = _TEXT_TO_AUDIO_SEGMENT[text_n]
                audio_id = f"{year}/listening/{seg}.mp3"
                if _update(con, origin, audio_id, texts.get(text_n, "")):
                    updated.append(
                        {"origin_ref": origin, "text": text_n, "audio_id": audio_id}
                    )

        # --- 2025 full paper ---
        raw_2025 = (TX / _TX_FILES[2025]).read_text(encoding="utf-8")
        raw_2025 = re.sub(r"(?mi)^( *Text)(\d+)\b", r"\1 \2", raw_2025)
        t2025 = _strip_md_meta(raw_2025)
        texts_2025 = _split_texts(t2025)
        if len(texts_2025) < 10:
            # last resort: whole body as shared transcript
            texts_2025 = {n: t2025 for n in range(1, 11)}
        for qn, text_n in _Q_TO_TEXT.items():
            origin = f"listening/2025/xgkii/{qn}"
            body = texts_2025.get(text_n) or t2025
            if _update(con, origin, "2025/listening/full.mp3", body):
                updated.append(
                    {
                        "origin_ref": origin,
                        "text": text_n,
                        "audio_id": "2025/listening/full.mp3",
                    }
                )

        # --- 2026 section blob ---
        t2026 = _strip_md_meta(
            (TX / "2026_national_ii_sjds_transcript.md").read_text(encoding="utf-8")
        )
        if _update(con, "xgkii/2026/listening", "2026/listening/full.mp3", t2026):
            updated.append(
                {
                    "origin_ref": "xgkii/2026/listening",
                    "audio_id": "2026/listening/full.mp3",
                }
            )

        n = con.execute(
            "SELECT count(*) FROM question_bank WHERE has_audio = true"
        ).fetchone()[0]
        by_year = con.execute(
            """
            SELECT
              CASE
                WHEN origin_ref LIKE 'eol/2021/%' THEN 2021
                WHEN origin_ref LIKE 'listening/%/xgkii/%' THEN
                  CAST(split_part(origin_ref, '/', 2) AS INTEGER)
                WHEN origin_ref LIKE 'xgkii/2026/%' THEN 2026
                ELSE NULL
              END AS y,
              count(*)
            FROM question_bank
            WHERE has_audio = true AND question_type = '听力'
            GROUP BY 1
            ORDER BY 1
            """
        ).fetchall()
    finally:
        con.close()
    return {
        "updated_n": len(updated),
        "has_audio_count": n,
        "listening_has_audio_by_year": by_year,
        "updated": updated,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(attach(), ensure_ascii=False, indent=2))
