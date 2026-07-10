"""Genre/theme 第一手交叉验证 (坑16 GenreTruthChecker MVP).

只读审计 + 统计; 不修改 edges (派生升级走 init_db loader 单点, 后续 Sprint)。
真相源优先级: exam_questions.analysis 显式体裁句 > dual_model artifact evidence (方向性, 非本函数核验)。
"""
from __future__ import annotations

import re
from pathlib import Path

import duckdb
import yaml

ROOT = Path(__file__).resolve().parents[3]
_GATE_CFG = ROOT / "backend" / "config" / "l3_readiness_gate.yaml"
_GENRES = ("记叙文", "说明文", "议论文", "应用文", "新闻报道", "夹叙夹议", "书评介绍")
_EXPLICIT_RE = re.compile(
    r"(?:这是一篇|本文是|文章为|体裁[为是：:]|文体[为是：:])\s*("
    + "|".join(re.escape(g) for g in _GENRES)
    + r")"
)


def _load_gate_cfg() -> dict:
    if not _GATE_CFG.exists():
        return {}
    return yaml.safe_load(_GATE_CFG.read_text(encoding="utf-8")) or {}


def _normalize_genre(label: str) -> str:
    return (label or "").split("|")[0].strip()


def _genre_edge_label(con: duckdb.DuckDBPyConnection, question_id: str) -> str | None:
    row = con.execute(
        "SELECT SUBSTR(e.dst_id, LENGTH('exam_point:genre:') + 1) "
        "FROM edges e WHERE e.src_id = ? AND e.relation = 'tests_exam_point' "
        "AND json_extract_string(e.evidence_json, '$.dimension') = 'genre'",
        [f"question:{question_id}"],
    ).fetchone()
    return row[0] if row else None


# 教研解析体裁名 → 可视为一致的 canonical 边标签 (课标无「夹叙夹议」项, 归记叙/议论)
_ANALYSIS_GENRE_ALIASES: dict[str, frozenset[str]] = {
    "夹叙夹议": frozenset({"记叙文", "议论文"}),
    "夹叙夹议文": frozenset({"记叙文", "议论文"}),
}


def _labels_agree(analysis_genre: str, edge_genre: str) -> bool:
    a, e = _normalize_genre(analysis_genre), _normalize_genre(edge_genre)
    if a == e or a in e or e in a:
        return True
    alts = _ANALYSIS_GENRE_ALIASES.get(a) or _ANALYSIS_GENRE_ALIASES.get(analysis_genre)
    return bool(alts and e in alts)


def analysis_genre_crosscheck(con: duckdb.DuckDBPyConnection) -> dict:
    """辽宁卷: analysis 显式体裁句 vs tests_exam_point genre 边."""
    rows = con.execute(
        "SELECT question_id, analysis FROM exam_questions "
        "WHERE province LIKE '辽宁%' AND analysis IS NOT NULL AND TRIM(analysis) <> ''"
    ).fetchall()
    agree, conflict, no_edge, samples = 0, 0, 0, []
    n_explicit = 0
    for qid, analysis in rows:
        m = _EXPLICIT_RE.search(analysis or "")
        if not m:
            continue
        n_explicit += 1
        explicit = m.group(1)
        edge_g = _genre_edge_label(con, qid)
        if edge_g is None:
            no_edge += 1
            continue
        row = {"question_id": qid, "analysis_genre": explicit, "edge_genre": edge_g}
        if _labels_agree(explicit, edge_g):
            agree += 1
        else:
            conflict += 1
            if len(samples) < 8:
                samples.append(row)
    n_cross = con.execute(
        "SELECT COUNT(*) FROM edges WHERE relation = 'tests_exam_point' "
        "AND json_extract_string(evidence_json, '$.dimension') IN "
        "('genre', 'theme_context', 'theme_l2') "
        "AND json_extract_string(evidence_json, '$.provenance') = 'cross_verified'"
    ).fetchone()[0]
    cfg = _load_gate_cfg().get("genre_truth", {})
    min_agree = int(cfg.get("min_analysis_agree", 5))
    max_conflict = int(cfg.get("max_analysis_conflict", 0))
    min_cross_edges = int(cfg.get("min_cross_verified_edges", 0))
    ok = agree >= min_agree and conflict <= max_conflict and n_cross >= min_cross_edges
    return {
        "n_analysis_explicit": n_explicit,
        "n_checked": agree + conflict,
        "n_agree": agree,
        "n_conflict": conflict,
        "n_no_edge": no_edge,
        "n_cross_verified_edges": n_cross,
        "conflict_samples": samples,
        "thresholds": {
            "min_analysis_agree": min_agree,
            "max_analysis_conflict": max_conflict,
            "min_cross_verified_edges": min_cross_edges,
        },
        "pass": ok,
        "note": "genre/theme 仍主要靠 dual_model; 本审计仅覆盖 analysis 显式体裁句子集",
    }
