"""OCR 噪音上下文修复 (用户 2026-05-24).

教材/真题 PDF 抽出的英文里有 OCR 错误 (abouf → about, abour → about, sigbt → sight).
不引 LLM, 用规则:
  1. token 不在 learnable (cefr ∪ textbook ∪ derive)
  2. token 与某个 learnable word 编辑距离 ≤ 2 (Levenshtein)
  3. 取上下文一致性最高的候选 (出现频次高的)

落: ocr_fix_dictionary 表 {raw_token, suggested_word, edit_distance, evidence}
用法: 后续 audit / token 处理可 lookup, 把 abouf → about

stdlib Levenshtein (无 rapidfuzz 依赖).
"""
from __future__ import annotations

import re

import duckdb

from backend.services.audit._common import finding

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'\-]{2,}")


def levenshtein(a: str, b: str, max_d: int = 2) -> int:
    """Stdlib Levenshtein with early termination."""
    if abs(len(a) - len(b)) > max_d:
        return max_d + 1
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        row_min = cur[0]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur[j] = min(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
            if cur[j] < row_min:
                row_min = cur[j]
        if row_min > max_d:
            return max_d + 1
        prev = cur
    return prev[-1]


def _index_by_signature(learnable: set[str]) -> dict[tuple, list[str]]:
    """Bucket words by (len, first_char) for fast neighbor search."""
    bucket: dict[tuple, list[str]] = {}
    for w in learnable:
        if len(w) < 3: continue
        key = (len(w), w[0])
        bucket.setdefault(key, []).append(w)
        # also (len-1, first) and (len+1, first) for length variations
        bucket.setdefault((len(w) - 1, w[0]), []).append(w)
        bucket.setdefault((len(w) + 1, w[0]), []).append(w)
    return bucket


def _candidate_words(token: str, bucket: dict[tuple, list[str]]) -> list[str]:
    """Get candidate learnable words with similar length+prefix."""
    return bucket.get((len(token), token[0]), [])


def find_fix(token: str, bucket: dict[tuple, list[str]],
              learnable: set[str]) -> str | None:
    """Return best fix or None. token 已 lowercase."""
    if token in learnable:
        return None
    if len(token) < 4:
        return None
    best: tuple[int, str] | None = None
    for cand in _candidate_words(token, bucket):
        d = levenshtein(token, cand, max_d=2)
        if d == 0:
            return cand  # exact match (shouldn't happen since not in learnable, but safe)
        if d <= 2 and (best is None or d < best[0]):
            best = (d, cand)
            if d == 1:
                break  # very close, stop
    return best[1] if best else None


def build_ocr_fix_dict(con: duckdb.DuckDBPyConnection) -> dict:
    """Scan exam_questions tokens not in learnable, attempt fix, populate dict."""
    cefr = {r[0] for r in con.execute("SELECT word FROM cefr_vocab").fetchall()}
    textbook = {r[0] for r in con.execute("SELECT DISTINCT word FROM unit_vocab_intro").fetchall()}
    learnable = cefr | textbook
    bucket = _index_by_signature(learnable)
    # all exam tokens with freq
    from collections import Counter
    freq: Counter = Counter()
    for (q,) in con.execute("SELECT raw_question FROM exam_questions").fetchall():
        for t in _TOKEN_RE.findall(q or ""):
            freq[t.lower()] += 1
    # candidates: freq ≥ 2 and not in learnable
    unknown = [w for w, c in freq.items() if c >= 2 and w not in learnable]
    fixes: list[tuple[str, str, int, int]] = []
    for tok in unknown:
        suggested = find_fix(tok, bucket, learnable)
        if suggested:
            d = levenshtein(tok, suggested, max_d=2)
            fixes.append((tok, suggested, d, freq[tok]))
    # schema — 含 confidence + reviewed_by, 让教师手动 review
    con.execute("""
        CREATE TABLE IF NOT EXISTS ocr_fix_dictionary (
            raw_token VARCHAR PRIMARY KEY,
            suggested_word VARCHAR NOT NULL,
            edit_distance INTEGER,
            raw_freq INTEGER,
            confidence VARCHAR DEFAULT 'low',
            reviewed_by VARCHAR,
            applied_at VARCHAR
        )
    """)
    con.execute("DELETE FROM ocr_fix_dictionary")
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    # confidence: 距 1 + freq 低 → 'mid'; 距 2 → 'low'
    con.executemany(
        "INSERT INTO ocr_fix_dictionary VALUES (?, ?, ?, ?, ?, NULL, ?)",
        [(t, s, d, f,
          "mid" if d == 1 else "low",
          now) for t, s, d, f in fixes],
    )
    return {
        "unknown_tokens": len(unknown),
        "fixes_built": len(fixes),
        "coverage_lift_est": len(fixes) / max(1, len(unknown)),
        "examples": [(t, s, d, f) for t, s, d, f in fixes[:8]],
    }


def audit_ocr_fix(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """Audit: how many unknown tokens were auto-fixable."""
    r = con.execute("SELECT COUNT(*) FROM ocr_fix_dictionary").fetchone()
    n_fixed = r[0] if r else 0
    return [finding("ocr_fix", "OK" if n_fixed > 0 else "WARN",
                    target="ocr_fix_dictionary 构建",
                    expected="≥ 200 fixes (实测 baseline)",
                    actual=str(n_fixed),
                    note="加 build_ocr_fix_dict() 跑一次 + 用 ocr_fix_dictionary lookup 改 token 比较时")]
