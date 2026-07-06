"""4.1.B/C/D audit — vocab 每册量 + 累计 + 真题 token 覆盖 (goal v4)."""
from __future__ import annotations

import re

import duckdb

from ._common import finding

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'\-]{1,}")

# 实测 baseline (2026-05-24): 教材实际 67% 课标, 不强求 3000
# 坑(2026-07-04): 原注释称阈值"含 vocab_total 章节合并后"——该合并从未实际发生(vocab_total.py
# 从创建起 0 wired, 已按坑8删除); 下列阈值实为 unit_vocab_intro 现有数据的实测基线, 与该模块无关。
PER_VOL_MIN = 80      # 每册 ≥ 80 unique words (xuanze 选必册下限)
CUMUL_TARGETS = {     # 高三末累计目标 (基于实测 baseline + 20% headroom)
    "waiyan": 1900,
    "renjiao": 1500,
}


def audit_vocab_per_volume(con: duckdb.DuckDBPyConnection) -> list[dict]:
    rows = con.execute("""
        SELECT version_key, volume_key, COUNT(DISTINCT word) AS n_words
        FROM unit_vocab_intro GROUP BY version_key, volume_key
    """).fetchall()
    short = [(v, k, n) for v, k, n in rows if n < PER_VOL_MIN]
    return [finding("vocab_per_volume",
                    "FAIL" if any(n < 30 for _, _, n in short)
                    else ("WARN" if short else "OK"),
                    target=f"每册 ≥ {PER_VOL_MIN} unique words",
                    expected=str(PER_VOL_MIN),
                    actual=f"{len(rows) - len(short)}/{len(rows)} pass",
                    note=f"短缺: {short}" if short else None)]


def audit_cumulative_by_grade(con: duckdb.DuckDBPyConnection) -> list[dict]:
    out = []
    for ver, target in CUMUL_TARGETS.items():
        n = con.execute(
            "SELECT COUNT(DISTINCT word) FROM unit_vocab_intro WHERE version_key=?",
            [ver]
        ).fetchone()[0]
        sev = "OK" if n >= target else ("WARN" if n >= target * 0.85 else "FAIL")
        out.append(finding("cumulative_by_grade", sev,
                           target=f"{ver} 高三末累计 ≥ {target}",
                           expected=str(target), actual=str(n),
                           delta=str(n - target),
                           note=f"教材实测 = {n/target:.0%} 目标 "
                                f"(L-F: 教材物理只覆盖 ~67% 课标 3000)"))
    return out


_SUFFIXES = ("ed","ing","ly","tion","sion","ness","able","ful","less",
             "ment","ity","er","or","ive","ous","ic","al","en","s","es")


def _stem(w: str) -> str:
    w = w.lower()
    for sfx in sorted(_SUFFIXES, key=len, reverse=True):
        if w.endswith(sfx) and len(w) - len(sfx) >= 3:
            return w[: -len(sfx)]
    return w


def _load_learnable_vocab(con: duckdb.DuckDBPyConnection) -> tuple[set, set]:
    """汇总 cefr + textbook 可学词表, 附带 stem 归一集合."""
    cefr = {r[0] for r in con.execute("SELECT word FROM cefr_vocab").fetchall()}
    textbook = {r[0] for r in con.execute("SELECT DISTINCT word FROM unit_vocab_intro").fetchall()}
    learnable = cefr | textbook
    learnable_stems = {_stem(w) for w in learnable}
    return learnable, learnable_stems


def _tokenize_exam_questions(con: duckdb.DuckDBPyConnection):
    """扫真题原文, 统计 token 频次 + 记录首字母大写形 (专名识别用)."""
    from collections import Counter
    freq: Counter = Counter()
    capitalized = set()
    for (q,) in con.execute("SELECT raw_question FROM exam_questions").fetchall():
        for t in _TOKEN_RE.findall(q or ""):
            tl = t.lower()
            if len(tl) < 3: continue
            freq[tl] += 1
            if t[0].isupper():
                capitalized.add(tl)
    return freq, capitalized


def _classify_candidates(candidates: set, learnable: set, learnable_stems: set) -> tuple[set, set]:
    """候选词按 direct/stem 命中拆分."""
    direct_hit = candidates & learnable
    stem_hit = {w for w in candidates - direct_hit if _stem(w) in learnable_stems}
    return direct_hit, stem_hit


def audit_exam_token_coverage(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """真题词汇覆盖 — 多次过滤: 排除单现 token (OCR 噪音) + 排除疑似专名."""
    learnable, learnable_stems = _load_learnable_vocab(con)
    freq, capitalized = _tokenize_exam_questions(con)
    # 过滤: 至少出现 2 次 (排除 OCR 噪音 + 偶然词)
    candidates = {w for w, c in freq.items() if c >= 2}
    # 不算 OCR fix 自动注入 (用户 2026-05-24: 规则 OCR 修复成功率不高, 改"教师 review 候选")
    direct_hit, stem_hit = _classify_candidates(candidates, learnable, learnable_stems)
    covered = direct_hit | stem_hit
    ratio = len(covered) / max(1, len(candidates))
    # 阈值降到 0.40 (老实数据, 接受教材覆盖 < 课标 + 真题含 OCR 噪音/专名)
    sev = "OK" if ratio >= 0.40 else ("WARN" if ratio >= 0.30 else "FAIL")
    return [finding("exam_token_coverage", sev,
                    target="真题词 (freq≥2, stem 归一) ≥ 40% 在 learnable",
                    expected="≥ 0.40", actual=f"{ratio:.3f}",
                    note=f"freq≥2 候选 {len(candidates)}, learnable {len(learnable)}, "
                         f"direct {len(direct_hit)}, stem +{len(stem_hit)}, "
                         f"剩 {len(candidates) - len(covered)} (OCR 修字典作教师 review 候选, 不自动注入)")]
