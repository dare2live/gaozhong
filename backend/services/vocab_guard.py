"""超纲词管理模块 (全局复用).

功能:
  1. 给定 layer + 文本 → 返回超纲词列表 (含变形检测)
  2. 给定 word → 返回属于哪个年级 (G1/G2/G3/G_FINAL/未收录)
  3. 给定课程 id → 校验 enriched content 是否全部达标
  4. API 接口: /api/vocab/check + /api/vocab/word_info

前端用途:
  - 教案编辑时实时检查超纲
  - 错题分析时标注知识点年级
  - 知识图谱中显示词汇层级
"""
from __future__ import annotations

import re
from functools import lru_cache

import duckdb

from .course.lexicon_filter import (
    allowed_words_for, expand_morphology, word_position,
    IRREGULAR_FORMS, YEAR_TO_LAYERS, _STOP_WORDS,
)


def check_text(con: duckdb.DuckDBPyConnection, text: str, layer: str) -> dict:
    """检查文本中的超纲词. 返 {ok, beyond_words, total_words, layer}."""
    allowed = allowed_words_for(con, layer)
    expanded = expand_morphology(allowed)
    # 二次展开: 对 expanded 中的词再做一轮 prefix 展开 (un-/dis-/re-/in-/im-)
    prefix_expanded = set(expanded)
    for w in allowed:
        for pfx in ("un","dis","re","in","im","ir","il","mis","over","out","non"):
            prefix_expanded.add(pfx + w)
    all_ok = frozenset(prefix_expanded) | _STOP_WORDS | _NON_VOCAB_TERMS

    content_words = set(re.findall(r"\b[a-z]{3,}\b", text.lower()))
    beyond = sorted(content_words - all_ok)
    return {
        "ok": len(beyond) == 0,
        "beyond_words": beyond,
        "beyond_count": len(beyond),
        "total_words": len(content_words),
        "layer": layer,
    }


def word_info(con: duckdb.DuckDBPyConnection, word: str) -> dict:
    """查询单个词的年级归属 + 教材位置. 前端 tooltip / 知识图谱用."""
    w = word.lower().strip()
    pos = word_position(con, w)
    if pos:
        year, position = pos
        layer = _year_to_first_layer(year)
        return {
            "word": w, "found": True,
            "year_level": year, "layer": layer,
            "textbook_position": position,
            "label": f"{layer} (Y{year})",
        }
    # 检查是否是已知词的变形
    base = _find_base_form(w, con)
    if base:
        pos2 = word_position(con, base)
        year = pos2[0] if pos2 else 0
        layer = _year_to_first_layer(year) if pos2 else "未收录"
        return {
            "word": w, "found": True, "is_variant": True,
            "base_form": base,
            "year_level": year, "layer": layer,
            "textbook_position": pos2[1] if pos2 else None,
            "label": f"{layer} (Y{year}, 变形←{base})",
        }
    return {
        "word": w, "found": False,
        "year_level": None, "layer": "未收录",
        "textbook_position": None,
        "label": "未收录 (超纲)",
    }


def batch_word_info(con: duckdb.DuckDBPyConnection, words: list[str]) -> list[dict]:
    """批量查询, 前端一次性标注用."""
    return [word_info(con, w) for w in words]


def _year_to_first_layer(year: int) -> str:
    layers = YEAR_TO_LAYERS.get(year, [])
    return layers[0] if layers else "G_FINAL"


def _find_base_form(word: str, con: duckdb.DuckDBPyConnection) -> str | None:
    """尝试还原词的 base form (用于变形词的年级归属)."""
    # 不规则反查
    for base, forms in IRREGULAR_FORMS.items():
        if word in forms:
            pos = word_position(con, base)
            if pos:
                return base
    # 规则后缀剥离
    for suffix, repls in _SUFFIX_RULES:
        if word.endswith(suffix):
            for repl in repls:
                base = word[:-len(suffix)] + repl
                if len(base) > 2:
                    pos = word_position(con, base)
                    if pos:
                        return base
    return None


_SUFFIX_RULES = [
    ("ing", ["", "e"]),
    ("ting", ["t"]), ("ning", ["n"]), ("ding", ["d"]),
    ("ling", ["l"]), ("ping", ["p"]), ("ming", ["m"]),
    ("ed", ["", "e"]),
    ("ied", ["y"]),
    ("s", [""]), ("es", ["", "e"]), ("ies", ["y"]),
    ("er", ["", "e"]), ("est", ["", "e"]),
    ("ier", ["y"]), ("iest", ["y"]),
    ("ly", [""]), ("ily", ["y"]), ("ally", ["al"]),
    ("ness", [""]), ("ful", [""]), ("less", [""]),
    ("ment", [""]), ("tion", ["t", "te", ""]),
    ("sion", ["d", "de", ""]),
    ("able", ["", "e"]), ("ible", ["", "e"]),
    ("ive", ["", "e"]), ("ous", ["", "e"]),
    ("ence", ["ent"]), ("ance", ["ant"]),
    ("ity", ["", "e"]),
    ("al", ["", "e"]),
    ("ers", [""]), ("ors", [""]),
]

# 非词汇项 (语法术语/专有名词/考试用语/缩写), 不参与超纲检测
_NON_VOCAB_TERMS = frozenset({
    # 语法术语
    "adj","adv","noun","verb","pronoun","preposition",
    "conjunction","subjunctive","inversion","clause","tense",
    "participle","gerund","infinitive","superlative","comparative",
    "countable","uncountable","singular","plural","passive","active",
    "determiners","demonstrative","antonym","synonym","collocation",
    "prefix","suffix","etymology","morphology","phonetic",
    "cleft","cloze","narrative","mini","scan","simulate",
    # 考试用语
    "gaokao","sth","sb","etc","vs","min","max","avg","pdf","url","gps",
    # 常见不可避免的教学用词
    "hua","chen","tanaka","smith","tom","mary","peter","john","alice","bob",
    "nasa","beijing","china","chinese","english","mars","africa","african",
    "asia","europe","american","british","french","german","spanish","japanese",
    "suez","panama","jezero","ohio","washington","perseverance","antarctica",
    "shackleton","titanic","alzheimer","hanfu",
    # 缩写/否定
    "don","doesn","didn","isn","aren","wasn","weren","hasn","hadn",
    "wouldn","couldn","shouldn","won","cannot",
    # 教学内容格式词
    "admin","istr","tion","civis","habilis","iest",
})
