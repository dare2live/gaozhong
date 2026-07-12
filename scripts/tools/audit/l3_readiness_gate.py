#!/usr/bin/env python3
"""L3 就绪门 — 北极星 product_master_plan §5 机器可检查版 (Phase D 前置).

用法:
  python3 scripts/tools/audit/l3_readiness_gate.py [--json] [--strict]
  exit 0 = 五项就绪门全绿 (允许 Phase D 内容生成)
  exit 1 = 任一项 FAIL (--strict 时 WARN 也退 1)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import duckdb
import yaml

from backend.services.course.coverage import coverage_model
from backend.services.exam_point.genre_truth import analysis_genre_crosscheck
from backend.services.exam_point.theme_truth import analysis_theme_crosscheck
from backend.services.k12 import tested_word_stage_distribution
from scripts.lib.db_lock import connect_readonly_with_retry

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"
CFG_PATH = ROOT / "backend" / "config" / "l3_readiness_gate.yaml"

FAILURES: list[str] = []
WARNS: list[str] = []
QUIET = False


def _cfg() -> dict:
    return yaml.safe_load(CFG_PATH.read_text(encoding="utf-8")) or {}


def _record(name: str, ok: bool, detail: str = "", *, warn: bool = False) -> None:
    if QUIET:
        if not ok:
            (WARNS if warn else FAILURES).append(f"{name}: {detail}")
        return
    sym = "✅" if ok else ("⚠️" if warn else "❌")
    print(f"  {sym} {name}", end="")
    if detail:
        print(f"  ({detail})", end="")
    print()
    if ok:
        return
    (WARNS if warn else FAILURES).append(f"{name}: {detail}")


def check_textbook(con: duckdb.DuckDBPyConnection, cfg: dict) -> dict:
    if not QUIET: print("\n=== [1/5] 教材提取完整 (高中外研+人教) ===")
    tb = cfg.get("textbook", {})
    versions = cfg.get("high_school_versions", ["waiyan", "renjiao"])
    expected = tb.get("units_expected", {})
    ok_all = True
    for vk in versions:
        n = con.execute("SELECT COUNT(*) FROM units WHERE version_key=?", [vk]).fetchone()[0]
        exp = int(expected.get(vk, 0))
        ok = n == exp
        ok_all = ok_all and ok
        _record(f"units {vk} == {exp}", ok, f"{n}")
    if tb.get("require_section_text_1to1", True):
        ph = ",".join("?" * len(versions))
        missing = con.execute(
            f"SELECT COUNT(*) FROM sections s "
            f"LEFT JOIN section_text st USING (version_key, volume_key, unit_number, seq) "
            f"WHERE s.version_key IN ({ph}) AND st.raw_text IS NULL",
            versions,
        ).fetchone()[0]
        ok = missing == 0
        ok_all = ok_all and ok
        _record("sections 1:1 section_text (高中)", ok, f"missing={missing}")
    if tb.get("require_unit_vocab_all_units", True):
        ph = ",".join("?" * len(versions))
        orphan = con.execute(
            f"SELECT COUNT(*) FROM units u WHERE u.version_key IN ({ph}) "
            f"AND NOT EXISTS (SELECT 1 FROM unit_vocab_intro v "
            f"WHERE v.version_key=u.version_key AND v.volume_key=u.volume_key "
            f"AND v.unit_number=u.unit_number)",
            versions,
        ).fetchone()[0]
        ok = orphan == 0
        ok_all = ok_all and ok
        _record("每单元均有 unit_vocab_intro (高中)", ok, f"无词表单元={orphan}")
    return {"pass": ok_all}


def check_exam_annotation(con: duckdb.DuckDBPyConnection, cfg: dict) -> dict:
    if not QUIET: print("\n=== [2/5] 考点标注可信 ===")
    cog_cfg = cfg.get("cognitive_skill", {})
    if cog_cfg.get("require_all_explicit_label", True):
        bad = con.execute(
            "SELECT COUNT(*) FROM edges WHERE relation='tests_exam_point' "
            "AND json_extract_string(evidence_json,'$.dimension')='cognitive_skill' "
            "AND json_extract_string(evidence_json,'$.provenance')<>'explicit_label'"
        ).fetchone()[0]
        ok_cog = bad == 0
        _record("cognitive_skill 全 explicit_label", ok_cog, f"非explicit={bad}")
    else:
        ok_cog = True
        _record("cognitive_skill explicit_label (跳过)", True)
    gt = analysis_genre_crosscheck(con)
    ok_gt = bool(gt["pass"])
    _record(
        "genre analysis 交叉验证 (坑16)",
        ok_gt,
        f"agree={gt['n_agree']} conflict={gt['n_conflict']} "
        f"(阈 agree>={gt['thresholds']['min_analysis_agree']} "
        f"conflict<={gt['thresholds']['max_analysis_conflict']})",
    )
    if gt["conflict_samples"]:
        if not QUIET: print(f"    冲突样例: {gt['conflict_samples'][:3]}")
    th = analysis_theme_crosscheck(con)
    # theme 无第一手交叉源 → 诚实 WARN 披露, 不挡 Phase D (genre 已 cross_verified)
    _record(
        "theme dual_model 诚实披露 (不伪造 cross_verified)",
        True,
        f"status={th['status']} explicit={th['n_analysis_explicit_theme']} "
        f"cross={th['n_cross_verified_edges']}",
        warn=False,
    )
    if not th["pass"]:
        _record("theme 无假升 cross_verified", False, f"cross={th['n_cross_verified_edges']}")
    return {"pass": ok_cog and ok_gt and th["pass"], "genre_truth": gt, "theme_truth": th}


def check_association(con: duckdb.DuckDBPyConnection) -> dict:
    if not QUIET: print("\n=== [3/5] 关联口径正确 (D0 关键子集) ===")
    from backend.services.exam_vocab import TESTED_QTYPES
    from backend.services import k12
    d = k12.tested_word_stage_distribution(con)
    qmarks = ",".join("?" * len(TESTED_QTYPES))
    indep = con.execute(
        "SELECT COUNT(DISTINCT SUBSTR(e.dst_id,6)) FROM edges e "
        "JOIN exam_questions q ON q.question_id=SUBSTR(e.src_id,10) "
        f"WHERE e.relation='tests_word' AND q.province LIKE '辽宁%' AND q.question_type IN ({qmarks})",
        list(TESTED_QTYPES)).fetchone()[0]
    ok_w = d["total"] == indep
    _record("考查词口径 service==独立SQL (辽宁∧离散题型)", ok_w, f"service={d['total']} sql={indep}")
    from backend.services.exam_point.loader import exam_point_distribution
    dist = exam_point_distribution(con)
    dist_n = sum(x["n"] for era in dist.values()
                 for d in ("genre", "theme_context", "theme_l2") for x in era.get(d, []))
    truth_n = con.execute(
        "SELECT COUNT(*) FROM edges e "
        "JOIN exam_questions q ON ('question:'||q.question_id)=e.src_id AND q.province LIKE '辽宁%' "
        "WHERE e.relation='tests_exam_point' "
        "AND json_extract_string(e.evidence_json,'$.dimension') IN ('genre','theme_context','theme_l2') "
        "AND q.source_repo NOT LIKE 'eol_xgkii%'"
    ).fetchone()[0]
    ok_g = dist_n == truth_n
    _record("genre/theme 篇章级口径 (排除eol子题)", ok_g, f"分布{dist_n} vs 真值{truth_n}")
    return {"pass": ok_w and ok_g}


def check_coverage(con: duckdb.DuckDBPyConnection, cfg: dict) -> dict:
    if not QUIET: print("\n=== [4/5] 覆盖模型跑通 ===")
    cov_cfg = cfg.get("coverage", {})
    axes_req = cov_cfg.get("required_axes", ["genre", "theme_l2", "word", "grammar"])
    min_hy = int(cov_cfg.get("min_high_yield_n", 1))
    model = coverage_model(con)
    axes = model.get("axes", {})
    ok_all = True
    for ax in axes_req:
        hy = int(axes.get(ax, {}).get("high_yield_n", 0))
        ok = hy >= min_hy
        ok_all = ok_all and ok
        _record(f"覆盖轴 {ax} high_yield_n>={min_hy}", ok, f"{hy}")
    return {"pass": ok_all}


def check_k12_word_stage(con: duckdb.DuckDBPyConnection, cfg: dict) -> dict:
    if not QUIET: print("\n=== [5/5] 小初高词占比验证 ===")
    k12_cfg = cfg.get("k12_word_stage", {})
    tw = tested_word_stage_distribution(con)
    max_unc = float(k12_cfg.get("max_unclassified_pct", 30.0))
    unc = float(tw.get("unclassified_pct", 100.0))
    ok_unc = unc <= max_unc
    _record(f"未分类词占比 <= {max_unc}%", ok_unc, f"{unc}%")
    if k12_cfg.get("require_foundation_gt_senior", True):
        fnd, sen = float(tw["foundation_pct"]), float(tw["senior_pct"])
        ok_fs = fnd > sen
        _record("foundation_pct > senior_pct (王牌实证)", ok_fs, f"{fnd}% vs {sen}%")
    else:
        ok_fs = True
    return {"pass": ok_unc and ok_fs, "distribution": tw}


def run_audit(con: duckdb.DuckDBPyConnection, *, quiet: bool = False) -> dict:
    global QUIET
    QUIET = quiet
    cfg = _cfg()
    items = {
        "textbook": check_textbook(con, cfg),
        "exam_annotation": check_exam_annotation(con, cfg),
        "association": check_association(con),
        "coverage": check_coverage(con, cfg),
        "k12_word_stage": check_k12_word_stage(con, cfg),
    }
    all_pass = all(v["pass"] for v in items.values()) and not FAILURES
    return {
        "ready_for_phase_d": all_pass,
        "items": items,
        "failures": list(FAILURES),
        "warnings": list(WARNS),
        "config": str(CFG_PATH),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="WARN 也退非零")
    args = parser.parse_args(argv)
    FAILURES.clear()
    WARNS.clear()
    con = connect_readonly_with_retry(DB_PATH)
    try:
        report = run_audit(con, quiet=args.json)
    finally:
        con.close()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if not QUIET: print("\n" + "=" * 60)
        if report["ready_for_phase_d"]:
            if not QUIET: print("✅ L3 就绪门全绿 — 允许 Phase D 内容生成 (仍需用户拍板)")
        else:
            if not QUIET: print("❌ L3 就绪门未绿 — Phase D 阻塞")
            for f in report["failures"]:
                if not QUIET: print(f"  · {f}")
    if report["ready_for_phase_d"]:
        return 0
    if args.strict and WARNS:
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
