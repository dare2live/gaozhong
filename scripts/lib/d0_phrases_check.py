"""D0 phrases 句型语义正确性校验 (A1 修, 坑17 盲区: phrases 表此前零 D0 覆盖).

sentence_pattern 原 regex 用 .* + DOTALL 跨段贪婪 → such as/so that/形式主语 误命中(32%污染, 进 lesson_plan 老师可见)。
锁: (a) 每 sentence_pattern evidence 必过其 canonical 对应正则(结构自洽, 防跨段误命中回归);
    (b) 0 such-as / so-that(目的状语) bleed 进 sentence_pattern。
verb_phrase/function 是字面子串(已验0误命中), 不查。check 由调用方传入, 只读。
"""
from __future__ import annotations

import re

import duckdb

from backend.services.extraction.phrases import PATTERN_RE


def check_phrases(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (32) phrases 句型语义正确性 (A1: regex 误命中防回归, 坑17盲区补 D0) ===")
    rows = con.execute(
        "SELECT canonical, evidence FROM phrases WHERE phrase_type='sentence_pattern'").fetchall()
    # (a) 每 evidence 过其 canonical 正则 (evidence=匹配span, 应 100% 重配; 跨段贪婪会重配失败)
    no_re = [c for c, _ in rows if c not in PATTERN_RE]
    bad_match = [(c, (e or "")[:40]) for c, e in rows
                 if c in PATTERN_RE and not re.search(PATTERN_RE[c], e or "", re.IGNORECASE)]
    check("sentence_pattern canonical 全有对应正则 (无野标签)", not no_re, f"无正则={set(no_re)}")
    check("每 sentence_pattern evidence 过其正则 (结构自洽, 防跨段误命中)", not bad_match, f"{len(bad_match)}行重配失败 {bad_match[:3]}")
    # (b) 0 such as / so that 误命中残留
    bleed = con.execute(
        "SELECT COUNT(*) FROM phrases WHERE phrase_type='sentence_pattern' AND ("
        "regexp_matches(evidence, '\\bsuch\\s+\\w+\\s+as\\b') OR regexp_matches(evidence, '\\bso that\\b'))"
    ).fetchone()[0]
    check("sentence_pattern 无 such-as/so-that(目的) 误命中残留", bleed == 0, f"{bleed} 行残留")
