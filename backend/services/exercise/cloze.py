"""完形填空合成器 (规则版, 不调 LLM) — 第二阶段题型扩展.

策略:
  1. 从 section_text (kind=Reading, 长度足) 取一篇
  2. 在前 200-400 字符范围内, 每 25-40 字符遮蔽 1 个高频实词 (避免停用词)
  3. 干扰项: 同 cefr_level 同 pos 其他词
  4. 控制题量 (一篇 8-15 空)
"""
from __future__ import annotations

import random
import re
from collections import Counter

import duckdb

_TOKEN_RE = re.compile(r"\b[A-Za-z][A-Za-z'\-]+\b")
STOPWORDS = {
    "the","a","an","of","to","in","on","at","for","with","by","is","are","was","were",
    "be","been","being","am","do","does","did","done","have","has","had","will","would",
    "can","could","may","might","must","not","no","this","that","these","those","it","its",
    "he","she","they","them","we","you","i","me","my","your","our","what","when","where",
    "why","how","which","who","from","into","up","down","out","over","under","about","also",
    "very","too","much","many","some","any","all","each","every","other","such","same",
    "and","or","but","if","so","as","than","then","because","although","though","while",
}


def _pick_blank_candidates(text: str, n_blanks: int = 10) -> list[tuple[int, str]]:
    """Pick non-stopword tokens spaced apart in text. Return [(char_offset, word), ...]."""
    matches = [(m.start(), m.group()) for m in _TOKEN_RE.finditer(text)
               if m.group().lower() not in STOPWORDS and len(m.group()) >= 4]
    if len(matches) <= n_blanks:
        return matches
    # evenly space
    step = len(matches) / n_blanks
    return [matches[int(i * step)] for i in range(n_blanks)]


def _distractor_pool(con: duckdb.DuckDBPyConnection, target_word: str) -> list[str]:
    """3 同长度/同首字母/同级别词."""
    rows = con.execute("""
        SELECT word FROM cefr_vocab
        WHERE word != ?
          AND LENGTH(word) BETWEEN ? AND ?
          AND cefr_level IN ('义教', '必修')
        LIMIT 100
    """, [target_word.lower(), max(3, len(target_word) - 1), len(target_word) + 2]).fetchall()
    return [r[0] for r in rows]


def generate_cloze(con: duckdb.DuckDBPyConnection, unit_id: str | None = None,
                   n_blanks: int = 10, seed: int | None = None) -> dict:
    """Generate cloze test from a section_text (Reading kind preferred)."""
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
        WHERE s.kind = 'Reading' AND st.n_chars BETWEEN 800 AND 5000
          AND {where}
        ORDER BY RANDOM() LIMIT 1
    """, args).fetchall()
    if not rows:
        return {"error": "no suitable Reading section", "unit_id": unit_id}
    ver, vol, un, seq, text = rows[0]
    # take first 1500 chars
    passage = text[:2000].replace("\n", " ").strip()
    blanks = _pick_blank_candidates(passage, n_blanks=n_blanks)
    if not blanks:
        return {"error": "no blank candidates"}
    questions = []
    chunks: list[str] = []
    last = 0
    for i, (offset, word) in enumerate(blanks):
        chunks.append(passage[last:offset])
        chunks.append(f"___{i+1}___")
        last = offset + len(word)
        # build options
        distractors = _distractor_pool(con, word)
        rng.shuffle(distractors)
        d3 = distractors[:3]
        if len(d3) < 3:
            continue
        opts = [word] + d3
        rng.shuffle(opts)
        answer_idx = opts.index(word)
        questions.append({
            "seq": i + 1, "blank_marker": f"___{i+1}___",
            "options": [{"label": chr(65 + k), "text": o} for k, o in enumerate(opts)],
            "answer": chr(65 + answer_idx),
            "evidence_word": word,
        })
    chunks.append(passage[last:])
    return {
        "paper_level": "L2_cloze",
        "scope": f"unit:{ver}/{vol}/U{un}/section_{seq}",
        "passage_with_blanks": "".join(chunks),
        "n_blanks": len(questions),
        "questions": questions,
    }
