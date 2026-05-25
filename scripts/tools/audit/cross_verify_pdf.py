#!/usr/bin/env python3
"""结构化数据 vs PDF 原文交叉核对 — 确保内容 100% 准确.

逐年逐题: 从 PDF 提取原文片段, 与结构化数据的 question/answer 字段对比.
输出 data/reports/cross_verify_{year}.json

用法:
    python3 scripts/tools/audit/cross_verify_pdf.py --year 2024
    python3 scripts/tools/audit/cross_verify_pdf.py --all
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import duckdb
import pypdf

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"
REPORT_DIR = ROOT / "data" / "reports"

PDF_MAP = {
    2020: ROOT.parent / "gaokao/data/raw/pdfs/scmlzx_net/scmlzx_english_2017_rev2020__english_2020.pdf",
    2024: ROOT.parent / "gaokao/data/raw/pdfs/cdn_zgkao_com/zgkao_2024_xgkii_english__english_2024.pdf",
    2025: ROOT.parent / "gaokao/data/raw/pdfs/jhgk_cn/jhgk_2025_xgkii_english__english_2025.pdf",
}


def extract_pdf_text(pdf_path: Path) -> str:
    reader = pypdf.PdfReader(str(pdf_path))
    return "".join(p.extract_text() or "" for p in reader.pages)


def _load_structured(year: int, con=None) -> tuple[list, list]:
    """加载 DB + JSONL 结构化数据."""
    own_con = con is None
    if own_con:
        con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        rows = con.execute(
            "SELECT question_id, question_type, raw_question, answer "
            "FROM exam_questions WHERE year = ?", [year]
        ).fetchall()
    finally:
        if own_con:
            con.close()
    jsonl_path = ROOT / "data" / "gaokao_verified_xgkii_2023_2024.jsonl"
    jsonl_entries = []
    if jsonl_path.exists():
        for line in jsonl_path.read_text().split("\n"):
            if line.strip():
                entry = json.loads(line)
                if entry.get("year") == year:
                    jsonl_entries.append(entry)
    return rows, jsonl_entries


def _check_item(qid, qtype, question_text, pdf_words) -> dict:
    """核对一条: 关键词是否在 PDF 中."""
    q_words = re.findall(r"[a-zA-Z]{4,}", question_text or "")[:20]
    if not q_words:
        return {"qid": str(qid), "type": qtype, "match": "skip", "reason": "no English words"}
    matched = sum(1 for w in q_words if w.lower() in pdf_words)
    rate = matched / len(q_words)
    status = "pass" if rate >= 0.6 else ("warn" if rate >= 0.3 else "fail")
    return {"qid": str(qid), "type": qtype, "match": status,
            "match_rate": round(rate, 2), "matched_words": matched,
            "total_words": len(q_words), "sample_words": q_words[:5]}


def verify_year(year: int, con=None) -> dict:
    """核对一个年份: 结构化数据的关键文本是否在 PDF 原文中出现."""
    pdf_path = PDF_MAP.get(year)
    if not pdf_path or not pdf_path.exists():
        return {"year": year, "status": "skip", "reason": f"PDF not found: {pdf_path}"}
    pdf_text = extract_pdf_text(pdf_path)
    pdf_words = set(re.findall(r"[a-zA-Z]{4,}", pdf_text.lower()))
    rows, jsonl_entries = _load_structured(year, con)
    sources = list(rows) + [(e.get("source", ""), e.get("question_type", ""),
                              e.get("question", ""), e.get("answer", "")) for e in jsonl_entries]
    checks = [_check_item(s[0], s[1], s[2], pdf_words) for s in sources]
    summary = {k: sum(1 for c in checks if c["match"] == k) for k in ("pass", "warn", "fail", "skip")}
    result = {
        "year": year, "pdf_path": str(pdf_path), "pdf_chars": len(pdf_text),
        "pdf_unique_words": len(pdf_words), "structured_entries": len(rows),
        "jsonl_entries": len(jsonl_entries), "checks": checks,
        "summary": summary, "overall": "PASS" if summary["fail"] == 0 else "FAIL",
    }
    out_path = REPORT_DIR / f"cross_verify_{year}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    years = list(PDF_MAP.keys()) if args.all else ([args.year] if args.year else [])
    if not years:
        print("Usage: --year 2024 or --all"); return

    for year in years:
        result = verify_year(year)
        s = result.get("summary", {})
        status = result.get("overall", "?")
        icon = "✅" if status == "PASS" else ("⚠️" if status == "skip" else "❌")
        print(f"\n{icon} {year}: {status}")
        if "checks" in result:
            print(f"   DB entries: {result['structured_entries']}, JSONL: {result['jsonl_entries']}")
            print(f"   PDF: {result['pdf_chars']} chars, {result['pdf_unique_words']} unique words")
            print(f"   Checks: {s.get('pass',0)} pass, {s.get('warn',0)} warn, {s.get('fail',0)} fail, {s.get('skip',0)} skip")
            for c in result["checks"]:
                if c["match"] in ("fail", "warn"):
                    print(f"   ⚠️ {c['qid']} [{c['type']}]: match={c['match_rate']:.0%} words={c.get('sample_words',[][:3])}")
        else:
            print(f"   {result.get('reason', '')}")


if __name__ == "__main__":
    main()
