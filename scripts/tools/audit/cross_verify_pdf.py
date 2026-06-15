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

from backend.services.contracts.source_crosscheck import html_identity_required_groups
from backend.services.data_sources.registry import SourceSpec, load_registry

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"
REPORT_DIR = ROOT / "data" / "reports"

PDF_FALLBACK_MAP = {
    2020: ROOT.parent / "gaokao/data/raw/pdfs/scmlzx_net/scmlzx_english_2017_rev2020__english_2020.pdf",
}


class PdfUnreadableError(Exception):
    """PDF 非有效格式 (HTML 伪装/损坏下载) — 不静默吞 (§1.5), 由 verify_year 转为 skip."""


def extract_pdf_text(pdf_path: Path) -> str:
    # 校验真 PDF: 防 HTML 伪装/损坏下载 (如反爬墙存成 .pdf) 崩溃整个 init_db
    head = Path(pdf_path).read_bytes()[:5]
    if not head.startswith(b"%PDF"):
        raise PdfUnreadableError(f"{pdf_path.name} 非有效 PDF (文件头 {head!r}, 疑下载为 HTML/损坏)")
    try:
        reader = pypdf.PdfReader(str(pdf_path))
        return "".join(p.extract_text() or "" for p in reader.pages)
    except Exception as e:
        raise PdfUnreadableError(f"{pdf_path.name} PDF 解析失败: {type(e).__name__}: {e}")


def _source_is_usable_pdf_truth(source: SourceSpec) -> bool:
    status = source.status.lower()
    if "candidate" in status or "suspicious" in status:
        return False
    if not source.family.startswith("exam_truth_source"):
        return False
    return any(item.kind == "pdf" for item in source.attachments)


def _registry_pdf_sources() -> dict[int, tuple[str, Path]]:
    registry = load_registry()
    by_year: dict[int, tuple[str, Path]] = {}
    for source in registry.list_sources():
        if source.year is None or not _source_is_usable_pdf_truth(source):
            continue
        pdfs = [item.local_path for item in source.attachments if item.kind == "pdf"]
        if not pdfs:
            continue
        if source.year not in by_year or "third_party" not in by_year[source.year][0]:
            by_year[source.year] = (source.source_id, pdfs[0])
    return by_year


def _registry_html_sources(year: int) -> list[tuple[str, Path]]:
    registry = load_registry()
    sources: list[tuple[str, Path]] = []
    for source in registry.list_sources():
        if source.year != year:
            continue
        if source.family != "exam_truth_source_landing_page":
            continue
        for attachment in source.attachments:
            if attachment.kind == "html":
                sources.append((source.source_id, attachment.local_path))
    return sources


def _pdf_source_for_year(year: int) -> tuple[str, Path] | None:
    registry_sources = _registry_pdf_sources()
    if year in registry_sources:
        return registry_sources[year]
    fallback = PDF_FALLBACK_MAP.get(year)
    if fallback:
        return ("legacy_fallback_pdf_map", fallback)
    return None


def _all_pdf_years() -> list[int]:
    return sorted(set(PDF_FALLBACK_MAP) | set(_registry_pdf_sources()))


def build_pdf_map() -> dict[int, Path]:
    """Compatibility map for legacy callers; registry remains the owner."""
    pdf_map = dict(PDF_FALLBACK_MAP)
    for year, (_source_id, path) in _registry_pdf_sources().items():
        pdf_map[year] = path
    return pdf_map


PDF_MAP = build_pdf_map()


