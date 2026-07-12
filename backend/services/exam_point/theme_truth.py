"""Theme 交叉验证诚实披露 (坑16).

辽宁卷 analysis 几乎无显式主题句可抽 → 不可伪造 cross_verified。
本模块只报 dual_model 现状 + 可核验缺口, 不写 provenance 升级。
"""
from __future__ import annotations

import re

import duckdb

# 显式主题句极窄: 仅当教研解析写明「主题/话题是…人与X」才可交叉; 现库实测≈0
_THEME_EXPLICIT_RE = re.compile(
    r"(?:本文|文章|本篇)?(?:的)?(?:主题|话题)(?:是|为|：|:)\s*([^\n。；;]{2,40})"
)


def analysis_theme_crosscheck(con: duckdb.DuckDBPyConnection) -> dict:
    """辽宁卷: analysis 显式主题句 vs theme_l2 边 — 诚实报缺口, 不升级 provenance."""
    rows = con.execute(
        "SELECT question_id, analysis FROM exam_questions "
        "WHERE province LIKE '辽宁%' AND analysis IS NOT NULL AND TRIM(analysis) <> ''"
    ).fetchall()
    n_explicit = sum(1 for _, a in rows if _THEME_EXPLICIT_RE.search(a or ""))
    n_theme = con.execute(
        "SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' "
        "AND json_extract_string(evidence_json, '$.dimension') = 'theme_l2' "
        "AND src_id LIKE 'question:%'"
    ).fetchone()[0]
    n_cross = con.execute(
        "SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' "
        "AND json_extract_string(evidence_json, '$.dimension') = 'theme_l2' "
        "AND json_extract_string(evidence_json, '$.provenance') = 'cross_verified'"
    ).fetchone()[0]
    return {
        "n_analysis_with_any_text": len(rows),
        "n_analysis_explicit_theme": n_explicit,
        "n_theme_l2_edges": n_theme,
        "n_cross_verified_edges": n_cross,
        # 诚实门: 无假升 cross_verified (有显式句时仅披露, 不自动 FAIL)
        "pass": n_cross == 0,
        "status": "dual_model_only",
        "note": (
            "theme_l2 仍 dual_model_agree; analysis 无可核验显式主题句 → "
            "不伪造 cross_verified (坑16). 待有第一手主题解析源再开升级路径."
        ),
    }
