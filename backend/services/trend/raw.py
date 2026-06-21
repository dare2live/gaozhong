"""raw 词频/题型 count 统计 (从原 trend.py 抽)."""
from __future__ import annotations

import re
from collections import Counter, defaultdict

import duckdb

from . import scope

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]{1,}")

STOPWORDS = {
    "the","a","an","and","or","but","of","to","in","on","at","for","with","by",
    "is","are","was","were","be","been","being","am","do","does","did","done",
    "have","has","had","having","will","would","shall","should","can","could",
    "may","might","must","not","no","nor","yes","so","as","if","then","than",
    "this","that","these","those","it","its","he","she","they","them","his",
    "her","their","we","you","i","me","my","your","our","us","him",
    "what","when","where","why","how","which","who","whom","whose",
    "from","into","onto","upon","over","under","about","above","below","between",
    "out","up","down","off","through","during","before","after","since","until",
    "while","because","although","though","unless","also","just","only","more",
    "most","some","any","all","each","every","other","another","such","same",
    "very","too","much","many","few","little","own",
    "one","two","three","four","five","six","seven","eight","nine","ten",
    "first","second","third",
    "passage","question","answer","choose","read","write","following","below",
    "correct","best","blank","blanks","example","examples","section",
    "according","please","note","instructions",
}


def word_freq_by_year(con: duckdb.DuckDBPyConnection,
                       restrict_to_cefr: bool = True,
                       exclude_stopwords: bool = True) -> dict[str, dict[int, int]]:
    cefr = _load_cefr_set(con) if restrict_to_cefr else set()
    out: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    rows = con.execute(
        f"SELECT year, raw_question FROM exam_questions "
        f"WHERE {scope.LIAONING_PREDICATE} AND year IS NOT NULL"
    ).fetchall()
    for yr, qtext in rows:
        _tally_year(out, yr, qtext, cefr, exclude_stopwords, restrict_to_cefr)
    return out


def _load_cefr_set(con: duckdb.DuckDBPyConnection) -> set[str]:
    return {r[0] for r in con.execute("SELECT word FROM cefr_vocab").fetchall()}


def _tally_year(out: dict, yr, qtext, cefr: set, exclude_stop: bool, restrict: bool) -> None:
    if not yr or not qtext:
        return
    for tok in _WORD_RE.findall(qtext):
        w = tok.lower()
        if exclude_stop and w in STOPWORDS:
            continue
        if restrict and w not in cefr:
            continue
        out[w][yr] += 1


def top_high_freq_words(con: duckdb.DuckDBPyConnection, top_n: int = 50) -> list[dict]:
    freq = word_freq_by_year(con)
    totals = {w: sum(yrs.values()) for w, yrs in freq.items()}
    rank = sorted(totals.items(), key=lambda kv: -kv[1])[:top_n]
    return [{"word": w, "total": n,
              "years": dict(sorted(freq[w].items())),
              "year_span": len(freq[w])} for w, n in rank]


def type_freq_by_year(con: duckdb.DuckDBPyConnection) -> dict[int, Counter]:
    out: dict[int, Counter] = defaultdict(Counter)
    for yr, qt in con.execute(
        f"SELECT year, question_type FROM exam_questions "
        f"WHERE {scope.LIAONING_PREDICATE} AND year IS NOT NULL"
    ).fetchall():
        if yr and qt:
            out[yr][qt] += 1
    return out


def question_type_era_presence(con: duckdb.DuckDBPyConnection) -> dict:
    """题型 × 卷制era presence — **命题趋势真值层**(provenance=structural_truth, 真题原卷题型).

    用户 2026-06-21: 结构层真值足以撑命题趋势("万变不离其宗"+可感知迁移)。presence **粒度无关**
    (不受 2021/22 子题级 vs 余年 passage 级 count 抖动影响, 区别 type_distribution 占比) → 跨命题主体
    可信。signal: skeleton(两era皆在=骨架) / retired(退场) / introduced(登场)。复用 scope.segment 单点。
    实测: 阅读/完形/七选五/语法填空=骨架; 短文改错退场(末2020); 续写/应用文/听力登场=2017课标核心素养驱动。
    """
    rows = con.execute(
        f"SELECT year, question_type FROM exam_questions "
        f"WHERE {scope.LIAONING_PREDICATE} AND year IS NOT NULL AND question_type IS NOT NULL"
    ).fetchall()
    era_qt: dict = defaultdict(lambda: defaultdict(set))
    for yr, qt in rows:
        era_qt[scope.segment(int(yr))][qt].add(int(yr))
    eras = [scope.ERA_OLD, scope.ERA_NEW]
    out = []
    for qt in sorted({qt for e in era_qt.values() for qt in e}):
        old = sorted(era_qt[eras[0]].get(qt, set()))
        new = sorted(era_qt[eras[1]].get(qt, set()))
        signal = "retired" if old and not new else ("introduced" if new and not old else "skeleton")
        out.append({"question_type": qt, "old_years": old, "new_years": new, "signal": signal,
                    "first_year": min(old + new), "last_year": max(old + new)})
    return {"province_scope": "辽宁卷", "provenance": "structural_truth", "eras": eras,
            "by_question_type": out,
            "note": "presence粒度无关; 题型骨架连续(万变不离其宗)+退场/登场迁移=命题趋势真值层; 登场年受提取gap影响(听力/写作部分年未抽)"}


def trend_summary(con: duckdb.DuckDBPyConnection) -> dict:
    """件1: 全部趋势锚定辽宁卷 (§7); 附样本量诊断, 薄样本年不冒充趋势."""
    top = top_high_freq_words(con, top_n=30)
    type_by_year = type_freq_by_year(con)
    type_by_year_serialized = {y: dict(c) for y, c in sorted(type_by_year.items())}
    # 件3: 题型分布按卷制 era 聚合 (PIT §3.1 不混算 2021 断点; 复用上面已取的 by_year + scope.segment 单点)
    by_era: dict[str, Counter] = defaultdict(Counter)
    for yr, c in type_by_year.items():
        by_era[scope.segment(yr)] += c
    type_by_era = {era: dict(c) for era, c in sorted(by_era.items(), reverse=True)}
    diag = scope.diagnose(con)
    return {
        "province_scope": "辽宁卷",
        "top_words": top,
        "type_distribution_by_year": type_by_year_serialized,
        "type_distribution_by_era": type_by_era,  # 件3 前端 era 分隔渲染源 (分布层, 不画跨era斜率)
        "years_covered": sorted(type_by_year),
        "sample_diagnosis": diag["by_segment"],
        "distribution_reliable": diag["distribution_reliable"],  # 辽宁新高考II 140题 → True
        "trend_reliable": diag["trend_reliable"],                # 逐年slope → False
    }
