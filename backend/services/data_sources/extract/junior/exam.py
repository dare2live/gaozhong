"""中考真题 jsonl → exam_questions 入库 (域A 检验层, inc1; 模块化单一计算点).

源: data/junior_high/exams/{year}_liaoning/exam_questions.jsonl (extract_zhongkao 产, 已验证)。
判别维: province=辽宁(与高考辽宁卷同名) **靠 exam_type=中考 区分**(K12设计§1 三判别维), 不靠 province。
题面: 有 raw_question(+options) 则拼接入库; 无则退化记 stem_status(诚实, 不伪造题面) ——
数据驱动、不按年份 hardcode(2024 曾全 walled, 2026-07-08 全网挖掘找到第6渠道后转真,
本函数逻辑无需改动即自动纳入, 见 junior/qbank.py 模块docstring)。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]            # .../gaozhong
EXAMS = ROOT / "data" / "junior_high" / "exams"


def available_years() -> tuple[str, ...]:
    """有 exam_questions.jsonl 的中考年 (数据驱动, 不 hardcode; 新年目录落地即纳入)."""
    years = []
    for d in sorted(EXAMS.glob("*_liaoning")):
        if (d / "exam_questions.jsonl").exists():
            years.append(d.name.split("_", 1)[0])
    return tuple(years)


# 兼容旧引用 (测试/预检); 真值 = available_years() 现算
YEARS = available_years()
_COLS = ("question_id,year,province,paper_type,question_type,raw_question,answer,"
         "analysis,source_file,source_index,source_repo,exam_type")


def _raw(r: dict) -> str | None:
    """题面: 有 stem(+options 拼); 无 → 记 stem_status (诚实, 不伪造题面)."""
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
    rows = [row for y in available_years() for row in _rows(y)]
    if rows:
        con.executemany(
            f"INSERT OR REPLACE INTO exam_questions_all ({_COLS}) VALUES ({','.join(['?'] * 12)})", rows)
    return {"中考真题入库": len(rows), "years": list(YEARS), "exam_type": "中考"}
