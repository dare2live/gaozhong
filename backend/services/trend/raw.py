"""raw 词频/题型 count 统计 (从原 trend.py 抽)."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

import duckdb
import yaml

from . import scope

_ERA_STRUCT_YAML = Path(__file__).resolve().parents[3] / "backend" / "config" / "exam_structure_eras.yaml"


@lru_cache(maxsize=1)
def _era_structure() -> dict:
    """卷改结构真相源 (单一加载点; canonical 题型 + extraction_gap 掩码 by era)."""
    return yaml.safe_load(_ERA_STRUCT_YAML.read_text(encoding="utf-8"))["eras"]

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


def _qt_signal(qt: str, struct: dict, eras: list) -> tuple[bool, bool, bool, str]:
    """题型 signal 由**卷面结构 config**(真相源)定, 非数据 presence (数据有提取gap会误判).

    返回 (in_old, in_new, extraction_gap, signal). signal: skeleton(两卷制常驻骨架) /
    retired(真退场: 卷面改革取消) / introduced(真登场: 卷面改革新增) / unregistered(config未登记, 诚实暴露)。
    """
    old_c, new_c = struct.get(eras[0], {}), struct.get(eras[1], {})
    in_old = qt in (old_c.get("canonical") or [])
    in_new = qt in (new_c.get("canonical") or [])
    gap = qt in (old_c.get("extraction_gap") or []) or qt in (new_c.get("extraction_gap") or [])
    if in_old and in_new:
        sig = "skeleton"
    elif in_old:
        sig = "retired"
    elif in_new:
        sig = "introduced"
    else:
        sig = "unregistered"   # 数据里有但 config 未登记 → 暴露(防默默漏登记卷改结构)
    return in_old, in_new, gap, sig


def _qt_row(qt: str, era_qt: dict, struct: dict, eras: list) -> dict:
    """单题型 presence 行 (signal 由 config 结构定 + 数据年份附带, extraction_gap 标提取不全)."""
    old = sorted(era_qt[eras[0]].get(qt, set()))
    new = sorted(era_qt[eras[1]].get(qt, set()))
    in_old, in_new, gap, signal = _qt_signal(qt, struct, eras)
    yrs = old + new
    return {"question_type": qt, "old_years": old, "new_years": new, "signal": signal,
            "extraction_gap": gap, "in_blueprint_old": in_old, "in_blueprint_new": in_new,
            "first_year": min(yrs) if yrs else None, "last_year": max(yrs) if yrs else None}


def question_type_era_presence(con: duckdb.DuckDBPyConnection) -> dict:
    """题型 × 卷制era presence — **命题趋势真值层**(provenance=structural_truth, 真题原卷结构).

    用户 2026-06-21: 结构层真值足以撑命题趋势("万变不离其宗"+可感知迁移)。presence **粒度无关**
    (不受 2021/22 子题级 vs 余年 passage 级 count 抖动影响)。**v2 提取完整性掩码(坑12)**: signal 由
    `exam_structure_eras.yaml` 卷面结构真相源定, **非数据 presence** — 区分 (a) 真退场/真登场(卷面改革)
    vs (b) extraction_gap(卷面有但本项目未抽全 → presence年不可作首末考年信号)。修 v1 把听力/续写"提取年"
    误当"登场年"。实测: 阅读/完形/七选五/语法填空=骨架; 短文改错=真退场(新高考取消); 续写/应用文=真登场
    (新高考新增, 但登场年=extraction_gap不可信); 听力=骨架·缺源(两卷制常驻, 本项目未抽全, 非登场2021)。
    """
    rows = con.execute(
        f"SELECT year, question_type FROM exam_questions "
        f"WHERE {scope.LIAONING_PREDICATE} AND year IS NOT NULL AND question_type IS NOT NULL"
    ).fetchall()
    era_qt: dict = defaultdict(lambda: defaultdict(set))
    for yr, qt in rows:
        era_qt[scope.segment(int(yr))][qt].add(int(yr))
    struct = _era_structure()
    eras = [scope.ERA_OLD, scope.ERA_NEW]
    # 题型全集 = config canonical ∪ 数据出现 (config-only 也列出 = 诚实暴露"卷面有未抽")
    all_qt = {q for e in struct.values() for q in (e.get("canonical") or [])}
    all_qt |= {qt for e in era_qt.values() for qt in e}
    out = [_qt_row(qt, era_qt, struct, eras) for qt in sorted(all_qt)]
    return {"province_scope": "辽宁卷", "provenance": "structural_truth", "eras": eras,
            "by_question_type": out,
            "note": "signal由卷面结构真相源(exam_structure_eras.yaml)定非数据presence; extraction_gap=卷面有但本项目未抽全(听力/写作年不可信); 短文改错真退场/续写应用文真登场=新高考改革命题趋势真值"}


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
