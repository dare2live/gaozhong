"""沪教牛津(广深沈) 初中英语 6册 短语/句型/表达 抽取 — 补 STEP1 缺口(2026-07-07 用户要求).

背景: senior_knowledge.py::phrase_pattern_exam_relevance 此前明确标注"短语/搭配/句式无
初中基线"(STEP1数据缺口, 调研1实证 phrases 表100%高中来源)。用户指出教材 PDF 原文其实
本地已有(data/junior_high/textbooks/hujiao/{7a..9b}.pdf), 要求补齐 —— 之前调研没找全
本地文件是真实疏漏, 不是数据真不存在。

方法(颗粒度对齐高中, 单一计算点): 直接复用 backend.services.extraction.phrases._scan_text
(高中短语/句型/表达扫描器, 规则版, 不调 LLM) 逐页扫描英文正文, **不重新发明一套抽取规则**——
同一份 VERB_PHRASES/PATTERNS/FUNCTIONS 词表, 同一套匹配逻辑, 高中初中用同一把尺子量。

PDF 文本层已知问题(与 extract_hujiao_vocab.py 同源 PDF, 见 textbook_manifest.jsonl
text_layer="InDesign乱码,待OCR"): CID 乱码集中在表格/挖空练习(comprehension worksheet
的下划线填空/表格式 Name:___ 这类版式), 阅读课文/对话正文(短语最可能出现的地方)实测清晰
可读(83-138页/72-138页 无cid标记, 见开发时人工抽样验证)。乱码页的短语命中会静默漏检
(小写子串/正则匹配不上乱码), 不会误判——安全的错误方向(宁缺毋滥)。

unit 追踪: 页眉页脚"Unit N"逐页复现, 顺序扫描页面时维护"当前 unit"状态, 命中即打当前
unit(不需要精确切分段落归属, 同高中 section_text 的 unit_number 颗粒度一致)。

产物: data/junior_high/structured/hujiao_phrases.jsonl (同 hujiao_vocab.jsonl 等既有
产物模式 —— PDF 抽取是慢+脆的一次性预处理, 结构化 jsonl 提交入库; init_db 只做 jsonl→DB
的快速确定性加载, 不在每次重建时重跑 pdfplumber)。DB 加载见
backend/services/data_sources/extract/junior/phrases.py::load(), 写入**已有** phrases
表(不新建表), version_key='hujiao', volume_key∈{7a,7b,8a,8b,9a,9b}, 与高中 renjiao/
waiyan 数据物理共存于同一张表, 靠 version_key 区分学段来源 —— 这样
senior_knowledge.py 只需按 version_key 分组就能算"初中已学 vs 高中新学"(不必新增
at_stage 边或新表, Rule2 Canonical First 已有的 phrases 表本身就是 canonical)。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pdfplumber

from backend.services.extraction.phrases import _scan_text

ROOT = Path(__file__).resolve().parent.parent
TB = ROOT / "data" / "junior_high" / "textbooks" / "hujiao"
OUT = ROOT / "data" / "junior_high" / "structured" / "hujiao_phrases.jsonl"
VOLUMES = ("7a", "7b", "8a", "8b", "9a", "9b")
_UNIT_RE = re.compile(r"\bUnit\s+(\d+)\b")


def _page_texts(vol: str) -> list[str]:
    with pdfplumber.open(str(TB / f"{vol}.pdf")) as pdf:
        return [p.extract_text() or "" for p in pdf.pages]


def _unit_tagged_texts(pages: list[str]) -> list[tuple[int, str]]:
    """[(unit_number, page_text)]; unit=0 = 未进入任何 Unit 前的封面/目录页."""
    out = []
    cur = 0
    for txt in pages:
        m = _UNIT_RE.search(txt)
        if m:
            cur = int(m.group(1))
        out.append((cur, txt))
    return out


def extract_volume(vol: str) -> list[tuple]:
    """[(volume_key, unit_number, canonical, phrase_type, evidence)]."""
    rows: list[tuple] = []
    seen: set[tuple] = set()
    for unit, txt in _unit_tagged_texts(_page_texts(vol)):
        if unit == 0 or not txt.strip():
            continue
        for canonical, ptype, ev in _scan_text(txt):
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
        for vol in VOLUMES:
            for _vol, unit, canonical, ptype, ev in extract_volume(vol):
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
