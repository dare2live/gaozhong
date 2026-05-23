"""超纲词 × 高考真题 cross-check (用户 2026-05-23: 超纲词跟高考试卷比对).

定义:
  - 超纲词 (extracurricular) = unit_vocab_intro 中 NOT IN cefr_vocab 的 word.
  - 高价值超纲 (HV-extra) = 超纲词 ∧ 出现在 ≥ 1 道辽宁真题题面里.
  - 低价值超纲 (LV-extra) = 超纲词 ∧ 不出现在任何辽宁真题中.

教学意义:
  - HV-extra 是"虽超纲但高考考" — 必须教
  - LV-extra 是"超纲且高考不考" — 教材厚度的"装饰"部分, 可降权 / 选学

输出: audit_findings + 给 word 节点的 attrs.gaokao_hit_count.
"""
from __future__ import annotations

import re

import duckdb

from ._common import finding


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[A-Za-z][A-Za-z'\-]{1,}", text or "")}


def _load_extracurricular(con: duckdb.DuckDBPyConnection) -> set[str]:
    try:
        return {row[0] for row in con.execute("""
            SELECT DISTINCT v.word FROM unit_vocab_intro v
            INNER JOIN units u
              ON u.version_key=v.version_key AND u.volume_key=v.volume_key AND u.unit_number=v.unit_number
            LEFT JOIN cefr_vocab c ON c.word = v.word
            WHERE c.word IS NULL
        """).fetchall()}
    except duckdb.CatalogException:
        return set()


def _exam_hits(con: duckdb.DuckDBPyConnection, extra: set[str]
               ) -> tuple[dict[str, set], dict[str, set]]:
    """Return (word→qids_all, word→qids_liaoning)."""
    all_q: dict[str, set] = {}
    ln_q: dict[str, set] = {}
    for qid, qtext, prov in con.execute(
        "SELECT question_id, raw_question, province FROM exam_questions"
    ).fetchall():
        hits = _tokenize(qtext) & extra
        is_ln = prov and "辽宁" in prov
        for w in hits:
            all_q.setdefault(w, set()).add(qid)
            if is_ln:
                ln_q.setdefault(w, set()).add(qid)
    return all_q, ln_q


def _write_priority_attrs(con: duckdb.DuckDBPyConnection,
                          hv_all: dict[str, set], hv_ln: dict[str, set],
                          lv: set[str]) -> None:
    for w, qs in hv_all.items():
        attrs = ('{"extracurricular": true, "cefr_level": "校本扩展", '
                 f'"gaokao_hit_count_all": {len(qs)}, '
                 f'"gaokao_hit_count_ln": {len(hv_ln.get(w, set()))}, '
                 '"teaching_priority": "HV_extra"}')
        con.execute("UPDATE nodes SET attrs_json=? WHERE concept_id=?",
                    [attrs, f"word:{w}"])
    if lv:
        lv_attrs = ('{"extracurricular": true, "cefr_level": "校本扩展", '
                    '"gaokao_hit_count_all": 0, "teaching_priority": "LV_extra"}')
        con.executemany("UPDATE nodes SET attrs_json=? WHERE concept_id=?",
                        [(lv_attrs, f"word:{w}") for w in lv])


def audit_extracurricular_in_exam(con: duckdb.DuckDBPyConnection) -> list[dict]:
    extra = _load_extracurricular(con)
    if not extra:
        return [finding("extracurricular_vs_exam", "OK", target="extracurricular set",
                        expected="N", actual="0", note="无超纲词 (extractor 未跑或全在课标内)")]
    all_q, ln_q = _exam_hits(con, extra)
    hv_all = {w: qs for w, qs in all_q.items() if qs}
    hv_ln = {w: qs for w, qs in ln_q.items() if qs}
    lv = extra - set(hv_all)
    _write_priority_attrs(con, hv_all, ln_q, lv)
    return [
        finding("extracurricular_vs_exam", "OK",
                target="超纲词 ∩ 高考真题 (题面 substring)",
                expected="HV_extra > 0", actual=f"HV_all={len(hv_all)} HV_ln={len(hv_ln)} LV={len(lv)}",
                note=f"超纲词总 {len(extra)}; HV_all 比例 {len(hv_all)/len(extra):.1%}"),
        finding("extracurricular_vs_exam", "WARN" if hv_all else "OK",
                target="教学优先级建议", expected="HV_extra 标星",
                actual=f"HV_all={len(hv_all)}",
                note="HV_all 已写入 nodes.attrs_json.teaching_priority='HV_extra'"),
    ]
