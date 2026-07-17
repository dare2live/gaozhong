#!/usr/bin/env python3
"""Import 2022–2025 XGKII listening stems into exam_questions_all / question_bank.

Harvest: listening_stems_harvest.py. Idempotent; does not wipe qbank.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import duckdb

from backend.services.question_bank.loader import autotag, insert_question
from backend.services.trend import scope
from scripts.tools.map.listening_stems_harvest import (
    OUT,
    harvest_2022,
    harvest_2023,
    harvest_2024,
    harvest_2025,
    write_jsonl,
)
from scripts.tools.map.listening_stems_parse import fmt_raw

PROVINCE = scope.LIAONING_XGKII_2021
PAPER = scope.PAPER_XGKII
REPO = "listening_stems_xgkii"


def import_rows(rows: list[dict]) -> dict:
    from backend.services.links import build_question_in_year, build_question_type

    con = duckdb.connect(str(ROOT / "data/db/gaozhong.duckdb"))
    cefr = {r[0] for r in con.execute("SELECT word FROM cefr_vocab").fetchall()}
    inserted_eq = 0
    inserted_qb = 0
    try:
        for r in rows:
            year, n = r["year"], r["n"]
            qid = f"listening/{year}/xgkii/{n}"
            raw = fmt_raw(n, r["stem"], r.get("options") or {})
            src = f"listening_stems/{year}"
            con.execute("DELETE FROM exam_questions_all WHERE question_id = ?", [qid])
            con.execute(
                "INSERT INTO exam_questions_all "
                "(question_id, year, province, paper_type, question_type, "
                " raw_question, answer, analysis, source_file, source_index, "
                " source_repo, exam_type) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                [
                    qid, year, PROVINCE, PAPER, "听力", raw, r["answer"],
                    f"listening stem import; source={r.get('source')}",
                    src, n, REPO, "高考",
                ],
            )
            cid = f"question:{qid}"
            con.execute("DELETE FROM nodes WHERE concept_id = ?", [cid])
            con.execute(
                "INSERT INTO nodes VALUES (?,?,?,?)",
                [
                    cid, "question", f"{year} 听力",
                    json.dumps({"year": year, "province": PROVINCE, "type": "听力"}, ensure_ascii=False),
                ],
            )
            inserted_eq += 1
            old = con.execute(
                "SELECT qb_id FROM question_bank WHERE origin_ref = ?", [qid]
            ).fetchall()
            for (qb_id,) in old:
                con.execute("DELETE FROM question_tags WHERE qb_id = ?", [qb_id])
                con.execute("DELETE FROM question_bank WHERE qb_id = ?", [qb_id])
            qb_id = insert_question(
                con, "real", qid, "听力", raw,
                json.dumps(r.get("options") or {}, ensure_ascii=False),
                r["answer"], f"source={r.get('source')}",
            )
            autotag(con, qb_id, raw, year, "听力", cefr, origin_ref=qid)
            inserted_qb += 1
        build_question_in_year(con)
        build_question_type(con)
    finally:
        con.close()
    return {"exam_questions": inserted_eq, "question_bank": inserted_qb}


def main() -> int:
    all_rows: list[dict] = []
    for harvester in (harvest_2022, harvest_2023, harvest_2024, harvest_2025):
        rows = harvester()
        assert len(rows) == 20, harvester.__name__
        write_jsonl(rows[0]["year"], rows)
        all_rows.extend(rows)
        print(f"OK harvest {rows[0]['year']}: 20 stems -> {OUT}/{rows[0]['year']}_xgkii_listening_stems.jsonl")
    stats = import_rows(all_rows)
    print("import", stats)
    con = duckdb.connect(str(ROOT / "data/db/gaozhong.duckdb"), read_only=True)
    print(
        "listening by year",
        con.execute(
            "SELECT year, count(*) FROM exam_questions WHERE question_type='听力' GROUP BY 1 ORDER BY 1"
        ).fetchall(),
    )
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
