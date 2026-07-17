"""D0: listening transcript teaching aids grounded in stem/answer/transcript."""
from __future__ import annotations

import json
import re

import duckdb

from backend.services.listening.teaching_aid import JSONL, REQUIRED_KEYS, clear_cache


def check_listening_teaching(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== 听力文字稿讲解辅助 (transcript-grounded teaching aids) ===")
    clear_cache()
    check("listening_teaching jsonl 存在", JSONL.is_file(), str(JSONL))
    if not JSONL.is_file():
        return
    rows = []
    bad_json = 0
    with JSONL.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                bad_json += 1
    check("listening_teaching json 可解析", bad_json == 0, f"bad={bad_json}")
    check("listening_teaching n == 100 (2021-2025)", len(rows) == 100, f"n={len(rows)}")

    refs = {
        r[0]
        for r in con.execute(
            "SELECT origin_ref FROM question_bank WHERE has_audio=true AND question_type='听力'"
        ).fetchall()
        if r[0]
    }
    missing_keys = 0
    unknown_ref = 0
    ans_mismatch = 0
    bad_cue = 0
    bad_prov = 0
    for r in rows:
        if any(k not in r for k in REQUIRED_KEYS):
            missing_keys += 1
        ref = r.get("origin_ref")
        if ref not in refs:
            unknown_ref += 1
            continue
        qb = con.execute(
            "SELECT answer, transcript FROM question_bank "
            "WHERE origin_ref=? AND has_audio=true",
            [ref],
        ).fetchone()
        if not qb:
            unknown_ref += 1
            continue
        ans, tr = qb
        if (r.get("answer") or "").upper()[:1] != (ans or "").upper()[:1]:
            ans_mismatch += 1
        if r.get("provenance") != "agent_transcript_grounded":
            bad_prov += 1
        for d in r.get("distractors") or []:
            cue = d.get("cue_in_transcript")
            if not cue:
                continue
            compact = lambda s: re.sub(r"\s+", "", (s or "").lower())
            if compact(cue) not in compact(tr) and cue not in (tr or ""):
                bad_cue += 1

    need = [
        x[0]
        for x in con.execute(
            "SELECT origin_ref FROM question_bank "
            "WHERE has_audio=true AND question_type='听力' "
            "AND origin_ref NOT LIKE '%2026%' AND length(transcript)>=40"
        ).fetchall()
    ]
    have = {r.get("origin_ref") for r in rows}
    coverage_gap = [x for x in need if x not in have]

    check("listening_teaching 必填字段齐全", missing_keys == 0, f"bad={missing_keys}")
    check("listening_teaching origin_ref ∈ qbank", unknown_ref == 0, f"bad={unknown_ref}")
    check("listening_teaching answer 与库一致", ans_mismatch == 0, f"bad={ans_mismatch}")
    check("listening_teaching cue ⊆ transcript", bad_cue == 0, f"bad={bad_cue}")
    check("listening_teaching provenance=agent_transcript_grounded", bad_prov == 0, f"bad={bad_prov}")
    check("listening_teaching 覆盖 2021-2025 has_audio 题", len(coverage_gap) == 0, f"gap={coverage_gap[:3]}")
