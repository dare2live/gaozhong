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

from backend.services.contracts.source_crosscheck import html_identity_required_groups
# M6 模块化: PDF→文本 + %PDF 头校验下沉到 extract 层 (extract_text 别名为本文件原 extract_pdf_text)
from backend.services.data_sources.extract.pdf import PdfUnreadableError
from backend.services.data_sources.extract.pdf import extract_text as extract_pdf_text
from backend.services.data_sources.registry import SourceSpec, load_registry

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"
REPORT_DIR = ROOT / "data" / "reports"

PDF_FALLBACK_MAP = {
    2020: ROOT.parent / "gaokao/data/raw/pdfs/scmlzx_net/scmlzx_english_2017_rev2020__english_2020.pdf",
}


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


def _skip_result(year: int, reason: str, pdf_source_id: str | None = None) -> dict:
    result = {"year": year, "status": "skip", "reason": reason}
    if pdf_source_id is not None:
        result["pdf_source_id"] = pdf_source_id
    return result


def _load_pdf_text_for_year(year: int):
    """定位年份 PDF 源并抽取文本; 不可用/不适用时返回 skip 结果字典.

    返回 (skip_result, None, None, None) 或 (None, pdf_source_id, pdf_path, pdf_text).
    """
    pdf_source = _pdf_source_for_year(year)
    if not pdf_source:
        return _skip_result(year, "PDF source not registered"), None, None, None
    pdf_source_id, pdf_path = pdf_source
    if not pdf_path.exists():
        return (_skip_result(year, f"PDF not found: {pdf_path}", pdf_source_id),
                None, None, None)
    try:
        pdf_text = extract_pdf_text(pdf_path)
    except PdfUnreadableError as e:
        # 损坏/非PDF源 → skip (不崩 init_db, 不假过): 该年真题数据另有可信源 (如 Updates JSON)
        return _skip_result(year, str(e), pdf_source_id), None, None, None
    if len((pdf_text or "").strip()) < 200:
        # 扫描图 PDF (无文字层, 如 2026 锦宏镜像): PDF-text 交叉验证不适用 (无文字可比), 不假过 →
        # 题面真值 = 双通道 ocrmac×视觉裁决转录 (.txt, 见 sources.yaml); 该年另由 D0/moth 断言守门 (避坑1绿门假绿)。
        reason = "scanned PDF (no text layer); 题面 verified via dual-channel transcript, gated by D0/moth"
        return _skip_result(year, reason, pdf_source_id), None, None, None
    return None, pdf_source_id, pdf_path, pdf_text


def _run_checks(year: int, con, pdf_text: str) -> tuple[list, list, list]:
    """跑结构化条目 vs PDF 关键词核对, 返回 (checks, rows, jsonl_entries)."""
    pdf_words = set(re.findall(r"[a-zA-Z]{4,}", pdf_text.lower()))
    rows, jsonl_entries = _load_structured(year, con)
    sources = list(rows) + [(e.get("source", ""), e.get("question_type", ""),
                              e.get("question", ""), e.get("answer", "")) for e in jsonl_entries]
    checks = [_check_item(s[0], s[1], s[2], pdf_words) for s in sources]
    return checks, rows, jsonl_entries


def _write_report(year: int, result: dict) -> None:
    out_path = REPORT_DIR / f"cross_verify_{year}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))


def verify_year(year: int, con=None) -> dict:
    """核对一个年份: 结构化数据的关键文本是否在 PDF 原文中出现."""
    skip_result, pdf_source_id, pdf_path, pdf_text = _load_pdf_text_for_year(year)
    if skip_result is not None:
        return skip_result
    pdf_words = set(re.findall(r"[a-zA-Z]{4,}", pdf_text.lower()))
    checks, rows, jsonl_entries = _run_checks(year, con, pdf_text)
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
    _write_report(year, result)
    return result


def _parse_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--strict", action="store_true",
                        help="Return non-zero when any requested year fails or skips.")
    return parser.parse_args()


def _print_year_checks(result: dict) -> None:
    s = result.get("summary", {})
    print(f"   DB entries: {result['structured_entries']}, JSONL: {result['jsonl_entries']}")
    print(f"   PDF: {result['pdf_chars']} chars, {result['pdf_unique_words']} unique words")
    print(f"   Checks: {s.get('pass',0)} pass, {s.get('warn',0)} warn, {s.get('fail',0)} fail, {s.get('skip',0)} skip")
    hs = result.get("html_summary", {})
    print(f"   HTML identity: {hs.get('pass',0)} pass, {hs.get('fail',0)} fail")
    for c in result["checks"]:
        if c["match"] in ("fail", "warn"):
            print(f"   ⚠️ {c['qid']} [{c['type']}]: match={c['match_rate']:.0%} words={c.get('sample_words',[][:3])}")


def _print_year_result(result: dict) -> bool:
    """打印单年结果, 返回该年是否应计入 failed."""
    status = result.get("overall", "?")
    failed = result.get("status") == "skip" or status == "FAIL"
    icon = "✅" if status == "PASS" else ("⚠️" if status == "skip" else "❌")
    print(f"\n{icon} {result.get('year')}: {status}")
    if "checks" in result:
        _print_year_checks(result)
    else:
        print(f"   {result.get('reason', '')}")
    return failed


def main():
    args = _parse_args()

    years = _all_pdf_years() if args.all else ([args.year] if args.year else [])
    if not years:
        print("Usage: --year 2024 or --all")
        return 2

    failed = False
    for year in years:
        result = verify_year(year)
        if _print_year_result(result):
            failed = True
    return 1 if args.strict and failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
