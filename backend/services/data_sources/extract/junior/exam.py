"""中考真题 jsonl → exam_questions 入库 (域A 检验层, inc1; 模块化单一计算点).

源: data/junior_high/exams/{year}_liaoning/exam_questions.jsonl (extract_zhongkao 产, 已验证)。
判别维: province=辽宁(与高考辽宁卷同名) **靠 exam_type=中考 区分**(K12设计§1 三判别维), 不靠 province。
2024 题面 stem walled → raw_question 记 stem_status; 2025 题面驱动 → stem + options 拼。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]            # .../gaozhong
EXAMS = ROOT / "data" / "junior_high" / "exams"
YEARS = ("2024", "2025")
_COLS = ("question_id,year,province,paper_type,question_type,raw_question,answer,"
         "analysis,source_file,source_index,source_repo,exam_type")


def _raw(r: dict) -> str | None:
    """题面: 2025 stem(+options 拼); 2024 walled → 记 stem_status (诚实, 不伪造题面)."""
    stem = (r.get("raw_question") or "").strip()
    opts = r.get("options") or {}
    if opts:
        stem = (stem + " | " + "  ".join(f"{k}.{v}" for k, v in sorted(opts.items()))).strip(" |")
    return stem or r.get("stem_status")


def _rows(year: str) -> list[tuple]:
    f = EXAMS / f"{year}_liaoning" / "exam_questions.jsonl"
    if not f.exists():
        return []
    rows = []
    for line in f.open(encoding="utf-8"):
        r = json.loads(line)
        rows.append((
            r["question_id"], r["year"], r["province"], r["paper_type"], r["question_type"],
            _raw(r), r.get("answer"), r.get("kaodian"),        # analysis ← 语篇填空逐空考点
            r.get("source"), r.get("question_number"), r.get("provenance", "B"), "中考",
        ))
    return rows


def load(con) -> dict:
    """中考真题入 exam_questions (单一计算点; init_db 的 junior Layer 调)."""
    rows = [row for y in YEARS for row in _rows(y)]
    if rows:
        con.executemany(
            f"INSERT OR REPLACE INTO exam_questions_all ({_COLS}) VALUES ({','.join(['?'] * 12)})", rows)
    return {"中考真题入库": len(rows), "years": list(YEARS), "exam_type": "中考"}
