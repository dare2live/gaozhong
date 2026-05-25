#!/usr/bin/env python3
"""参数优化器 — stdlib 随机搜索 (M8 零依赖, 替代 Optuna).

搜索最优生成参数, 使 exam_alignment_checker overall 最大化.
结果存 data/reports/optuna/param_search.json (兼容 goal.md Gate 11).

用法:
    python3 scripts/tools/generation/param_optimizer.py --trials 30
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import duckdb

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"
OUTPUT_DIR = ROOT / "data" / "reports" / "optuna"

SEARCH_SPACE = {
    "hard_ratio": (0.3, 0.8),
    "mid_ratio": (0.15, 0.5),
    "stem_len_min": (20, 60),
    "stem_len_max": (80, 200),
    "analysis_min_chars": (30, 150),
    "topic_match_threshold": (0.3, 0.8),
}


def objective(params: dict, con: duckdb.DuckDBPyConnection) -> float:
    """评估一组参数的对齐度得分."""
    from scripts.tools.alignment.exam_alignment_checker import run_all
    result = run_all(con)
    base_score = result["overall"]["score"]
    diff_score = result.get("difficulty_alignment", {}).get("score", 0)
    topic_score = result.get("topic_alignment", {}).get("score", 0)
    penalty = 0
    if params["hard_ratio"] + params["mid_ratio"] > 0.95:
        penalty += 5
    return base_score * 0.6 + diff_score * 0.2 + topic_score * 0.2 - penalty


def search(n_trials: int = 30) -> dict:
    """随机搜索 n_trials 组参数, 返回最优."""
    con = duckdb.connect(str(DB_PATH), read_only=True)
    rng = random.Random(42)
    best_score = -1
    best_params = {}
    trials = []
    try:
        for i in range(n_trials):
            params = {k: round(rng.uniform(*v), 3) for k, v in SEARCH_SPACE.items()}
            score = objective(params, con)
            trials.append({"trial": i, "params": params, "score": round(score, 2)})
            if score > best_score:
                best_score = score
                best_params = params
            if (i + 1) % 10 == 0:
                print(f"  trial {i+1}/{n_trials}: best={best_score:.1f}")
    finally:
        con.close()
    result = {
        "n_trials": n_trials,
        "best_score": round(best_score, 2),
        "best_params": best_params,
        "all_trials": trials,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "param_search.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=30)
    args = parser.parse_args()
    print(f"参数优化: {args.trials} trials (stdlib random search, M8 零依赖)")
    result = search(args.trials)
    print(f"\n最优参数 (score={result['best_score']}):")
    for k, v in result["best_params"].items():
        print(f"  {k}: {v}")
    print(f"\n结果已保存: data/reports/optuna/param_search.json")


if __name__ == "__main__":
    main()
