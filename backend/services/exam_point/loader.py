"""考点 canonical 维度入库 (件2) — 双模型标注 artifact → nodes(exam_point) + edges(tests_exam_point).

来源: data/structured/exam_point/genre_theme_labels.jsonl (双模型分类, 一致=dual_model_agree)。
诚实红线:
  - **只落 dual_model_agree 且非 NA** 的边 (歧义 needs_review / 无正文 NA 不入 canonical 分布,
    宁缺毋滥); provenance 入 edges.evidence_json, 趋势/分布消费方据此知"这是双模型一致, 非人工核验"。
  - 节点**懒建**: 只为实际出现的考点 label 建 exam_point 节点, 避免 taxonomy 全集造 orphan。
取代 tests_word 把整篇实词当"考点"的 token 假象 (critic 盲点 #2)。
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]
LABELS_PATH = ROOT / "data" / "structured" / "exam_point" / "genre_theme_labels.jsonl"

# 标注字段 dimension → exam_point node 维度名 (与 taxonomy node_id_pattern 对齐)
_DIMENSIONS = (("genre", "genre_prov", "genre"),
               ("theme", "theme_prov", "theme_context"))


def _point_node_id(dimension: str, label: str) -> str:
    return f"exam_point:{dimension}:{label}"


def _read_labels() -> list[dict]:
    if not LABELS_PATH.exists():
        return []
    return [json.loads(line) for line in LABELS_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _ensure_point_node(con: duckdb.DuckDBPyConnection, dimension: str, label: str) -> bool:
    """懒建 exam_point 节点 (只为实际出现的考点); 返回是否新建."""
    nid = _point_node_id(dimension, label)
    if con.execute("SELECT 1 FROM nodes WHERE concept_id = ?", [nid]).fetchone():
        return False
    con.execute("INSERT INTO nodes VALUES (?, ?, ?, ?)",
                [nid, "exam_point", label, json.dumps({"dimension": dimension}, ensure_ascii=False)])
    return True


def load_exam_points(con: duckdb.DuckDBPyConnection) -> dict:
    """读标注 artifact → 落 exam_point 节点 + tests_exam_point 边 (只 dual_model_agree, 非 NA)."""
    rows = _read_labels()
    nodes_made = 0
    edges_made = 0
    skipped_review = 0
    for row in rows:
        qnode = f"question:{row['question_id']}"
        if not con.execute("SELECT 1 FROM nodes WHERE concept_id = ?", [qnode]).fetchone():
            continue
        for label_key, prov_key, dimension in _DIMENSIONS:
            label = row.get(label_key)
            prov = row.get(prov_key)
            if label == "NA":
                continue
            if prov != "dual_model_agree":
                skipped_review += 1
                continue
            nodes_made += int(_ensure_point_node(con, dimension, label))
            pnode = _point_node_id(dimension, label)
            exists = con.execute(
                "SELECT 1 FROM edges WHERE src_id = ? AND dst_id = ? AND relation = 'tests_exam_point'",
                [qnode, pnode]).fetchone()
            if exists:
                continue
            con.execute(
                "INSERT INTO edges (src_id, dst_id, relation, weight, evidence_json) VALUES (?, ?, ?, ?, ?)",
                [qnode, pnode, "tests_exam_point", 1.0,
                 json.dumps({"dimension": dimension, "provenance": prov,
                             "cue": (row.get("evidence") or "")[:200]}, ensure_ascii=False)])
            edges_made += 1
    return {"labels": len(rows), "nodes_made": nodes_made,
            "edges_made": edges_made, "skipped_needs_review": skipped_review}


# 卷制断点 (PIT §3.1): 2021 起辽宁用新高考全国 II 卷; 与 trend.scope.segment 同口径。
_ERA_SQL = "CASE WHEN q.year >= 2021 THEN '2021+_新高考II' ELSE '2015-2020_旧课标II' END"


def exam_point_distribution(con: duckdb.DuckDBPyConnection,
                            dimension: str | None = None) -> dict:
    """辽宁考点分布 — **按卷制 era 分层 + 占比** (单一计算点, 从 tests_exam_point 边算一次).

    用户 2026-06-15 纠偏: 不取全历史平均(会抹掉时间轴结构), 分时间轴/卷制分层看 (PIT §3.1)。
    返回 {era: {dimension: [{label, n, pct}]}}, 每段内 dimension 各 label 占比独立计。
    """
    rows = con.execute(f"""
        SELECT {_ERA_SQL} AS era,
               json_extract_string(e.evidence_json, '$.dimension') AS dim,
               n.label, COUNT(*) AS c
        FROM edges e
        JOIN nodes n ON n.concept_id = e.dst_id
        JOIN exam_questions q
          ON ('question:' || q.question_id) = e.src_id AND q.province LIKE '辽宁%'
        WHERE e.relation = 'tests_exam_point'
        GROUP BY 1, 2, 3
    """).fetchall()
    totals: dict[tuple, int] = {}
    for era, dim, _label, c in rows:
        totals[(era, dim)] = totals.get((era, dim), 0) + c
    by_era: dict[str, dict[str, list]] = {}
    for era, dim, label, c in rows:
        if dimension and dim != dimension:
            continue
        by_era.setdefault(era, {}).setdefault(dim, []).append(
            {"label": label, "n": c, "pct": round(100 * c / totals[(era, dim)], 1)})
    for era in by_era:
        for dim in by_era[era]:
            by_era[era][dim].sort(key=lambda r: -r["n"])
    return by_era
