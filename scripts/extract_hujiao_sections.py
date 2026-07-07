"""沪教牛津(广深沈) 初中英语 6册 units/sections/section_text 抽取 (Phase E1, 2026-07-07).

背景: 高中已有 units→sections→section_text 三层结构(教材单元/子板块/正文, 供短语抽取+
L3课程单元定位用), 初中此前完全空白(sections=0行) —— 用户要求把高中这套方法论全深度
复刻到初中, 这是复刻的地基第一步。

页眉结构实测(6册通用, pdfplumber提取, 每页首行固定为版权水印"上海教育出版社"跳过):
  - unit 边界: 单元起始页出现连续3行 "Module N <标题>" / "Unit" / "<数字>" (跨7a/8a/9a
    抽样验证100%命中, 每册固定8个unit, 页码间隔固定); 其余页眉交替显示 "Module N"/"Unit N"。
  - section 锚点: 页眉第2/3行(跳过水印+Module/Unit行)出现 Reading/Listening/Grammar/
    Writing/Speaking/Vocabulary(常带字母前缀"C ")/Comprehension(常带"D ")/More practice/
    Study skills/Culture corner 之一, 即该页起新 section; 未命中视为上一 section 延续
    (同高中 section.py 的"非每页都重复锚点"设计)。

PDF文本层已知问题(同 extract_hujiao_phrases.py): 表格/挖空练习页 CID 乱码, 正文/锚点行
清晰可读(锚点行本身是短标签, 不受影响)。

产物: data/junior_high/structured/{hujiao_units,hujiao_sections}.jsonl (同 hujiao_vocab
等既有产物模式, DB 加载见 backend/services/data_sources/extract/junior/sections.py)。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
TB = ROOT / "data" / "junior_high" / "textbooks" / "hujiao"
OUT = ROOT / "data" / "junior_high" / "structured"
VOLUMES = ("7a", "7b", "8a", "8b", "9a", "9b")

_UNIT_OPENER_RE = re.compile(r"^Module\s+(\d+)\s*(.*)$")
_KIND_ANCHORS = [
    ("Comprehension", "Comprehension"), ("Vocabulary", "Vocabulary"),
    ("Reading", "Reading"), ("Listening", "Listening"), ("Grammar", "Grammar"),
    ("Speaking", "Speaking"), ("Writing", "Writing"),
    ("More practice", "MorePractice"), ("Study skills", "StudySkills"),
    ("Culture corner", "CultureCorner"),
]
_ANCHOR_RE = re.compile(r"^[A-Z]?\d*\s*(" + "|".join(re.escape(a) for a, _ in _KIND_ANCHORS) + r")\b")
_KIND_MAP = dict(_KIND_ANCHORS)


def _clean_lines(page_text: str) -> list[str]:
    return [ln.strip() for ln in page_text.split("\n") if ln.strip()]


def _page_lines_by_volume(vol: str) -> list[list[str]]:
    with pdfplumber.open(str(TB / f"{vol}.pdf")) as pdf:
        return [_clean_lines(p.extract_text() or "") for p in pdf.pages]


def _dedouble(s: str) -> str:
    """PDF粗体渲染偶发把字符连续输出2次(如"Module"→"MMoodduullee")。仅用于本模块内部
    "严格匹配失败后"的兜底重试, 不做全局清洗(避免误伤"book"/"add"这类真双写词)。"""
    return re.sub(r"(.)\1", r"\1", s)


def _strict_unit_opener(lines: list[str]) -> tuple[int, str] | None:
    for j in range(len(lines) - 2):
        m = _UNIT_OPENER_RE.match(lines[j])
        if m and lines[j + 1] == "Unit" and lines[j + 2].isdigit():
            return int(lines[j + 2]), m.group(2).strip()
    return None


def _fallback_unit_opener(lines: list[str]) -> tuple[int, str] | None:
    """粗体渲染乱序/字符加倍兜底(6册抽样实测2处触发): 独立"Unit"行 前后小窗口内找
    数字(顺序可能被乱序标题行打断)+ 之前的 Module 行(可能整行字符加倍需 _dedouble 复原)。
    """
    for j, ln in enumerate(lines):
        if ln != "Unit":
            continue
        window = lines[max(0, j - 1):j + 4]
        digit = next((w for w in window if w.isdigit()), None)
        if not digit:
            continue
        for cand in lines[:j]:
            m = _UNIT_OPENER_RE.match(cand) or _UNIT_OPENER_RE.match(_dedouble(cand))
            if m:
                return int(digit), m.group(2).strip()
    return None


def _find_unit_openers(pages: list[list[str]]) -> list[tuple[int, int, str]]:
    """[(page_index, unit_number, module_title)]."""
    out = []
    for i, lines in enumerate(pages):
        hit = _strict_unit_opener(lines) or _fallback_unit_opener(lines)
        if hit:
            out.append((i, hit[0], hit[1]))
    return out


def _section_anchor(lines: list[str]) -> str | None:
    for ln in lines[1:4]:
        m = _ANCHOR_RE.match(ln)
        if m:
            return _KIND_MAP[m.group(1)]
    return None


def _backmatter_start(pages: list[list[str]]) -> int:
    """全书末尾"Appendices"独立标题页(0-indexed) — 末单元 page_end 收口于此, 防止吞入
    书末词表/人名录/不规则动词表等 back-matter(坑, 6册抽样实测: 直接用 len(pages) 会连带
    30+ 页附录一起吞进末单元最后一个 section)。找不到则退回 len(pages)(诚实, 不臆造)。
    """
    for i, lines in enumerate(pages):
        if len(lines) >= 2 and lines[1] == "Appendices":
            return i
    return len(pages)


def extract_volume(vol: str) -> tuple[list[dict], list[dict]]:
    """Return (units, sections) for one volume."""
    pages = _page_lines_by_volume(vol)
    openers = _find_unit_openers(pages)
    backmatter = _backmatter_start(pages)
    units: list[dict] = []
    sections: list[dict] = []
    for k, (page_idx, unit_number, title) in enumerate(openers):
        page_start = page_idx + 1  # 1-indexed
        page_end = (openers[k + 1][0] if k + 1 < len(openers) else min(len(pages), backmatter))
        units.append({
            "volume_key": vol, "unit_number": unit_number, "title": title,
            "page_start": page_start, "page_end": page_end,
        })
        seq = 0
        cur_kind = None
        cur_start = page_start
        for pi in range(page_idx, page_end):
            anchor = _section_anchor(pages[pi])
            if anchor and anchor != cur_kind:
                if cur_kind is not None:
                    seq += 1
                    sections.append({
                        "volume_key": vol, "unit_number": unit_number, "seq": seq,
                        "kind": cur_kind, "page_start": cur_start, "page_end": pi,
                    })
                cur_kind = anchor
                cur_start = pi + 1
        if cur_kind is not None:
            seq += 1
            sections.append({
                "volume_key": vol, "unit_number": unit_number, "seq": seq,
                "kind": cur_kind, "page_start": cur_start, "page_end": page_end,
            })
    return units, sections


def _section_text(vol: str, pages: list[list[str]], sec: dict) -> str:
    lines: list[str] = []
    for pi in range(sec["page_start"] - 1, sec["page_end"]):
        if pi < len(pages):
            lines.extend(pages[pi][1:])  # skip watermark line
    return "\n".join(lines)


def _collect_all() -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    all_units: list[dict] = []
    all_sections: list[dict] = []
    section_texts: list[dict] = []
    volume_pages: list[dict] = []
    for vol in VOLUMES:
        pages = _page_lines_by_volume(vol)
        volume_pages.append({"volume_key": vol, "pdf_pages": len(pages)})
        units, sections = extract_volume(vol)
        all_units.extend(units)
        all_sections.extend(sections)
        for sec in sections:
            text = _section_text(vol, pages, sec)
            section_texts.append({
                "volume_key": vol, "unit_number": sec["unit_number"], "seq": sec["seq"],
                "raw_text": text, "n_chars": len(text),
            })
    return all_units, all_sections, section_texts, volume_pages


def _write_rows(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_jsonl() -> dict:
    all_units, all_sections, section_texts, volume_pages = _collect_all()
    _write_rows(OUT / "hujiao_units.jsonl", all_units)
    _write_rows(OUT / "hujiao_sections.jsonl", all_sections)
    _write_rows(OUT / "hujiao_section_text.jsonl", section_texts)
    _write_rows(OUT / "hujiao_textbook_pages.jsonl", volume_pages)

    by_kind: dict[str, int] = {}
    for s in all_sections:
        by_kind[s["kind"]] = by_kind.get(s["kind"], 0) + 1
    return {
        "units": len(all_units), "sections": len(all_sections),
        "units_per_volume": {v: sum(1 for u in all_units if u["volume_key"] == v) for v in VOLUMES},
        "by_kind": by_kind,
    }


if __name__ == "__main__":
    print(write_jsonl())
