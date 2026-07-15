"""结构 L2 分类: analysis → curated → discourse_slot → fallback 句际衔接.

永不返回 unknown (用户要求全覆盖; fallback 仍属官方「理解文章结构类型」下衔接功能).
"""
from __future__ import annotations

import ast
import json
import re
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
_SUBTYPES = ROOT / "backend" / "config" / "cognitive_structure_subtypes.yaml"
_CURATED = ROOT / "data" / "structured" / "exam_point" / "cognitive_structure_subtype_labels.jsonl"


@lru_cache(maxsize=1)
def _cfg() -> dict:
    return yaml.safe_load(_SUBTYPES.read_text(encoding="utf-8")) or {}


@lru_cache(maxsize=1)
def _analysis_rules() -> list[tuple[str, list[re.Pattern]]]:
    out = []
    for st in _cfg().get("subtypes") or []:
        pats = [re.compile(p) for p in (st.get("analysis_any") or [])]
        out.append((st["id"], pats))
    return out


@lru_cache(maxsize=1)
def curated_subtypes() -> dict[str, dict]:
    if not _CURATED.exists():
        return {}
    out = {}
    for ln in _CURATED.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            row = json.loads(ln)
            out[row["src_id"]] = row
    return out


def classify_structure_subtype(
    analysis_snip: str | None,
    *,
    src_id: str | None = None,
    passage: str | None = None,
    blank_no: int | None = None,
) -> tuple[str, str, str]:
    """(subtype, rule, method). method∈analysis_explicit|curated_passage|discourse_slot|fallback_cohesion."""
    text = (analysis_snip or "").strip()
    if text:
        for sid, pats in _analysis_rules():
            for p in pats:
                if p.search(text):
                    return sid, p.pattern, "analysis_explicit"
    if src_id and src_id in curated_subtypes():
        cur = curated_subtypes()[src_id]
        return cur["subtype"], cur.get("note") or "curated", "curated_passage"
    slot = discourse_slot(passage or "", blank_no)
    if slot:
        return slot[0], slot[1], "discourse_slot"
    fb = _cfg().get("fallback_subtype") or "句际衔接"
    return fb, "fallback:句际衔接(选句填空默认衔接)", "fallback_cohesion"


def _blank_pos(passage: str, blank_no: int) -> int:
    for pat in (rf"_{{2,}}\s*{blank_no}\s*_{{2,}}", rf"●\s*.{{0,6}}{blank_no}", rf"(?<!\d){blank_no}(?!\d)"):
        m = re.search(pat, passage)
        if m:
            return m.start()
    return -1


def discourse_slot(passage: str, blank_no: int | None) -> tuple[str, str] | None:
    if not passage or blank_no is None:
        return None
    pos = _blank_pos(passage, blank_no)
    if pos < 0:
        return None
    left = passage[max(0, pos - 80):pos]
    line_end = passage.find("\n", pos)
    line = passage[passage.rfind("\n", 0, pos) + 1: line_end if line_end >= 0 else pos + 60]
    if "●" in line and len(line.strip()) < 48:
        return "主题句", "discourse:heading_blank"
    if pos < len(passage) * 0.2 and ("?" in left or "？" in left):
        return "承上启下", "discourse:opening_bridge"
    nxt = re.search(r"\n\s*\n|●", passage[pos + 4:])
    if nxt and nxt.start() < 28:
        return "段旨收束", "discourse:para_final"
    if re.search(r"●\s*$", left[-8:]) or re.search(r"\n\s*\n\s*$", left[-12:]):
        return "主题句", "discourse:para_initial"
    if re.search(r"[.!?。]\s*$", left[-24:]):
        return "逻辑推进", "discourse:para_medial"
    return "句际衔接", "discourse:local_cohesion"


def parse_option_letters(answer: str | None) -> list[str]:
    a = (answer or "").strip()
    if re.fullmatch(r"[A-G]", a):
        return [a]
    if a.startswith("["):
        try:
            vals = ast.literal_eval(a)
            if isinstance(vals, (list, tuple)):
                return [str(v).strip() for v in vals]
        except (SyntaxError, ValueError):
            pass
    return re.findall(r"(?:\d+[．.]?\s*)?([A-G])\b", a)


def blank_src_ids(qid: str, answer: str | None, blank_nos: tuple[int, ...] = (36, 37, 38, 39, 40)
                  ) -> list[tuple[str, int, str | None]]:
    letters = parse_option_letters(answer)
    m = re.search(r"/(\d+)$", qid)
    trail = int(m.group(1)) if m else None
    if len(letters) == 1 and trail in blank_nos:
        return [(qid, trail, letters[0])]
    if len(letters) == len(blank_nos):
        return [(f"{qid}#q{no}", no, letters[i]) for i, no in enumerate(blank_nos)]
    raise ValueError(f"选句填空无法展开: qid={qid!r} answer={answer!r}")


def extract_blank_analysis(analysis: str | None) -> dict[int, str]:
    an = analysis or ""
    out: dict[int, str] = {}
    for m in re.finditer(r"【(\d{1,2})题详解】\s*(.*?)(?=【\d{1,2}题详解】|\Z)", an, re.S):
        out[int(m.group(1))] = re.sub(r"\s+", " ", m.group(2)).strip()
    if not out:
        for m in re.finditer(r"(?m)^(\d{2})[.．]\s*[A-G][.．]?\s*(.+?)(?=^\d{2}[.．]|\Z)", an, re.S):
            n = int(m.group(1))
            if 36 <= n <= 40:
                out[n] = re.sub(r"\s+", " ", m.group(2)).strip()
    if not out:
        for m in re.finditer(r"(\d{2})[.．]\s*[A-G][.．]?\s*([^0-9【]{8,280})", an):
            n = int(m.group(1))
            if 36 <= n <= 40:
                out.setdefault(n, re.sub(r"\s+", " ", m.group(2)).strip())
    if not out:
        parts = list(re.finditer(r"[（(](\d)[）)]\s*(.*?)(?=[（(]\d[）)]|\Z)", an, re.S))
        if len(parts) >= 4:
            for i, m in enumerate(parts[:5]):
                out[36 + i] = re.sub(r"\s+", " ", m.group(2)).strip()
    return out
