"""真题省份/卷型精炼 (F) — 单一计算点, 按 provenance + 辽宁实际卷型史诚实标注.

L-N / L-P 教训: GAOKAO-Bench base repo **不标省份**, 旧逻辑对 2021+ 默认推断辽宁,
导致 2021/2022 混合卷(含全国甲卷, 见 Reading_Comp/112 "Landscape Photographer")
被假标"辽宁新课标 II 卷". 本服务按 source_repo 区分可信度, 宁缺毋滥:

可信 provenance (可断言"辽宁新课标 II 卷"):
  - source_repo='local_pdf'      → 2024/2025 真题 PDF 全文核验
  - source_repo 含 'Updates'      → 2023 GAOKAO-Bench-Updates, repo 自带卷型标注
  - 2015-2020 (国家卷时期)        → 辽宁实际坐 全国新课标 II, 与 GAOKAO-Bench 同卷

诚实降级 (不得冒充辽宁/新课标 II):
  - 2010-2014 (辽宁自主命题期)    → GAOKAO-Bench 数据为他省全国新课标 II, 非辽宁卷
  - 2021+ 且无可信 provenance     → GAOKAO-Bench 混合卷, 未核验, 待 M0 收口

这是 exam_questions.province / paper_type 的唯一计算点 (architecture Rule 1).
init_db.py Layer 2 在 mirror 后调本服务, 覆盖 mirror 时的临时 province.
"""
from __future__ import annotations

import duckdb

# 降级后的诚实标签 (check_21 据此防回归)
LABEL_PRE2015_NON_LN = "全国卷 (2010-2014, 非辽宁; 辽宁当年自主命题)"
# 2015-2020 国家卷期: 史实上辽宁坐全国新课标II, 但本数据未逐题 PDF 核验 → 标注推断级别,
# 区别于 2024/2025 的 PDF 全文核验. (对抗审查 L-R 保留意见: 不与已核验源混同可信度)
LABEL_NATIONAL_ERA_LN = "辽宁 (全国新课标 II 卷, 2015-2020·史实推断未逐题核验)"
LABEL_XGKII_LN = "辽宁 (新课标 II 卷, 2021+)"
LABEL_UNVERIFIED_XGKII = "未知 (GAOKAO-Bench 混合卷, 待 M0 核验)"
PAPER_XGKII = "新课标 II 卷"
PAPER_UNKNOWN = "未知"


def _is_trusted_xgkii(year: int | None, repo: str) -> bool:
    """2021+ 是否有可信 provenance 可断言辽宁新课标 II 卷."""
    if not year or year < 2021:
        return False
    return repo == "local_pdf" or "Updates" in repo


def _classify(year: int | None, repo: str) -> tuple[str, str]:
    """(province, paper_type) — 按 provenance + 辽宁卷型史. 见模块 docstring."""
    repo = repo or ""
    if _is_trusted_xgkii(year, repo):
        return LABEL_XGKII_LN, PAPER_XGKII
    if year is None:
        return PAPER_UNKNOWN, PAPER_UNKNOWN
    if year <= 2014:
        return LABEL_PRE2015_NON_LN, PAPER_UNKNOWN
    if year <= 2020:
        return LABEL_NATIONAL_ERA_LN, PAPER_UNKNOWN
    return LABEL_UNVERIFIED_XGKII, PAPER_UNKNOWN


def refine_province(con: duckdb.DuckDBPyConnection) -> dict:
    """重算所有 exam_questions 的 province + paper_type (idempotent, 单一计算点)."""
    rows = con.execute(
        "SELECT question_id, year, source_repo, province, paper_type FROM exam_questions"
    ).fetchall()
    updated = 0
    counts: dict[str, int] = {}
    for qid, yr, repo, old_prov, old_paper in rows:
        new_prov, new_paper = _classify(yr, repo or "")
        if new_prov != old_prov or new_paper != old_paper:
            con.execute(
                "UPDATE exam_questions SET province=?, paper_type=? WHERE question_id=?",
                [new_prov, new_paper, qid],
            )
            updated += 1
        counts[new_prov] = counts.get(new_prov, 0) + 1
    return {"updated": updated, "counts": counts}
