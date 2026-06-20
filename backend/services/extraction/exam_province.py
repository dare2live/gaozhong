"""真题省份/卷型精炼 (F) — 统一可信源标注; gb/Updates 信任 mirror 的 category-aware 标注.

2026-06-15 重构: exam.classify_paper 在 mirror 时按 GAOKAO-Bench/Updates 的 category
(新课标I/II/III/甲/乙) 做诚实卷型标注 — 只有 "新课标II + year>=2015" = 辽宁卷, 其余非辽宁。
本服务只负责把可信源(local_pdf 2024/2025 PDF 核验, eol_xgkii EOL M0 review 核验)
统一标为辽宁新课标II卷; gb/Updates 行的 category-aware province 由 mirror 设, 不在此覆盖
(避免 refine 用粗粒度年代逻辑把 mirror 的精确卷型标注冲掉, 见 L-N/L-P/L-R)。

这是 exam_questions 可信源 province 的单一统一点 (architecture Rule 1);
gb/Updates 的单一计算点是 exam.classify_paper。init_db Layer 2 在 mirror 后调本服务。
"""
from __future__ import annotations

import duckdb

LABEL_XGKII_LN = "辽宁 (新课标 II 卷, 2021+)"
PAPER_XGKII = "新课标 II 卷"

# 可信源前缀: 这些源已逐题/全文核验为辽宁新课标II卷
TRUSTED_LOCAL = "local_pdf"
TRUSTED_EOL_PREFIX = "eol_xgkii"


def _is_trusted_ln(repo: str) -> bool:
    return repo == TRUSTED_LOCAL or repo.startswith(TRUSTED_EOL_PREFIX)


def refine_province(con: duckdb.DuckDBPyConnection) -> dict:
    """统一可信源为辽宁新课标II; gb/Updates 保留 mirror 的 category-aware 标注 (idempotent)."""
    rows = con.execute(
        "SELECT question_id, source_repo, province, paper_type FROM exam_questions"
    ).fetchall()
    updated = 0
    counts: dict[str, int] = {}
    for qid, repo, prov, paper in rows:
        if _is_trusted_ln(repo or ""):
            if (prov, paper) != (LABEL_XGKII_LN, PAPER_XGKII):
                con.execute(
                    "UPDATE exam_questions_all SET province=?, paper_type=? WHERE question_id=?",
                    [LABEL_XGKII_LN, PAPER_XGKII, qid],
                )
                updated += 1
            counts[LABEL_XGKII_LN] = counts.get(LABEL_XGKII_LN, 0) + 1
        else:
            counts[prov] = counts.get(prov, 0) + 1
    return {"updated": updated, "counts": counts}
