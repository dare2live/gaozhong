#!/usr/bin/env python3
"""Milestone B 重建脚本：趋势/主题覆盖/图谱连通性一次性报告.

输入源：M0 的真值快照（data/reports/truth_baseline_2021_2025.json）+ exam_questions DB 表.
输出：
- trend_input_snapshot_*.json
- exam_trend_report_*.json
- theme_coverage_report_*.json
- graph_connectivity_report_*.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import sys

ROOT = Path(__file__).resolve().parents[3]
import duckdb  # noqa: E402

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"
REPORT_DIR = ROOT / "data" / "reports"
THEME_POOL_PATH = ROOT / "backend" / "config" / "theme_pool.yaml"
TRUTH_BASELINE_DEFAULT = REPORT_DIR / "truth_baseline_2021_2025.json"
YEAR_WEIGHTS = {2025: 5, 2024: 4, 2023: 3, 2022: 2, 2021: 1.5}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_id_from(value: Any) -> str:
    blob = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha1(blob).hexdigest()[:16]


def load_truth_snapshot(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"truth baseline not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload


def load_exam_rows(con, year_min: int, year_max: int, province_like: str) -> list[dict[str, Any]]:
    rows = con.execute(
        """
        SELECT question_id, year, question_type, raw_question, answer, analysis,
               source_file, source_repo, source_index, province, paper_type
        FROM exam_questions
        WHERE year >= ? AND year <= ? AND province LIKE ?
        ORDER BY year, question_id
        """,
        [year_min, year_max, province_like],
    ).fetchall()
    return [
        {
            "question_id": r[0],
            "year": r[1],
            "question_type": r[2] or "",
            "raw_question": r[3] or "",
            "answer": r[4] or "",
            "analysis": r[5] or "",
            "source_file": r[6],
            "source_repo": r[7],
            "source_index": r[8],
        }
        for r in rows
    ]


def load_theme_pool(path: Path) -> list[str]:
    themes: list[str] = []
    if not path.exists():
        return themes
    collecting = False
    buf = ""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "themes:" in line:
            m = re.search(r"themes:\s*\[(.*)\]", line)
            if m:
                items = m.group(1)
                themes.extend(_split_theme_list(items))
            else:
                collecting = True
                start = line.split("themes:", 1)[1].strip()
                if start.startswith("["):
                    buf = start[1:]
        elif collecting:
            buf += "," + line
            if "]" in line:
                collecting = False
                items = buf.split("]", 1)[0]
                themes.extend(_split_theme_list(items))
                buf = ""
    # keep unique, stable order
    seen: set[str] = set()
    uniq = []
    for t in themes:
        t = t.strip()
        if t and t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq


def _split_theme_list(raw: str) -> list[str]:
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return [p.strip('"\'" ') for p in parts]


def build_theme_coverage(rows: list[dict[str, Any]], themes: list[str]) -> dict[str, Any]:
    theme_stats: dict[str, int] = {t: 0 for t in themes}
    no_theme_rows: list[dict[str, Any]] = []
    total_rows = len(rows)

    for row in rows:
        text = f"{row['raw_question']} {row['answer']} {row['analysis']}".lower()
        hit = []
        for t in themes:
            if t.lower() in text:
                theme_stats[t] += 1
                hit.append(t)
        if not hit:
            no_theme_rows.append(row)

    covered = sum(1 for v in theme_stats.values() if v > 0)
    total = len(theme_stats)
    score = round(100 * covered / total, 2) if total else 0.0
    theme_items = [
        {
            "theme": t,
            "count": c,
            "coverage_ratio": round(c / total_rows, 4) if total_rows else 0.0,
        }
        for t, c in sorted(theme_stats.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    return {
        "version": 1,
        "generated_at": now_iso(),
        "theme_count": total,
        "covered_count": covered,
        "coverage_rate": score,
        "items": theme_items,
        "uncovered": [i["theme"] for i in theme_items if i["count"] == 0],
        "no_theme_question_count": len(no_theme_rows),
        "sample_no_theme": no_theme_rows[:10],
    }


def build_graph_connectivity(con) -> dict[str, Any]:
    nodes = [r[0] for r in con.execute("SELECT concept_id, node_type FROM nodes").fetchall()]
    node_type_map = {k: t for (k, t) in con.execute("SELECT concept_id, node_type FROM nodes").fetchall()}
    node_set = set(nodes)

    rels = con.execute("SELECT relation, COUNT(*) FROM edges GROUP BY relation ORDER BY 2 DESC").fetchall()
    relation_counts = {r: int(c) for r, c in rels}
    edge_rows = con.execute("SELECT src_id, dst_id FROM edges").fetchall()

    adj: dict[str, set[str]] = {n: set() for n in node_set}
    missing_src = 0
    missing_dst = 0
    for s, d in edge_rows:
        if s not in node_set:
            missing_src += 1
        if d not in node_set:
            missing_dst += 1
        if s in node_set and d in node_set:
            adj[s].add(d)
            adj[d].add(s)

    visited: set[str] = set()
    components = []
    for n in node_set:
        if n in visited:
            continue
        q = deque([n])
        visited.add(n)
        comp = []
        while q:
            cur = q.popleft()
            comp.append(cur)
            for nxt in adj.get(cur, ()):
                if nxt not in visited:
                    visited.add(nxt)
                    q.append(nxt)
        components.append(comp)

    components_sizes = [len(c) for c in components]
    components_sizes.sort(reverse=True)
    total_nodes = len(node_set)
    largest = components_sizes[0] if components_sizes else 0

    exam_question_nodes = [f"question:{qid}" for (qid,) in con.execute("SELECT question_id FROM exam_questions ORDER BY question_id").fetchall()]
    missing_exam = [n for n in exam_question_nodes if n not in node_set]

    iso_critical = 0
    critical_types = {"word", "grammar", "question", "phrase", "unit"}
    for n in node_set:
        t = node_type_map.get(n)
        if t in critical_types and not adj.get(n):
            iso_critical += 1

    materials_missing_ref = 0
    materials_by_kind = Counter()
    rows = con.execute("SELECT kind, ref_id FROM course_materials").fetchall()
    for kind, ref_id in rows:
        materials_by_kind[kind] += 1
        if ref_id not in node_set:
            materials_missing_ref += 1

    return {
        "node_count": total_nodes,
        "edge_count": len(edge_rows),
        "relation_count": len(relation_counts),
        "relation_distribution": relation_counts,
        "connected_components": len(components_sizes),
        "largest_component_size": largest,
        "largest_component_ratio": round(largest / total_nodes, 4) if total_nodes else 0.0,
        "component_top_sizes": components_sizes[:10],
        "edge_missing_src": missing_src,
        "edge_missing_dst": missing_dst,
        "exam_question_nodes_missing": len(missing_exam),
        "exam_question_nodes_total": len(exam_question_nodes),
        "critical_isolated_count": iso_critical,
        "course_materials": {
            "total": sum(materials_by_kind.values()),
            "missing_ref": materials_missing_ref,
            "by_kind": dict(materials_by_kind),
        },
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--truth-baseline", default=str(TRUTH_BASELINE_DEFAULT))
    parser.add_argument("--min-year", type=int, default=2021)
    parser.add_argument("--max-year", type=int, default=2025)
    parser.add_argument("--province-like", default="%辽宁%")
    args = parser.parse_args()

    tb_path = Path(args.truth_baseline)
    baseline = load_truth_snapshot(tb_path)
    baseline_run_id = baseline.get("run_id") or "unknown"

    years = list(range(args.min_year, args.max_year + 1))
    payload_anchor = {
        "truth_baseline_run_id": baseline_run_id,
        "truth_baseline_path": str(tb_path),
        "year_range": [args.min_year, args.max_year],
        "province_like": args.province_like,
        "snapshot_source": "scripts/tools/audit/truth_baseline_audit.py",
    }
    run_id = run_id_from(payload_anchor)

    snapshot_path = REPORT_DIR / f"trend_input_snapshot_{run_id}.json"
    trend_report_path = REPORT_DIR / f"exam_trend_report_{run_id}.json"
    theme_report_path = REPORT_DIR / f"theme_coverage_report_{run_id}.json"
    graph_report_path = REPORT_DIR / f"graph_connectivity_report_{run_id}.json"

    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        rows = load_exam_rows(con, args.min_year, args.max_year, args.province_like)
        exam_rows_count = len(rows)

        sys.path.insert(0, str(ROOT))
        from scripts.tools.alignment import exam_pattern_extractor, trend_engine
        trend_input = trend_engine.analyze(
            con,
            min_year=args.min_year,
            max_year=args.max_year,
            province_like=args.province_like,
            year_weights=YEAR_WEIGHTS,
        )
        pattern_input = exam_pattern_extractor.extract(
            con,
            min_year=args.min_year,
            max_year=args.max_year,
            province_like=args.province_like,
            paper_like="%",  # 依 M0 基座已在 DB 侧统一；不重复论文卷型硬筛
            year_weights=YEAR_WEIGHTS,
        )
        graph_input = build_graph_connectivity(con)

        themes = load_theme_pool(THEME_POOL_PATH)
        theme_input = build_theme_coverage(rows, themes)
    finally:
        con.close()

    year_counts = Counter(r["year"] for r in rows)

    snapshot = {
        "run_id": run_id,
        "generated_at": now_iso(),
        "baseline_run_id": baseline_run_id,
        "truth_baseline_path": str(tb_path),
        "input": payload_anchor,
        "query_rows": exam_rows_count,
        "year_counts": {str(k): v for k, v in sorted(year_counts.items())},
        "manifest": baseline.get("manifest", {}),
    }

    trend_report = {
        "run_id": run_id,
        "generated_at": now_iso(),
        "snapshot_run_id": run_id,
        "year_weights": YEAR_WEIGHTS,
        "trend": trend_input,
        "trend_input_rows": exam_rows_count,
        "trend_input_sample": rows[:3],
    }
    trend_report["trend"]["input_snapshot_run_id"] = run_id

    theme_report = {
        "run_id": run_id,
        "generated_at": now_iso(),
        "snapshot_run_id": run_id,
        "theme_pool_count": len(themes),
        "coverage": theme_input,
        "patterns_snapshot": {
            "n_questions": pattern_input["n_questions"],
            "years": pattern_input["years"],
            "global_vocab_top": pattern_input["global_vocab"].get("top50_content_words", [])[:10],
        },
    }

    graph_report = {
        "run_id": run_id,
        "generated_at": now_iso(),
        "snapshot_run_id": run_id,
        "graph": graph_input,
        "nodes": {
            "total": graph_input["node_count"],
            "edge_count": graph_input["edge_count"],
            "relation_count": graph_input["relation_count"],
            "largest_ratio": graph_input["largest_component_ratio"],
        },
    }

    write_json(snapshot_path, snapshot)
    write_json(trend_report_path, trend_report)
    write_json(theme_report_path, theme_report)
    write_json(graph_report_path, graph_report)

    print(f"trend_input_snapshot: {snapshot_path}")
    print(f"exam_trend_report: {trend_report_path}")
    print(f"theme_coverage_report: {theme_report_path}")
    print(f"graph_connectivity_report: {graph_report_path}")
    print(f"row_count={exam_rows_count}, year_counts={dict(year_counts)}")
    print(f"graph largest component = {graph_input['largest_component_ratio']:.1%}")


if __name__ == "__main__":
    main()
