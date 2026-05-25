#!/usr/bin/env python3
"""批次回归测试 — 检查对齐度是否比上次降了, 防 silent regression."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import duckdb

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"
REPORT_DIR = ROOT / "data" / "reports" / "alignment"
REGRESSION_THRESHOLD = 5.0


def run(con: duckdb.DuckDBPyConnection) -> dict:
    from scripts.tools.alignment.exam_alignment_checker import run_all
    current = run_all(con)
    current_score = current["overall"]["score"]
    _save_report(current)
    prev = _load_previous()
    if prev is None:
        return {"regression": False, "current": current_score,
                "previous": None, "delta": 0, "regressions_per_dim": {},
                "detail": "first run, no baseline"}
    prev_score = prev.get("overall", {}).get("score", 0)
    delta = current_score - prev_score
    regression = delta < -REGRESSION_THRESHOLD
    per_dim = {}
    for k in current:
        if k == "overall":
            continue
        c = current[k]["score"]
        p = prev.get(k, {}).get("score", 0)
        if p - c > 3:
            per_dim[k] = {"current": c, "previous": p, "delta": round(c - p, 1)}
    return {
        "regression": regression,
        "current": current_score, "previous": prev_score,
        "delta": round(delta, 1),
        "regressions_per_dim": per_dim,
        "detail": f"Δ={delta:+.1f} ({'REGRESSION' if regression else 'OK'})",
    }


def _save_report(results: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    data = {k: {"score": v["score"], "pass": v["pass"]} for k, v in results.items()}
    path = REPORT_DIR / f"{ts}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_previous() -> dict | None:
    if not REPORT_DIR.exists():
        return None
    files = sorted(REPORT_DIR.glob("*.json"))
    if len(files) < 2:
        return None
    prev_path = files[-2]
    return json.loads(prev_path.read_text(encoding="utf-8"))


def main():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        result = run(con)
    finally:
        con.close()
    status = "❌ REGRESSION" if result["regression"] else "✅ OK"
    print(f"批次回归测试: {status}")
    print(f"  当前: {result['current']:.1f}, 上次: {result['previous']}, Δ={result['delta']:+.1f}")
    if result["regressions_per_dim"]:
        print("  回退维度:")
        for k, v in result["regressions_per_dim"].items():
            print(f"    {k}: {v['previous']:.1f} → {v['current']:.1f} (Δ={v['delta']:+.1f})")
    if result["regression"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
