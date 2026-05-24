"""课标语法项目表 (附录 3, p187-191) 抽取 — 从 scripts/extract_curriculum.py 拆出 (4.5).

减 extract_grammar_items CC 35 → ≤ 10.
"""
from __future__ import annotations

import re

from pypdf import PdfReader

# 五种行型 → (depth, normalized_token)
RE_L1 = re.compile(r"^([一二三四五六七八九十]+)、(.+?)(\*+)?$")
RE_L2 = re.compile(r"^(\d+)\.\s*(.+?)(\*+)?$")
RE_L3 = re.compile(r"^[（(](\d+)[)）]\s*(.+?)(\*+)?$")
RE_L4 = re.compile(r"^([a-z])\.\s*(.+?)(\*+)?$")


def _level_of(suffix: str) -> str:
    if suffix.startswith("***"): return "选修"
    if suffix.startswith("**"): return "选必"
    if suffix.startswith("*"): return "必修"
    return "义教"


def _skip_line(line: str) -> bool:
    if not line: return True
    if line.startswith("│") or line.isdigit(): return True
    if line.startswith("附录") or "语法项目" in line: return True
    if line.startswith("说明") or line.startswith("普通高中"): return True
    if not line.strip(): return True
    # 跳过例句 (英文字母占比高)
    ratio = sum(ch.isascii() and ch.isalpha() for ch in line) / max(1, len(line.replace(" ", "")))
    return ratio > 0.4


def _emit_node(state: dict, depth: int, num: str, label: str, suffix: str,
                parent_path: str, source_tag: str) -> dict:
    path = parent_path + "/" + num if parent_path else num
    state["current"][depth] = path
    for k in range(depth + 1, 5):
        state["current"][k] = None
    state["seq"] += 1
    return {
        "grammar_item_id": path, "depth": depth,
        "parent_id": parent_path or None,
        "category": state["current"][1] and state["current"][1].split("/")[0],
        "label": label.strip().rstrip("：:"),
        "cefr_level": _level_of(suffix),
        "seq": state["seq"], "source": source_tag,
    }


def _try_match(state: dict, line: str, source_tag: str) -> dict | None:
    m1 = RE_L1.match(line)
    if m1:
        return _emit_node(state, 1, m1.group(1), m1.group(2), m1.group(3) or "", "", source_tag)
    m2 = RE_L2.match(line)
    if m2:
        return _emit_node(state, 2, m2.group(1), m2.group(2), m2.group(3) or "",
                            state["current"][1] or "", source_tag)
    m3 = RE_L3.match(line)
    if m3:
        parent = state["current"][2] or state["current"][1] or ""
        return _emit_node(state, 3, f"({m3.group(1)})", m3.group(2),
                            m3.group(3) or "", parent, source_tag)
    m4 = RE_L4.match(line)
    if m4:
        parent = state["current"][3] or state["current"][2] or state["current"][1] or ""
        return _emit_node(state, 4, m4.group(1), m4.group(2), m4.group(3) or "", parent, source_tag)
    return None


def extract_grammar_items(reader: PdfReader, source_tag: str,
                            start_page: int = 187, end_page: int = 192) -> list[dict]:
    """主入口 — 简化为 3 层调用, CC ≤ 6."""
    state = {"current": {1: None, 2: None, 3: None, 4: None}, "seq": 0}
    rows: list[dict] = []
    for pi in range(start_page - 1, end_page):
        if pi >= len(reader.pages): break
        text = reader.pages[pi].extract_text() or ""
        for raw in text.split("\n"):
            line = raw.strip()
            if _skip_line(line): continue
            row = _try_match(state, line, source_tag)
            if row: rows.append(row)
    return rows
