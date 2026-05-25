#!/usr/bin/env python3
"""解析 2024/2025 高考英语 PDF → 入 exam_questions 表.

从 gaokao 项目的 PDF 提取阅读/完形/语法填空/写作题, 结构化入库.
不处理听力 (PDF 无音频). 用 pypdf 抽文字, 按题型分段.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import duckdb
import pypdf

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"

PDFS = [
    (2024, "新课标 II 卷",
     Path("/Users/dp/Documents/M/gaokao/data/raw/pdfs/cdn_zgkao_com/zgkao_2024_xgkii_english__english_2024.pdf")),
    (2025, "新课标 II 卷",
     Path("/Users/dp/Documents/M/gaokao/data/raw/pdfs/jhgk_cn/jhgk_2025_xgkii_english__english_2025.pdf")),
]


def extract_text(pdf_path: Path) -> str:
    reader = pypdf.PdfReader(str(pdf_path))
    return "".join(p.extract_text() or "" for p in reader.pages)


def parse_questions(text: str, year: int) -> list[dict]:
    """按大题块分段: 阅读 A-D + 七选五 + 完形 + 语法填空 + 应用文 + 续写."""
    parts = _split_parts(text)
    questions = _parse_reading(parts["part2"], year)
    questions += _parse_language(parts["part3"], year)
    questions += _parse_writing(parts["part4"], year)
    return questions


def _split_parts(text: str) -> dict:
    return {
        "part2": _extract_between(text, "第二部分", "第三部分") or "",
        "part3": _extract_between(text, "第三部分", "第四部分") or "",
        "part4": _extract_between(text, "第四部分", None) or "",
    }


def _parse_reading(part2: str, year: int) -> list[dict]:
    qs = []
    for label in ["A", "B", "C", "D"]:
        block = _extract_passage(part2, label)
        if block and len(block) > 100:
            qs.append(_make_q(year, "阅读理解", block, ord(label) - ord("A") + 1))
    qiwu = _extract_between(part2, "第二节", None) or ""
    if len(qiwu) > 100:
        qs.append(_make_q(year, "完形填空(七选五/语篇)", qiwu, 36))
    return qs


def _parse_language(part3: str, year: int) -> list[dict]:
    qs = []
    cloze = _extract_between(part3, "第一节", "第二节") or part3[:2000]
    if len(cloze) > 100:
        qs.append(_make_q(year, "完形填空", cloze, 41))
    grammar = _extract_between(part3, "第二节", None) or ""
    if len(grammar) > 50:
        qs.append(_make_q(year, "语法填空", grammar, 56))
    return qs


def _parse_writing(part4: str, year: int) -> list[dict]:
    qs = []
    applied = _extract_between(part4, "第一节", "第二节") or ""
    if len(applied) > 50:
        qs.append(_make_q(year, "应用文写作", applied, 46))
    narrative = _extract_between(part4, "第二节", None) or ""
    if len(narrative) > 50:
        qs.append(_make_q(year, "续写", narrative, 47))
    return qs

    return questions


def _extract_passage(text: str, label: str) -> str:
    """提取阅读理解 A/B/C/D 篇."""
    next_label = chr(ord(label) + 1) if label < "D" else None
    pattern = rf'\n{label}\n'
    m = re.search(pattern, text)
    if not m:
        pattern = rf'\n{label}\s'
        m = re.search(pattern, text)
    if not m:
        return ""
    start = m.start()
    if next_label:
        end_pattern = rf'\n{next_label}\n|\n{next_label}\s'
        m2 = re.search(end_pattern, text[start + 2:])
        end = start + 2 + m2.start() if m2 else start + 3000
    else:
        end = min(start + 3000, len(text))
    return text[start:end].strip()


def _extract_between(text: str, start: str, end: str | None) -> str | None:
    si = text.find(start)
    if si < 0:
        return None
    si += len(start)
    if end:
        ei = text.find(end, si)
        return text[si:ei] if ei > si else text[si:]
    return text[si:]


def _make_q(year: int, qtype: str, raw: str, qnum: int) -> dict:
    return {
        "question_id": f"pdf/{year}/xgkii/{qtype}/{qnum}",
        "year": year,
        "province": f"辽宁 (新课标 II 卷, 2021+)",
        "paper_type": "新课标 II 卷",
        "question_type": qtype,
        "raw_question": raw[:2000],
        "answer": "",
        "analysis": "",
        "source_file": f"gaokao_pdf_{year}",
        "source_index": qnum,
        "source_repo": "local_pdf",
    }


def import_to_db(questions: list[dict]) -> int:
    con = duckdb.connect(str(DB_PATH))
    try:
        existing = {r[0] for r in con.execute("SELECT question_id FROM exam_questions").fetchall()}
        n = 0
        for q in questions:
            if q["question_id"] in existing:
                continue
            con.execute(
                "INSERT INTO exam_questions VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                [q["question_id"], q["year"], q["province"], q["paper_type"],
                 q["question_type"], q["raw_question"], q["answer"], q["analysis"],
                 q["source_file"], q["source_index"], q["source_repo"]],
            )
            cid = f"question:{q['question_id']}"
            if not con.execute("SELECT 1 FROM nodes WHERE concept_id=?", [cid]).fetchone():
                con.execute("INSERT INTO nodes VALUES (?,?,?,NULL)", [cid, "question", q["question_id"]])
            year_node = f"exam_year:{q['year']}"
            if not con.execute("SELECT 1 FROM nodes WHERE concept_id=?", [year_node]).fetchone():
                con.execute("INSERT INTO nodes VALUES (?,?,?,NULL)", [year_node, "exam_year", str(q["year"])])
            if not con.execute("SELECT 1 FROM edges WHERE src_id=? AND dst_id=?", [cid, year_node]).fetchone():
                con.execute("INSERT INTO edges VALUES (?,?,?,?)",
                            [cid, year_node, "exam_year_of", '{"source":"pdf_import"}'])
            n += 1
        return n
    finally:
        con.close()


def main():
    total = 0
    for year, paper, pdf_path in PDFS:
        if not pdf_path.exists():
            print(f"  SKIP {year}: {pdf_path} not found")
            continue
        text = extract_text(pdf_path)
        qs = parse_questions(text, year)
        print(f"  {year}: extracted {len(qs)} questions from {len(text)} chars")
        for q in qs[:3]:
            print(f"    {q['question_id']}: {q['raw_question'][:80]}...")
        n = import_to_db(qs)
        total += n
        print(f"    imported {n} new (skipped {len(qs) - n} existing)")
    print(f"\nTotal imported: {total}")
    con = duckdb.connect(str(DB_PATH), read_only=True)
    for r in con.execute("SELECT year, COUNT(*) FROM exam_questions WHERE year >= 2024 GROUP BY 1").fetchall():
        print(f"  DB year {r[0]}: {r[1]} questions")
    con.close()


if __name__ == "__main__":
    main()
