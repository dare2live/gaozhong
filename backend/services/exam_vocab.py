"""词 × 真题考过状态 — **唯一计算点** (Rule 1, 用户 2026-06-16 #12/#13/#14 整改).

同一事实「某词是否/在哪些真题里考过」此前在 3 处各算且矛盾:
  - build_vocab_classification._exam_vocab (province-scoped + lemmatize, 最正确)
  - audit/exam_coverage._tokenize_exam (province-blind, 无 lemmatize) → #13
  - audit/extracurricular._exam_hits (province-aware, 无 lemmatize)
此模块收敛为唯一 tokenizer + 唯一命中计数器, 三处消费者都改读它。

§7 辽宁卷锚定: 用精确前缀 `province LIKE '辽宁%'` 区分辽宁/外省
(不用 `%辽宁%` 子串 — '...辽宁当年自主命题' 含'辽宁'子串实为外省, 见坑7否定词子串)。

**nltk WordNet 仅生成/审计期 import** (词形归并); API 运行时不经此路径。CC ≤ 10/函数。
"""
from __future__ import annotations

import re

import duckdb

_LIAONING_PREFIX = "辽宁%"   # §7 精确前缀, 非 %辽宁% 子串 (防否定词子串误命中)
_TOKEN = re.compile(r"[A-Za-z]+")
_MIN_LEN = 2


def _lemma_tokens(text: str, lemm) -> set[str]:
    """题面/词 → lemmatize token 集 (token 原形 + v-lemma + n-lemma, len≥2)."""
    out: set[str] = set()
    for t in _TOKEN.findall((text or "").lower()):
        if len(t) >= _MIN_LEN:
            out.add(t)
            out.add(lemm.lemmatize(t, "v"))
            out.add(lemm.lemmatize(t, "n"))
    return out


def word_inflections(w: str, lemm) -> set[str]:
    """词的屈折形 {w} ∪ lemmatize(w, p) for p in (v,n,a,r) — 匹配 battlefields↔battlefield."""
    return {w.lower()} | {lemm.lemmatize(w.lower(), p) for p in ("v", "n", "a", "r")}


def province_exam_token_bags(con: duckdb.DuckDBPyConnection, lemm) -> tuple[set[str], set[str]]:
    """返回 (ln_v, ws_v): 辽宁 / 外省真题 raw_question 的 lemmatize token 集 (§7 精确前缀).

    唯一 tokenizer — build_vocab_classification 等都改调它, 不再各自 re.findall。
    """
    ln_v: set[str] = set()
    ws_v: set[str] = set()
    for raw, prov in con.execute(
            "SELECT raw_question, province FROM exam_questions").fetchall():
        bag = _lemma_tokens(raw, lemm)
        (ln_v if (prov or "").startswith("辽宁") else ws_v).update(bag)
    return ln_v, ws_v


def word_exam_hits(con: duckdb.DuckDBPyConnection, words: set[str], lemm
                   ) -> dict[str, dict[str, int]]:
    """遍历 exam_questions 一次, 对每词返回 {"ln": 辽宁命中题数, "all": 全部命中题数}.

    匹配 = 词的任一屈折形 ∈ 该题 lemmatize token 集 (battlefields↔battlefield)。
    覆盖传入的全部 words (cefr+超纲); hit_count 与 tested 布尔双用 (ln>0 / all>0)。
    单一命中计数器 — exam_coverage / extracurricular 都改读它, 不再各自 tokenize。
    """
    forms = {w: word_inflections(w, lemm) for w in words}
    hits: dict[str, dict[str, int]] = {w: {"ln": 0, "all": 0} for w in words}
    for raw, prov in con.execute(
            "SELECT raw_question, province FROM exam_questions").fetchall():
        bag = _lemma_tokens(raw, lemm)
        is_ln = (prov or "").startswith("辽宁")
        for w, fset in forms.items():
            if fset & bag:
                hits[w]["all"] += 1
                if is_ln:
                    hits[w]["ln"] += 1
    return hits
