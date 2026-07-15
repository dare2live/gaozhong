"""语法考点九桶只读 rollup — 派生自 tests_grammar, 禁止平行考查边.

单一计算点: 只读 edges(tests_grammar) ⋈ nodes/grammar_items → 九桶绝对计数。
禁止写入 tests_exam_point dim=grammar_point / tests_grammar_point。
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

import duckdb
import yaml

from backend.services.trend import scope

ROOT = Path(__file__).resolve().parents[3]
_BUCKETS = ROOT / "backend/config/grammar_point_buckets.yaml"


def _load_rules() -> list[tuple[str, list[str]]]:
    raw = yaml.safe_load(_BUCKETS.read_text(encoding="utf-8"))
    return [(b["id"], list(b.get("match_any") or [])) for b in (raw.get("buckets") or [])]


def _bucket_for(label: str, rules: list[tuple[str, list[str]]]) -> str | None:
    lab = label or ""
    for bid, keys in rules:
        if any(k in lab for k in keys):
            return bid
    return None


def grammar_point_rollup(con: duckdb.DuckDBPyConnection) -> dict:
    rules = _load_rules()
    bucket_ids = [b for b, _ in rules]
    rows = con.execute(f"""
        SELECT {scope.era_sql("q.year")} AS era, n.label, COUNT(*) AS c
        FROM edges e
        JOIN nodes n ON n.concept_id = e.dst_id
        JOIN exam_questions q
          ON ('question:' || q.question_id) = e.src_id AND q.province LIKE '辽宁%'
        WHERE e.relation = 'tests_grammar'
        GROUP BY 1, 2
    """).fetchall()
    n_edges_read = con.execute("""
        SELECT COUNT(*) FROM edges e
        JOIN exam_questions q ON ('question:' || q.question_id) = e.src_id
          AND q.province LIKE '辽宁%'
        WHERE e.relation = 'tests_grammar'
    """).fetchone()[0]
    n_parallel = con.execute("""
        SELECT COUNT(*) FROM edges
        WHERE relation = 'tests_exam_point'
          AND json_extract_string(evidence_json, '$.dimension') = 'grammar_point'
    """).fetchone()[0]
    n_rel = con.execute(
        "SELECT COUNT(*) FROM edges WHERE relation = 'tests_grammar_point'"
    ).fetchone()[0]

    by_era: dict[str, dict] = {}
    grand = Counter()
    unbucketed = Counter()
    assigned = 0
    for era, label, c in rows:
        bid = _bucket_for(label, rules)
        if bid is None:
            unbucketed[label] += c
            continue
        assigned += c
        grand[bid] += c
        by_era.setdefault(era, Counter())[bid] += c

    def _pack(ctr: Counter) -> list[dict]:
        return [{"bucket": b, "n": int(ctr.get(b, 0))} for b in bucket_ids]

    return {
        "derived_from": "tests_grammar",
        "status": "derived_rollup",
        "report_as": "absolute_count_not_percentage",
        "n_tests_grammar_edges_read": n_edges_read,
        "n_edges_assigned_to_buckets": assigned,
        "n_edges_unbucketed": sum(unbucketed.values()),
        "unbucketed_labels": sorted(unbucketed, key=lambda k: -unbucketed[k])[:20],
        "buckets": _pack(grand),
        "by_era": {era: _pack(ctr) for era, ctr in sorted(by_era.items())},
        "parallel_exam_point_edges": n_parallel,
        "parallel_tests_grammar_point_edges": n_rel,
        "honesty": {
            "not_an_independent_exam_dimension": True,
            "parallel_edges_forbidden": True,
            "note": "九桶是 tests_grammar 派生高频面, 不是第二套考点维",
        },
    }
