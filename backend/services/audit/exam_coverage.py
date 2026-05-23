"""词 / 语法 × 高考真题 4 象限分类 (用户 2026-05-23):

  A. 课标 ∩ 真题考过      → core           (必教必学, 高频考点)
  B. 课标 ∩ 真题未考      → standard       (课标背书, 常规教学)
  C. 超纲 ∩ 真题考过      → HV_extra       (虽超纲但考过, 高价值扩展)
  D. 超纲 ∩ 真题未考      → LV_extra       (装饰性扩展, 可降权)

教学语义入 word.attrs_json.exam_status, 给后续作业生成 + 前端展示用.
"""
from __future__ import annotations

import re

import duckdb

from ._common import finding


def _tokenize_exam(con: duckdb.DuckDBPyConnection) -> set[str]:
    """所有 exam_questions raw_question + analysis token set, lowercase."""
    rows = con.execute("SELECT raw_question, analysis FROM exam_questions").fetchall()
    bag: set[str] = set()
    pat = re.compile(r"[A-Za-z][A-Za-z'\-]{1,}")
    for q, a in rows:
        for src in (q, a):
            if src:
                for t in pat.findall(src):
                    bag.add(t.lower())
    return bag


STATUS_HINT = {
    "core":      "课标+高考双印证, 必教必练",
    "standard":  "课标内但近年真题未出, 常规教学",
    "HV_extra":  "教材超纲但高考考过, 必教 (高价值扩展)",
    "LV_extra":  "教材超纲且高考不考, 可降权/选学",
}


def _load_textbook_words(con: duckdb.DuckDBPyConnection) -> set[str]:
    try:
        return {r[0] for r in con.execute("""
            SELECT DISTINCT v.word FROM unit_vocab_intro v
            INNER JOIN units u
              ON u.version_key=v.version_key AND u.volume_key=v.volume_key AND u.unit_number=v.unit_number
        """).fetchall()}
    except duckdb.CatalogException:
        return set()


def _classify(cefr: set[str], textbook: set[str], exam: set[str]) -> dict[str, set[str]]:
    return {
        "core":     cefr & exam,
        "standard": cefr - exam,
        "HV_extra": (textbook - cefr) & exam,
        "LV_extra": (textbook - cefr) - exam,
    }


def _attrs_for(con: duckdb.DuckDBPyConnection, word: str, status: str, is_extra: bool) -> str:
    if is_extra:
        cefr_field = '"cefr_level": "校本扩展"'
    else:
        lv = con.execute("SELECT cefr_level FROM cefr_vocab WHERE word=?", [word]).fetchone()
        cefr_field = f'"cefr_level": "{lv[0]}"' if lv else ""
    sep = ", " if cefr_field else ""
    return ("{" + cefr_field + sep
            + f'"exam_status": "{status}", "teaching_hint": "{STATUS_HINT[status]}"' + "}")


def _write_status(con: duckdb.DuckDBPyConnection, status: str, words: set[str], is_extra: bool) -> None:
    if not words:
        return
    rows = [(_attrs_for(con, w, status, is_extra), f"word:{w}") for w in words]
    con.executemany("UPDATE nodes SET attrs_json=? WHERE concept_id=?", rows)


def audit_vocab_4q_classification(con: duckdb.DuckDBPyConnection) -> list[dict]:
    cefr = {r[0] for r in con.execute("SELECT word FROM cefr_vocab").fetchall()}
    textbook = _load_textbook_words(con)
    exam = _tokenize_exam(con)
    bins = _classify(cefr, textbook, exam)
    for status, words in bins.items():
        _write_status(con, status, words, is_extra=status.endswith("_extra"))
    core_ratio = len(bins["core"]) / max(1, len(cefr))
    return [
        finding("exam_coverage_4q", "OK",
                target="word 4 象限分类",
                expected="core+standard+HV+LV 全分类",
                actual=" ".join(f"{k}={len(v)}" for k, v in bins.items()),
                note=f"教材 {len(textbook)} 词, exam_bag {len(exam)} tokens"),
        finding("exam_coverage_4q", "WARN" if core_ratio < 0.3 else "OK",
                target="core 词比例", expected="≥ 30%",
                actual=f"{len(bins['core'])}/{len(cefr)} = {core_ratio:.1%}",
                note="低意味真题样本不足 (现 334 题)"),
    ]
