#!/usr/bin/env python3
"""通用 PDF 提取工具 — PDF→文本 + 高考真题按题型分段, 行为收口.

抽取来源 (行为保留):
- scripts/tools/audit/cross_verify_pdf.py: extract_pdf_text + PdfUnreadableError
  (%PDF 头校验防 HTML 伪装 + pypdf 异常转 PdfUnreadableError, §1.5 不静默)
- scripts/import_recent_exams.py: extract_text + parse_questions/_split_parts/
  _extract_between 等 PDF→题目分段逻辑

公开 API:
- PdfUnreadableError              非有效 PDF (HTML 伪装/损坏下载) 显式异常
- extract_text(pdf_path) -> str   校验 %PDF 头, pypdf 异常 → PdfUnreadableError
- parse_exam_sections(text, year) 按题型分段 (阅读/完形/语法/写作)
"""
from __future__ import annotations

import re
from pathlib import Path


class PdfUnreadableError(Exception):
    """PDF 非有效格式 (HTML 伪装/损坏下载) — 不静默吞 (§1.5), 由调用方转 skip."""


def extract_text(pdf_path: str | Path) -> str:
    """PDF → 纯文本.

    先校验 b'%PDF' 文件头, 防 HTML 伪装/损坏下载 (如反爬墙存成 .pdf) 崩溃整个流程;
    pypdf 解析异常统一转 PdfUnreadableError, 不静默吞 (§1.5).
    """
    import pypdf

    path = Path(pdf_path)
    head = path.read_bytes()[:5]
    if not head.startswith(b"%PDF"):
        raise PdfUnreadableError(
            f"{path.name} 非有效 PDF (文件头 {head!r}, 疑下载为 HTML/损坏)"
        )
    try:
        reader = pypdf.PdfReader(str(path))
        return "".join(p.extract_text() or "" for p in reader.pages)
    except Exception as e:
        raise PdfUnreadableError(f"{path.name} PDF 解析失败: {type(e).__name__}: {e}")


def parse_exam_sections(text: str, year: int) -> list[dict]:
    """按大题块分段: 阅读 A-D + 七选五 + 完形 + 语法填空 + 应用文 + 续写."""
    parts = _split_parts(text)
    sections = _parse_reading(parts["part2"], year)
    sections += _parse_language(parts["part3"], year)
    sections += _parse_writing(parts["part4"], year)
    return sections


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
            qs.append(_make_section(year, "阅读理解", block, ord(label) - ord("A") + 1))
    qiwu = _extract_between(part2, "第二节", None) or ""
    if len(qiwu) > 100:
        qs.append(_make_section(year, "完形填空(七选五/语篇)", qiwu, 36))
    return qs


def _parse_language(part3: str, year: int) -> list[dict]:
    qs = []
    cloze = _extract_between(part3, "第一节", "第二节") or part3[:2000]
    if len(cloze) > 100:
        qs.append(_make_section(year, "完形填空", cloze, 41))
    grammar = _extract_between(part3, "第二节", None) or ""
    if len(grammar) > 50:
        qs.append(_make_section(year, "语法填空", grammar, 56))
    return qs


def _parse_writing(part4: str, year: int) -> list[dict]:
    qs = []
    applied = _extract_between(part4, "第一节", "第二节") or ""
    if len(applied) > 50:
        qs.append(_make_section(year, "应用文写作", applied, 46))
    narrative = _extract_between(part4, "第二节", None) or ""
    if len(narrative) > 50:
        qs.append(_make_section(year, "续写", narrative, 47))
    return qs


def _extract_passage(text: str, label: str) -> str:
    """提取阅读理解 A/B/C/D 篇."""
    next_label = chr(ord(label) + 1) if label < "D" else None
    pattern = rf"\n{label}\n"
    m = re.search(pattern, text)
    if not m:
        pattern = rf"\n{label}\s"
        m = re.search(pattern, text)
    if not m:
        return ""
    start = m.start()
    if next_label:
        end_pattern = rf"\n{next_label}\n|\n{next_label}\s"
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


def _make_section(year: int, qtype: str, raw: str, qnum: int) -> dict:
    return {
        "question_id": f"pdf/{year}/xgkii/{qtype}/{qnum}",
        "year": year,
        "province": "辽宁 (新课标 II 卷, 2021+)",
        "paper_type": "新课标 II 卷",
        "question_type": qtype,
        "raw_question": raw[:2000],
        "answer": "",
        "analysis": "",
        "source_file": f"gaokao_pdf_{year}",
        "source_index": qnum,
        "source_repo": "local_pdf",
    }
