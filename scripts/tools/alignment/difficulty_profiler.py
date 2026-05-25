#!/usr/bin/env python3
"""难度曲线对比 — 按题型分组, 真题 vs 生成题的 easy/mid/hard 分布."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import duckdb

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"

DIFF_ORDER = ["easy", "mid", "hard"]


def profile(con: duckdb.DuckDBPyConnection) -> dict:
    real = _load_dist(con, "origin = 'real'")
    gen = _load_dist(con, "origin IN ('listening_exercise','writing_exercise','rule_synth')")

    real_agg = _aggregate(real)
    gen_agg = _aggregate(gen)
    r_total = max(sum(real_agg.values()), 1)
    g_total = max(sum(gen_agg.values()), 1)
    agg_dev = sum(abs(real_agg.get(d, 0) / r_total - gen_agg.get(d, 0) / g_total)
                  for d in DIFF_ORDER) / 2

    types = sorted(set(real) & set(gen))
    per_type = {}
    for qt in types:
        r, g = real[qt], gen[qt]
        rt, gt = max(sum(r.values()), 1), max(sum(g.values()), 1)
        dev = sum(abs(r.get(d, 0) / rt - g.get(d, 0) / gt) for d in DIFF_ORDER) / 2
        per_type[qt] = {"real": r, "gen": g, "deviation": round(dev, 3)}

    score = max(0, 100 * (1 - agg_dev * 2))
    return {
        "name": "难度分布对比",
        "score": round(score, 1),
        "pass": score >= 50,
        "real_aggregate": real_agg,
        "gen_aggregate": gen_agg,
        "aggregate_deviation": round(agg_dev, 3),
        "per_type": per_type,
    }


def _aggregate(dist: dict[str, dict[str, int]]) -> dict[str, int]:
    agg: dict[str, int] = {}
    for d in dist.values():
        for k, v in d.items():
            agg[k] = agg.get(k, 0) + v
    return agg


def _load_dist(con, where: str) -> dict[str, dict[str, int]]:
    rows = con.execute(
        f"SELECT question_type, difficulty, COUNT(*) FROM question_bank "
        f"WHERE {where} GROUP BY 1, 2"
    ).fetchall()
    out: dict[str, dict[str, int]] = {}
    for qt, diff, n in rows:
        out.setdefault(qt, {})[diff or "unknown"] = n
    return out


def main():
    import argparse
    parser = argparse.ArgumentParser(description="难度曲线对比")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        result = profile(con)
    finally:
        con.close()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    dev = result["aggregate_deviation"]
    print(f"难度分布对比: {result['score']:.1f}/100 (aggregate deviation={dev})")
    def fmt(d): return "/".join(f"{d.get(k,0)}" for k in DIFF_ORDER)
    print(f"  真题 (e/m/h): {fmt(result['real_aggregate'])}")
    print(f"  生成 (e/m/h): {fmt(result['gen_aggregate'])}")
    if result["per_type"]:
        print(f"\n共有题型 ({len(result['per_type'])}):")
        for qt, v in sorted(result["per_type"].items()):
            marker = " ⚠️" if v["deviation"] > 0.3 else ""
            print(f"  {qt:<20} 真题={fmt(v['real'])} 生成={fmt(v['gen'])} dev={v['deviation']}{marker}")


if __name__ == "__main__":
    main()
