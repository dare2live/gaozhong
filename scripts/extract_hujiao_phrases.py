"""沪教牛津(广深沈) 初中英语 6册 短语/句型/表达 抽取 — 补 STEP1 缺口(2026-07-07 用户要求).

背景: senior_knowledge.py::phrase_pattern_exam_relevance 此前明确标注"短语/搭配/句式无
初中基线"(STEP1数据缺口, 调研1实证 phrases 表100%高中来源)。用户指出教材 PDF 原文其实
本地已有(data/junior_high/textbooks/hujiao/{7a..9b}.pdf), 要求补齐 —— 之前调研没找全
本地文件是真实疏漏, 不是数据真不存在。

方法(颗粒度对齐高中, 单一计算点, 2026-07-07 二次收口): 读 scripts/extract_hujiao_sections.py
产出的 hujiao_section_text.jsonl(不再自己重新用 pdfplumber 扫 PDF —— 避免同一份 PDF 存在
两条独立文本抽取管线, Rule1 单一计算点), 复用
backend.services.extraction.phrases._scan_text(高中短语/句型/表达扫描器, 规则版, 不调
LLM) 逐 section 扫描, 同一份 VERB_PHRASES/PATTERNS/FUNCTIONS 词表, 高中初中用同一把尺子量
——完全对应高中 extract_phrases() 读 section_text 表的做法(见该函数)。

前置: 必须先跑 scripts/extract_hujiao_sections.py 生成 hujiao_section_text.jsonl。

产物: data/junior_high/structured/hujiao_phrases.jsonl (同 hujiao_vocab.jsonl 等既有
产物模式)。DB 加载见 backend/services/data_sources/extract/junior/phrases.py::load(),
写入**已有** phrases 表(不新建表), version_key='hujiao', 与高中 renjiao/waiyan 数据物理
共存于同一张表, 靠 version_key 区分学段来源。
"""
from __future__ import annotations

import json
from pathlib import Path

from backend.services.extraction.phrases import _scan_text

ROOT = Path(__file__).resolve().parent.parent
STRUCTURED = ROOT / "data" / "junior_high" / "structured"
SECTION_TEXT_SRC = STRUCTURED / "hujiao_section_text.jsonl"
OUT = STRUCTURED / "hujiao_phrases.jsonl"


def _iter_sections() -> list[dict]:
    if not SECTION_TEXT_SRC.exists():
        raise FileNotFoundError(
            f"{SECTION_TEXT_SRC} 不存在, 请先跑 python3 scripts/extract_hujiao_sections.py"
        )
    return [json.loads(line) for line in SECTION_TEXT_SRC.open(encoding="utf-8")]


def extract_all() -> list[tuple]:
    """[(volume_key, unit_number, canonical, phrase_type, evidence)]."""
    rows: list[tuple] = []
    seen: set[tuple] = set()
    for sec in _iter_sections():
        vol, unit, text = sec["volume_key"], sec["unit_number"], sec["raw_text"]
        if not text.strip():
            continue
        for canonical, ptype, ev in _scan_text(text):
            key = (vol, unit, canonical, ptype)
            if key in seen:
                continue
            seen.add(key)
            rows.append((vol, unit, canonical, ptype, ev))
    return rows


def write_jsonl() -> dict:
    by_type: dict[str, int] = {}
    by_volume: dict[str, int] = {}
    n = 0
    with OUT.open("w", encoding="utf-8") as f:
        for vol, unit, canonical, ptype, ev in extract_all():
            f.write(json.dumps(
                {"volume_key": vol, "unit_number": unit, "canonical": canonical,
                 "phrase_type": ptype, "evidence": ev},
                ensure_ascii=False) + "\n")
            n += 1
            group = ptype.split(":", 1)[0]
            by_type[group] = by_type.get(group, 0) + 1
            by_volume[vol] = by_volume.get(vol, 0) + 1
    return {"rows_written": n, "by_type": by_type, "by_volume": by_volume, "out": str(OUT)}


if __name__ == "__main__":
    print(write_jsonl())
