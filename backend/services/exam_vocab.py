"""词 × 真题考过状态 — **唯一计算点** (Rule 1, 用户 2026-06-16 #12/#13/#14 整改; 2026-06-17 收口到边).

「某词是否/在哪些真题里考过」的唯一真相 = **tests_word 边** (Rule 3 边一等公民):
  - 边由 links_extra.build_tests_word 建 (lemmatize + 去停用词 + classifiable=cefr∪教材词)。
  - 是唯一 tokenizer (build_tests_word 用此模块 _lemma_tokens); 唯一命中真相 (word_exam_hits_from_edges)。
  - exam_status (audit/exam_coverage) + 超纲考过档 (build_vocab_classification) 都据边推
    → 'core'/'辽宁考过' 词必有边 (core-无边=0 by construction, 杜绝 token-bag vs 边 Rule1 不一致)。

§7 辽宁卷锚定: 边 JOIN exam_questions 用精确前缀 `province LIKE '辽宁%'` 区分辽宁/外省
(不用 `%辽宁%` 子串 — 见坑7否定词子串)。**nltk WordNet 仅生成/审计期 import** (词形归并)。
"""
from __future__ import annotations

import re

import duckdb

from backend.services.stopwords import load_stopwords

_TOKEN = re.compile(r"[A-Za-z]+")
_MIN_LEN = 2


def _lemma_tokens(text: str, lemm) -> set[str]:
    """题面 → lemmatize 实词 token 集 (token 原形 + v/n-lemma, len≥2, **去停用词**).

    build_tests_word 的唯一 tokenizer — 去停用词与历史 content_tokens 同口径, 否则
    the/about/a 等功能词被当"考过"污染考点边 (坑5 停用词污染)。
    """
    stop = load_stopwords()
    out: set[str] = set()
    for t in _TOKEN.findall((text or "").lower()):
        if len(t) >= _MIN_LEN:
            for form in (t, lemm.lemmatize(t, "v"), lemm.lemmatize(t, "n")):
                if form not in stop:
                    out.add(form)
    return out


def word_inflections(w: str, lemm) -> set[str]:
    """词的屈折形 {w} ∪ lemmatize(w, p) for p in (v,n,a,r).

    用于 build_vocab_classification 判'课标屈折变形'(w 的屈折形是否在 cefr) —
    与"考过"判定无关 (考过走边)。"""
    return {w.lower()} | {lemm.lemmatize(w.lower(), p) for p in ("v", "n", "a", "r")}


def word_exam_hits_from_edges(con: duckdb.DuckDBPyConnection) -> dict[str, dict[str, int]]:
    """每词 {"ln": 辽宁命中题数, "all": 全部命中题数} — 从 tests_word 边 (唯一真相) 算.

    取代 token-bag 命中: 边是'考过'唯一真相 (Rule3), exam_status / 超纲考过档据此推 →
    'core'/'辽宁考过' 词必有边。§7 用 province LIKE '辽宁%' 精确前缀。
    """
    rows = con.execute(
        "SELECT SUBSTR(e.dst_id, 6) AS word, "
        "       SUM(CASE WHEN q.province LIKE '辽宁%' THEN 1 ELSE 0 END) AS ln, "
        "       COUNT(*) AS all_c "
        "FROM edges e JOIN exam_questions q ON q.question_id = SUBSTR(e.src_id, 10) "
        "WHERE e.relation = 'tests_word' GROUP BY 1"
    ).fetchall()
    return {w: {"ln": int(ln), "all": int(a)} for w, ln, a in rows}
