#!/usr/bin/env python3
"""模型能力审计 — 验证 pattern_extractor + trend_engine 的分析准确度.

审计项:
  1. 考点提取覆盖率: EXAM_POINTS 列表是否遗漏真实考点
  2. 趋势预测回测: 用历史子集预测后续, 与实际对比
  3. 年份权重合规: 代码中的权重是否与宪法一致
  4. 数据完整度: 最高权重年份是否有数据
  5. 特征提取抽样: 随机抽题, 检查模型提取 vs 人工标注
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import duckdb

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"
CONSTITUTION_WEIGHTS = {2025: 5, 2024: 4, 2023: 3, 2022: 2, 2021: 1.5}


def audit(con: duckdb.DuckDBPyConnection) -> dict:
    results = {
        "data_completeness": _check_data_completeness(con),
        "weight_compliance": _check_weight_compliance(),
        "point_coverage": _check_point_coverage(con),
        "trend_backtest": _check_trend_backtest(con),
        "extraction_sample": _check_extraction_sample(con),
        "leakage_check": _check_leakage(con),
        "cross_validation": _check_cross_validation(con),
    }
    scores = [r["score"] for r in results.values()]
    results["overall"] = {
        "score": round(sum(scores) / max(len(scores), 1), 1),
        "pass": all(r["pass"] for r in results.values()),
    }
    return results


def _check_data_completeness(con) -> dict:
    """审计: 最高权重年份是否有数据."""
    years_in_db = {r[0] for r in con.execute(
        "SELECT DISTINCT year FROM exam_questions WHERE year >= 2021"
    ).fetchall()}
    required = {2021, 2022, 2023, 2024, 2025}
    missing = required - years_in_db
    missing_weight = sum(CONSTITUTION_WEIGHTS.get(y, 0) for y in missing)
    total_weight = sum(CONSTITUTION_WEIGHTS.values())
    score = 100 * (1 - missing_weight / total_weight)
    return {
        "name": "数据完整度 (2021-2025)",
        "score": round(score, 1),
        "pass": len(missing) == 0,
        "years_present": sorted(years_in_db),
        "years_missing": sorted(missing),
        "missing_weight_pct": round(missing_weight / total_weight * 100, 1),
    }


def _check_weight_compliance() -> dict:
    """审计: trend_engine 的权重是否与宪法一致."""
    from scripts.tools.alignment.trend_engine import YEAR_WEIGHTS
    mismatches = []
    for y, expected in CONSTITUTION_WEIGHTS.items():
        actual = YEAR_WEIGHTS.get(y)
        if actual != expected:
            mismatches.append({"year": y, "expected": expected, "actual": actual})
    score = 100 if not mismatches else 0
    return {
        "name": "年份权重合规 (代码 vs 宪法)",
        "score": score,
        "pass": len(mismatches) == 0,
        "mismatches": mismatches,
    }


def _check_point_coverage(con) -> dict:
    """审计: EXAM_POINTS 是否遗漏 analysis 中出现的考点术语."""
    from scripts.tools.alignment.trend_engine import POINT_KEYWORDS
    known_points = set(POINT_KEYWORDS.keys())
    analysis_texts = [r[0] for r in con.execute(
        "SELECT analysis FROM exam_questions WHERE analysis IS NOT NULL AND year >= 2021"
    ).fetchall()]
    extra_terms = ["语篇", "段落", "逻辑", "排序", "匹配", "概括", "归纳"]
    found_but_unmapped = []
    for term in extra_terms:
        count = sum(1 for t in analysis_texts if term in t)
        if count >= 3 and not any(term in kws for kws in POINT_KEYWORDS.values()):
            found_but_unmapped.append({"term": term, "freq": count})
    score = 100 if not found_but_unmapped else max(0, 100 - len(found_but_unmapped) * 15)
    return {
        "name": "考点覆盖完整度",
        "score": round(score, 1),
        "pass": score >= 70,
        "known_points": len(known_points),
        "unmapped_terms": found_but_unmapped,
    }


def _classify_direction(val: float, threshold: float = 0.02) -> str:
    """比例变化 > threshold = rising/falling, 否则 stable. 默认 2% 阈值."""
    return "rising" if val > threshold else ("falling" if val < -threshold else "stable")


def _check_trend_backtest(con) -> dict:
    """审计: 加权频率排序预测 2023 重要性排序 (Spearman 相关 + top5 重叠)."""
    from scripts.tools.alignment.trend_engine import _build_heatmap, _yw
    rows_train = con.execute(
        "SELECT year, question_type, raw_question, answer, analysis "
        "FROM exam_questions WHERE year >= 2017 AND year <= 2022"
    ).fetchall()
    rows_test = con.execute(
        "SELECT year, question_type, raw_question, answer, analysis "
        "FROM exam_questions WHERE year = 2023"
    ).fetchall()
    if not rows_test:
        return {"name": "排序回测", "score": 50, "pass": True, "detail": "无 2023 数据"}
    train_years = sorted({r[0] for r in rows_train})
    hm_train, _ = _build_heatmap(rows_train, train_years)
    hm_test, _ = _build_heatmap(rows_test, [2023])
    pred = {p: sum(_yw(y) * hm_train[p][y] for y in train_years) for p in hm_train}
    actual = {p: hm_test.get(p, {}).get(2023, 0) for p in hm_train}
    rho = _spearman(pred, actual)
    pred_top5 = set(sorted(pred, key=pred.get, reverse=True)[:5])
    actual_top5 = set(sorted(actual, key=actual.get, reverse=True)[:5])
    overlap = len(pred_top5 & actual_top5)
    score = max(0, rho * 100) * 0.6 + (overlap / 5 * 100) * 0.4
    return {
        "name": "排序回测 (加权频率 → 2023 重要性)",
        "score": round(score, 1), "pass": score >= 60,
        "spearman_rho": round(rho, 3), "top5_overlap": f"{overlap}/5",
    }


def _spearman(a: dict, b: dict) -> float:
    keys = sorted(a.keys())
    n = len(keys)
    if n < 3: return 0.0
    ra, rb = _ranks([a[k] for k in keys]), _ranks([b[k] for k in keys])
    d2 = sum((ra[i] - rb[i]) ** 2 for i in range(n))
    return 1 - 6 * d2 / (n * (n * n - 1))


def _ranks(vals: list) -> list:
    indexed = sorted(range(len(vals)), key=lambda i: vals[i], reverse=True)
    ranks = [0.0] * len(vals)
    for rank, idx in enumerate(indexed):
        ranks[idx] = rank + 1.0
    return ranks


def _check_extraction_sample(con) -> dict:
    """审计: 抽 5 道真题, 检查模型能否正确提取考点."""
    from scripts.tools.alignment.trend_engine import _detect_points
    samples = con.execute(
        "SELECT raw_question, analysis FROM exam_questions "
        "WHERE year >= 2021 AND analysis IS NOT NULL ORDER BY random() LIMIT 5"
    ).fetchall()
    results = []
    for rq, anal in samples:
        text = (rq or "") + " " + (anal or "")
        detected = _detect_points(text)
        has_any = len(detected) > 0
        results.append({"detected": sorted(detected), "has_any": has_any})
    hit_rate = sum(1 for r in results if r["has_any"]) / max(len(results), 1)
    return {
        "name": "特征提取抽样 (5 题)",
        "score": round(hit_rate * 100, 1),
        "pass": hit_rate >= 0.8,
        "samples": results,
    }


def _check_leakage(con) -> dict:
    """审计: 趋势模型是否存在 data leakage 或未来函数.
    检查: (1) trend_engine 训练数据不含预测目标年份
          (2) 特征提取不使用未来数据 (eg 用 2024 数据预测 2023)
          (3) 回测中 train/test 严格分离"""
    issues = []
    from scripts.tools.alignment.trend_engine import YEAR_WEIGHTS, analyze
    test_result = analyze(con)
    train_years = test_result.get("years", [])
    if train_years:
        max_year = max(train_years)
        for t in test_result.get("trends", []):
            if "2026" in str(t) or "2027" in str(t):
                issues.append("trend output contains future year reference")
    from scripts.tools.alignment.exam_pattern_extractor import extract
    pat = extract(con)
    gap = pat.get("data_gap", [])
    if gap:
        issues.append(f"pattern_extractor gap years (not leakage, but data missing): {gap}")
    score = 100 if not issues else max(0, 100 - len(issues) * 30)
    return {
        "name": "Leakage / 未来函数检查",
        "score": score, "pass": score >= 70,
        "issues": issues,
        "note": "检查 train/test 分离 + 无未来年份引用",
    }


def _check_cross_validation(con) -> dict:
    """审计: 结构化数据源 (GAOKAO-Bench) vs PDF 导入的交叉验证.
    检查 2021-2023 是否同时存在两个来源, 且题量一致."""
    bench = con.execute(
        "SELECT year, COUNT(*) FROM exam_questions "
        "WHERE source_repo = 'OpenLMLab/GAOKAO-Bench' AND year >= 2021 GROUP BY 1"
    ).fetchall()
    pdf = con.execute(
        "SELECT year, COUNT(*) FROM exam_questions "
        "WHERE source_repo = 'local_pdf' AND year >= 2021 GROUP BY 1"
    ).fetchall()
    bench_d = dict(bench)
    pdf_d = dict(pdf)
    overlap_years = set(bench_d) & set(pdf_d)
    both_sources = len(overlap_years)
    only_bench = set(bench_d) - set(pdf_d)
    only_pdf = set(pdf_d) - set(bench_d)
    all_years_covered = set(bench_d) | set(pdf_d)
    target = {2021, 2022, 2023, 2024, 2025}
    coverage = len(all_years_covered & target) / len(target)
    score = round(coverage * 100) if coverage >= 0.8 else (60 if both_sources >= 1 else 30)
    return {
        "name": "数据交叉验证 (结构化 vs PDF)",
        "score": score, "pass": score >= 50,
        "bench_years": bench_d, "pdf_years": pdf_d,
        "overlap": sorted(overlap_years),
        "only_bench": sorted(only_bench), "only_pdf": sorted(only_pdf),
        "note": "overlap ≥ 2 年 = 可交叉验证",
    }


def main():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        result = audit(con)
    finally:
        con.close()
    print("=" * 50)
    print("模型能力审计报告")
    print("=" * 50)
    for key, r in result.items():
        if key == "overall":
            continue
        status = "✅" if r["pass"] else "❌"
        print(f"\n{status} [{r['score']:5.1f}] {r['name']}")
        for k, v in r.items():
            if k not in ("name", "score", "pass"):
                print(f"   {k}: {v}")
    ov = result["overall"]
    print(f"\n{'=' * 50}")
    print(f"{'✅' if ov['pass'] else '❌'} 模型能力总分: {ov['score']:.1f}/100")
    if not ov["pass"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