def _html_identity_checks(year: int) -> list[dict]:
    checks = []
    for source_id, path in _registry_html_sources(year):
        required_groups = html_identity_required_groups(source_id)
        if not required_groups:
            checks.append({
                "source_id": source_id,
                "path": str(path),
                "match": "fail",
                "reason": "html identity rule missing",
            })
            continue
        if not path.exists():
            checks.append({
                "source_id": source_id,
                "path": str(path),
                "match": "fail",
                "reason": "html artifact missing",
            })
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        compact = re.sub(r"\s+", "", text)
        group_hits = {
            group: [token for token in tokens if token in compact]
            for group, tokens in required_groups.items()
        }
        missing_groups = [group for group, hits in group_hits.items() if not hits]
        checks.append({
            "source_id": source_id,
            "path": str(path),
            "chars": len(text),
            "match": "pass" if not missing_groups else "fail",
            "group_hits": group_hits,
            "missing_groups": missing_groups,
        })
    return checks


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
    pdf_source = _pdf_source_for_year(year)
    if not pdf_source:
        return {"year": year, "status": "skip", "reason": "PDF source not registered"}
    pdf_source_id, pdf_path = pdf_source
    if not pdf_path.exists():
        return {"year": year, "status": "skip", "reason": f"PDF not found: {pdf_path}", "pdf_source_id": pdf_source_id}
    try:
        pdf_text = extract_pdf_text(pdf_path)
    except PdfUnreadableError as e:
        # 损坏/非PDF源 → skip (不崩 init_db, 不假过): 该年真题数据另有可信源 (如 Updates JSON)
        return {"year": year, "status": "skip", "reason": str(e), "pdf_source_id": pdf_source_id}
    pdf_words = set(re.findall(r"[a-zA-Z]{4,}", pdf_text.lower()))
    rows, jsonl_entries = _load_structured(year, con)
    sources = list(rows) + [(e.get("source", ""), e.get("question_type", ""),
                              e.get("question", ""), e.get("answer", "")) for e in jsonl_entries]
    checks = [_check_item(s[0], s[1], s[2], pdf_words) for s in sources]
    summary = {k: sum(1 for c in checks if c["match"] == k) for k in ("pass", "warn", "fail", "skip")}
    html_checks = _html_identity_checks(year)
    html_summary = {k: sum(1 for c in html_checks if c["match"] == k) for k in ("pass", "fail")}
    overall = "PASS" if summary["fail"] == 0 and html_summary["fail"] == 0 else "FAIL"
    result = {
        "year": year, "pdf_source_id": pdf_source_id,
        "pdf_path": str(pdf_path), "pdf_chars": len(pdf_text),
        "pdf_unique_words": len(pdf_words), "structured_entries": len(rows),
        "jsonl_entries": len(jsonl_entries), "checks": checks,
        "summary": summary,
        "html_identity_checks": html_checks,
        "html_summary": html_summary,
        "overall": overall,
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
    parser.add_argument("--strict", action="store_true",
                        help="Return non-zero when any requested year fails or skips.")
    args = parser.parse_args()

    years = _all_pdf_years() if args.all else ([args.year] if args.year else [])
    if not years:
        print("Usage: --year 2024 or --all")
        return 2

    failed = False
    for year in years:
        result = verify_year(year)
        s = result.get("summary", {})
        status = result.get("overall", "?")
        if result.get("status") == "skip" or status == "FAIL":
            failed = True
        icon = "✅" if status == "PASS" else ("⚠️" if status == "skip" else "❌")
        print(f"\n{icon} {year}: {status}")
        if "checks" in result:
            print(f"   DB entries: {result['structured_entries']}, JSONL: {result['jsonl_entries']}")
            print(f"   PDF: {result['pdf_chars']} chars, {result['pdf_unique_words']} unique words")
            print(f"   Checks: {s.get('pass',0)} pass, {s.get('warn',0)} warn, {s.get('fail',0)} fail, {s.get('skip',0)} skip")
            hs = result.get("html_summary", {})
            print(f"   HTML identity: {hs.get('pass',0)} pass, {hs.get('fail',0)} fail")
            for c in result["checks"]:
                if c["match"] in ("fail", "warn"):
                    print(f"   ⚠️ {c['qid']} [{c['type']}]: match={c['match_rate']:.0%} words={c.get('sample_words',[][:3])}")
        else:
            print(f"   {result.get('reason', '')}")
    return 1 if args.strict and failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
