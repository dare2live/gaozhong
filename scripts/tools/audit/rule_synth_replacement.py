#!/usr/bin/env python3
"""rule_synth 全量替换 — 清退历史无解析样本并按当前生成策略重建.

执行：
    python3 scripts/tools/audit/rule_synth_replacement.py [--json]

输出：
  - 终端报告
  - data/reports/rule_synth_replacement_<ts>.json
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import duckdb

from backend.services.question_bank import loader

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"
REPORT_DIR = ROOT / "data" / "reports"


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _count_by_type(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    rows = con.execute(
        "SELECT question_type, COUNT(*) FROM question_bank WHERE origin='rule_synth' GROUP BY question_type"
    ).fetchall()
    return {k: v for k, v in rows}


def _sample_ids(con: duckdb.DuckDBPyConnection, limit: int = 50) -> list[dict]:
    return [
        {"qb_id": qb_id, "question_type": qtype, "analysis_len": len((analysis or ""))}
        for qb_id, qtype, analysis in con.execute(
            "SELECT qb_id, question_type, analysis FROM question_bank WHERE origin='rule_synth' ORDER BY qb_id LIMIT ?",
            [limit],
        ).fetchall()
    ]


def _missing_after(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    rows = con.execute("""
        SELECT question_type, COUNT(*) FILTER (WHERE analysis IS NULL OR TRIM(analysis) = '')
        FROM question_bank
        WHERE origin='rule_synth'
        GROUP BY question_type
    """).fetchall()
    return {k: v for k, v in rows}


def _delete_rule_synth(con: duckdb.DuckDBPyConnection) -> int:
    ids = [r[0] for r in con.execute("SELECT qb_id FROM question_bank WHERE origin='rule_synth'").fetchall()]
    if not ids:
        return 0
    placeholders = ",".join("?" * len(ids))
    con.execute(f"DELETE FROM question_tags WHERE qb_id IN ({placeholders})", ids)
    con.execute(f"DELETE FROM question_bank WHERE qb_id IN ({placeholders})", ids)
    return len(ids)


def run() -> dict:
    con = duckdb.connect(str(DB_PATH))
    before_total = con.execute("SELECT COUNT(*) FROM question_bank WHERE origin='rule_synth'").fetchone()[0]
    before_by_type = _count_by_type(con)
    before_missing = _missing_after(con)
    before_sample = _sample_ids(con)

    deleted = _delete_rule_synth(con)
    regen = loader.load_synthesized_samples(con, samples_per_type=15)
    after_total = con.execute("SELECT COUNT(*) FROM question_bank WHERE origin='rule_synth'").fetchone()[0]
    after_by_type = _count_by_type(con)
    after_missing = _missing_after(con)
    after_sample = _sample_ids(con)

    result = {
        "run_id": _timestamp(),
        "before": {
            "total": before_total,
            "by_type": before_by_type,
            "analysis_missing_by_type": before_missing,
            "sample": before_sample,
        },
        "action": {
            "deleted": deleted,
            "regen": regen,
        },
        "after": {
            "total": after_total,
            "by_type": after_by_type,
            "analysis_missing_by_type": after_missing,
            "sample": after_sample,
        },
    }
    report_path = REPORT_DIR / f"rule_synth_replacement_{result['run_id']}.json"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    con.close()
    return {"report_path": str(report_path), "result": result}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="rule_synth replacement")
    parser.add_argument("--json", action="store_true", help="only output json")
    args = parser.parse_args()

    payload = run()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(f"rule_synth replacement completed, report -> {payload['report_path']}")
    print(json.dumps(payload["result"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
