"""词 × 高考真题 4 象限分类 — **辽宁卷口径** (§7) + **单一 writer** (Rule 1; #12/#13/#14).

  A. 课标 ∩ 辽宁考过      → core           (必教必练, 高频考点)
  B. 课标 − 辽宁考过      → standard       (课标背书, 常规教学)
  C. 超纲 ∩ 辽宁考过      → HV_extra       (虽超纲但辽宁考过, 高价值扩展)
  D. 超纲 − 辽宁考过      → LV_extra       (装饰性扩展, 可降权)

整改 (用户 2026-06-16/17):
  #13 province-blind → 改 **辽宁口径** (只看 tests_word 边的辽宁命中, 不混 284 外省题)。
  #14 整段 UPDATE 覆盖 → 本模块是 nodes.attrs_json 的 **唯一 writer**:
      一次写全 {cefr_level, exam_status, teaching_hint, gaokao_hit_count_ln,
      gaokao_hit_count_all, teaching_priority?, extracurricular?},
      extracurricular 不再写 nodes (杜绝双写覆盖)。
  考过判定 → **tests_word 边** (Rule3 唯一真相, exam_vocab.word_exam_hits_from_edges):
      core 词必有边 (core-无边=0 by construction); 与 build_vocab_classification 同源 (3源一致)。
"""
from __future__ import annotations

import duckdb

from backend.services.exam_vocab import word_exam_hits_from_edges
from backend.services.vocab_classify import is_real_over

from ._common import finding

STATUS_HINT = {
    "core":      "课标+辽宁高考双印证, 必教必练",
    "standard":  "课标内但辽宁近年真题未出, 常规教学",
    "HV_extra":  "教材超纲但辽宁高考考过, 必教 (高价值扩展)",
    "LV_extra":  "教材超纲且辽宁高考不考, 可降权/选学",
}

# stage 维 (K12 分阶段平台, docs/k12_staged_platform_design.md): cefr_level→引入阶段。
# tag-not-exclude: with/the 等义教词标"义务教育"(非高中新词), 留图里供按 stage 过滤, 不删。
# 小学/初中 细分待初中课标(义务教育2022 二级/三级)抽取后 reconcile (S1/S4)。
_STAGE = {"义教": "义务教育", "必修": "高中必修", "选必": "高中选修",
          "校本扩展": "校本超纲", "课标变形": "课标变形"}


def _load_textbook_words(con: duckdb.DuckDBPyConnection) -> set[str]:
    try:
        return {r[0] for r in con.execute("""
            SELECT DISTINCT v.word FROM unit_vocab_intro v
            INNER JOIN units u
              ON u.version_key=v.version_key AND u.volume_key=v.volume_key AND u.unit_number=v.unit_number
        """).fetchall()}
    except duckdb.CatalogException:
        return set()


def _cefr_levels(con: duckdb.DuckDBPyConnection) -> dict[str, str]:
    return {r[0]: r[1] for r in con.execute("SELECT word, cefr_level FROM cefr_vocab").fetchall()}


def _classify(cefr: set[str], textbook: set[str], ln_tested: set[str]) -> dict[str, set[str]]:
    """辽宁口径 4 象限 (ln_tested = 辽宁命中 ≥1 题的词集).

    "超纲" 判定走单一计算点 vocab_classify.is_real_over (= 真超纲, 排除课标词的
    屈折/派生/专名) — 与 vocab_classification.jsonl 同一真相源, 保证 3 源一致 (#12)。
    课标词的屈折/派生(based/assessment...) 实为课标内 (§1.2), 归 cefr-aligned 桶
    (core/standard), 不冒充 HV_extra。
    """
    over = {w for w in (textbook - cefr) if is_real_over(w)}     # 真超纲 (单一判定点)
    aligned = (cefr | textbook) - over                          # 课标 + 屈折/派生变形
    return {
        "core":     aligned & ln_tested,
        "standard": aligned - ln_tested,
        "HV_extra": over & ln_tested,
        "LV_extra": over - ln_tested,
    }


def _attrs_for(word: str, status: str, is_extra: bool,
               hit: dict[str, int], cefr_lv: dict[str, str]) -> str:
    """完整 attrs_json (单一 writer 写全; 超纲词带 teaching_priority+extracurricular)."""
    parts: list[str] = []
    if is_extra:
        cefr_field = "校本扩展"
    elif word in cefr_lv:
        cefr_field = cefr_lv[word]
    else:
        cefr_field = "课标变形"   # 课标词的屈折/派生 (§1.2 实为课标内, 非超纲)
    parts.append(f'"cefr_level": "{cefr_field}"')
    parts.append(f'"stage": "{_STAGE.get(cefr_field, cefr_field)}"')
    parts.append(f'"exam_status": "{status}"')
    parts.append(f'"teaching_hint": "{STATUS_HINT[status]}"')
    parts.append(f'"gaokao_hit_count_ln": {hit["ln"]}')
    parts.append(f'"gaokao_hit_count_all": {hit["all"]}')
    if is_extra:
        parts.append('"extracurricular": true')
        parts.append(f'"teaching_priority": "{status}"')   # HV_extra / LV_extra 与 exam_status 一致
    return "{" + ", ".join(parts) + "}"


def _write_all(con: duckdb.DuckDBPyConnection, bins: dict[str, set[str]],
               hits: dict[str, dict[str, int]], cefr_lv: dict[str, str]) -> None:
    """唯一 writer: 每词一次写全 attrs_json (杜绝 #14 整段覆盖)."""
    rows: list[tuple[str, str]] = []
    for status, words in bins.items():
        is_extra = status.endswith("_extra")
        for w in words:
            hit = hits.get(w, {"ln": 0, "all": 0})   # 无边词 (standard/LV) 命中 0
            rows.append((_attrs_for(w, status, is_extra, hit, cefr_lv), f"word:{w}"))
    if rows:
        con.executemany("UPDATE nodes SET attrs_json=? WHERE concept_id=?", rows)


def audit_vocab_4q_classification(con: duckdb.DuckDBPyConnection) -> list[dict]:
    cefr_lv = _cefr_levels(con)
    cefr = set(cefr_lv)
    textbook = _load_textbook_words(con)
    hits = word_exam_hits_from_edges(con)   # 唯一真相=tests_word 边 (core 词必有边)
    ln_tested = {w for w, h in hits.items() if h["ln"] > 0}      # 辽宁命中 ≥1 题
    bins = _classify(cefr, textbook, ln_tested)
    _write_all(con, bins, hits, cefr_lv)
    core_ratio = len(bins["core"]) / max(1, len(cefr))
    n_ln_q = con.execute("SELECT COUNT(*) FROM exam_questions WHERE province LIKE '辽宁%'").fetchone()[0]
    return [
        finding("exam_coverage_4q", "OK",
                target="word 4 象限分类 (辽宁口径, 单一 writer)",
                expected="core+standard+HV+LV 全分类",
                actual=" ".join(f"{k}={len(v)}" for k, v in bins.items()),
                note=f"教材 {len(textbook)} 词; 辽宁命中 {len(ln_tested)} 词; 辽宁题 {n_ln_q}"),
        finding("exam_coverage_4q", "WARN" if core_ratio < 0.3 else "OK",
                target="core 词比例 (辽宁)", expected="≥ 30%",
                actual=f"{len(bins['core'])}/{len(cefr)} = {core_ratio:.1%}",
                note=f"辽宁真题 {n_ln_q} 题; 低=辽宁样本不足"),
    ]
