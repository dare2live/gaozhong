"""语法填空合成器 (规则版) — 第二阶段题型扩展.

策略: 选 reading section 文本中的特定语法点, 遮蔽并要求填合适形式:
  - 时态: 找 -ed/-ing 形式 + 给原形要求填正确时态
  - 词形派生: 用 derive_from edges 找派生族, 给词根要求填派生
  - 介词搭配: 找介词组合 (in/on/at/of), 遮蔽
"""
from __future__ import annotations

import random
import re

import duckdb

# 简化 grammar fill: 在文本里找 derive_from cluster 的成员词遮蔽 + 给词根
_TOKEN_RE = re.compile(r"\b([A-Za-z]+(?:ed|ing|tion|ment|ness|ity|ly|able|ful))\b")


def _verb_root(word: str) -> str:
    """Naive root: strip common suffixes."""
    for sfx in ("ation","ment","ness","ity","able","ful","less","ing","ed","ly","s"):
        if word.endswith(sfx) and len(word) - len(sfx) >= 3:
            return word[:-len(sfx)]
    return word


def generate_grammar_fill(con: duckdb.DuckDBPyConnection, unit_id: str | None = None,
                           n_blanks: int = 10, seed: int | None = None) -> dict:
    """Find inflected/derived words in a section, blank them, give root as hint."""
    rng = random.Random(seed)
    where = "1=1"
    args: list = []
    if unit_id and unit_id.startswith("unit:"):
        parts = unit_id[5:].split("/")
        if len(parts) >= 3:
            where = "st.version_key=? AND st.volume_key=? AND st.unit_number=?"
            args = [parts[0], parts[1], int(parts[2].lstrip("U"))]
    rows = con.execute(f"""
        SELECT st.version_key, st.volume_key, st.unit_number, st.seq, st.raw_text
        FROM section_text st
        INNER JOIN sections s USING (version_key, volume_key, unit_number, seq)
        WHERE s.kind IN ('Reading', 'Grammar') AND st.n_chars BETWEEN 500 AND 5000
          AND {where}
        ORDER BY RANDOM() LIMIT 1
    """, args).fetchall()
    if not rows:
        return {"error": "no suitable section"}
    ver, vol, un, seq, text = rows[0]
    passage = text[:1500].replace("\n", " ").strip()
    candidates = list(_TOKEN_RE.finditer(passage))
    if not candidates:
        return {"error": "no inflected word in passage"}
    rng.shuffle(candidates)
    picked = candidates[:n_blanks]
    chunks: list[str] = []
    last = 0
    questions = []
    for i, m in enumerate(sorted(picked, key=lambda x: x.start())):
        chunks.append(passage[last:m.start()])
        word = m.group()
        root = _verb_root(word.lower())
        chunks.append(f"___({root})___")
        last = m.end()
        questions.append({
            "seq": i + 1,
            "blank_marker": f"___({root})___",
            "hint": f"原形提示: {root}",
            "answer": word,
        })
    chunks.append(passage[last:])
    return {
        "paper_level": "L2_grammar_fill",
        "scope": f"unit:{ver}/{vol}/U{un}/section_{seq}",
        "passage_with_blanks": "".join(chunks),
        "n_blanks": len(questions),
        "questions": questions,
        "note": "学生填入正确形式 (时态/词形派生)",
    }
