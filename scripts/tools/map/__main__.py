"""项目地图 CLI 入口 — 一张可查的"模块/数据/gate/drift/stats"图 (只读聚合).

用法:
  python3 -m scripts.tools.map [doctor|modules|gates|drift|stats] [--json] [--strict]
  默认 doctor (一屏 live 状态, 新 session 接手单一入口)。
  --json   机器可读输出 (供 CI/其它工具)
  --strict 有红 (架构 fail / moth drift / 模块缺失) 退非零码 (供 stop_gate/CI 调用)
"""
from __future__ import annotations

import argparse
import json
import sys

from . import collect

OK, BAD = "✅", "❌"


def _mark(ok: bool) -> str:
    return OK if ok else BAD


def cmd_modules(args) -> bool:
    rows = collect.collect_modules()
    bad = sum(1 for r in rows if r["exists"] is False or r["missing_required"])
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return bad > 0
    print(f"模块/数据/配置契约 ({len(rows)} 条, {bad} 缺失):")
    for r in rows:
        ok = r["exists"] is not False and not r["missing_required"]
        miss = f"  缺{r['missing_required']}" if r["missing_required"] else ""
        owner = f"  ←{r['owner']}" if r["owner"] else ""
        print(f"  {_mark(ok)} [{r['category']:<6}] {r['name']:<24} {r['path'] or ''}{owner}{miss}")
    return bad > 0


def cmd_gates(args) -> bool:
    gates = collect.collect_gates()
    broken = any(g.get("order") is None for g in gates)
    if args.json:
        print(json.dumps(gates, ensure_ascii=False, indent=2))
        return broken
    print(f"M0 gate 契约 ({len(gates)} 门, planner 不执行):")
    for g in gates:
        if g.get("order") is None:
            print(f"  {BAD} {g.get('name')}: {g.get('error')}")
            continue
        print(f"  {g['order']:>2}. {g['name']:<34} 期望={g['expected'] or '?':<6} 失败={g['failure_action'] or '?'}")
    return broken


def cmd_drift(args) -> bool:
    drift = collect.collect_drift()
    if args.json:
        print(json.dumps(drift, ensure_ascii=False, indent=2))
        return _drift_bad(drift)
    if not drift.get("available"):
        print(f"{BAD} moth 不可用: {drift.get('error')}")
        return True
    bad = _drift_bad(drift)
    print(f"{_mark(not bad)} 声称-实况弹仓 moth: verdict={drift.get('verdict')} "
          f"pass={drift.get('pass')} fail={drift.get('fail')} error={drift.get('error')}")
    return bad


def _drift_bad(drift: dict) -> bool:
    if not drift.get("available"):
        return True
    return drift.get("verdict") != "PASS" or drift.get("fail", 0) > 0 or drift.get("error", 0) > 0


def cmd_stats(args) -> bool:
    stats = collect.collect_stats()
    if args.json:
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return not stats.get("available")
    if not stats.get("available"):
        print(f"{BAD} {stats.get('error')}")
        return True
    print("DB 关键计数 (read-only):")
    print(f"  真题 exam_questions: {stats['exam_questions']} "
          f"(辽宁 {stats['exam_liaoning']} · eol {stats['exam_eol']} · 本地PDF {stats['exam_local_pdf']})")
    print(f"  题库 question_bank: {stats['question_bank']} | question_tags: {stats['question_tags']} | tag_dictionary: {stats['tag_dictionary']}")
    print(f"  图谱: {stats['nodes']} 节点 / {stats['edges']} 边 | units: {stats['units']}")
    print(f"  辽宁年度分布 (样本量, D0 透明): {stats['liaoning_by_year']}")
    _warn_thin_years(stats["liaoning_by_year"])
    return False


def _warn_thin_years(by_year: dict, threshold: int = 10) -> None:
    thin = {y: n for y, n in by_year.items() if n < threshold}
    if thin:
        print(f"  ⚠️ 这些年 <{threshold} 题, 不锚定**逐年趋势 slope** (考点分布快照不受影响): {thin}")


def cmd_doctor(args) -> bool:
    arch = collect.collect_arch_audit()
    drift = collect.collect_drift()
    gates = collect.collect_gates()
    stats = collect.collect_stats()
    readiness = collect.collect_readiness_gate()
    if args.json:
        print(json.dumps({"arch_audit": arch, "drift": drift,
                          "gate_count": len(gates), "stats": stats,
                          "readiness_gate": readiness},
                         ensure_ascii=False, indent=2))
        return _doctor_bad(arch, drift, stats, readiness)
    print("=== gaozhong 项目地图 · doctor (live 状态单一入口) ===")
    arch_bad = arch.get("status") == "fail" or not arch.get("available")
    print(f"  {_mark(not arch_bad)} 架构契约审计: {arch.get('status', arch.get('error'))} "
          f"(block={arch.get('block')}, warn={arch.get('warn')})")
    print(f"  {_mark(not _drift_bad(drift))} 声称-实况弹仓: verdict={drift.get('verdict')} "
          f"fail={drift.get('fail')} error={drift.get('error')}")
    print(f"  ·  M0 gate 契约: {len(gates)} 门")
    if stats.get("available"):
        print(f"  ·  真题 {stats['exam_questions']} (辽宁 {stats['exam_liaoning']}) | "
              f"图谱 {stats['nodes']}节点/{stats['edges']}边 | tags {stats['question_tags']}")
        _warn_thin_years(stats["liaoning_by_year"])
    else:
        print(f"  {BAD} DB: {stats.get('error')}")
    if readiness.get("available"):
        rg_ok = readiness.get("ready_for_phase_d", False)
        print(f"  {_mark(rg_ok)} L3 就绪门 (Phase D): "
              f"{'全绿' if rg_ok else '未绿 — ' + str(len(readiness.get('failures', []))) + ' 项阻塞'}")
    else:
        print(f"  {BAD} L3 就绪门: {readiness.get('error')}")
    return _doctor_bad(arch, drift, stats, readiness)


def _doctor_bad(arch: dict, drift: dict, stats: dict, readiness: dict | None = None) -> bool:
    rg = readiness or {}
    rg_bad = rg.get("available") and not rg.get("ready_for_phase_d", False)
    return (arch.get("status") == "fail" or not arch.get("available")
            or _drift_bad(drift) or not stats.get("available") or rg_bad)


_COMMANDS = {
    "doctor": cmd_doctor,
    "modules": cmd_modules,
    "gates": cmd_gates,
    "drift": cmd_drift,
    "stats": cmd_stats,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python3 -m scripts.tools.map",
                                     description="gaozhong 项目地图 (只读聚合)")
    parser.add_argument("command", nargs="?", default="doctor", choices=list(_COMMANDS))
    parser.add_argument("--json", action="store_true", help="机器可读 JSON 输出")
    parser.add_argument("--strict", action="store_true", help="有红退非零码 (供 CI/stop_gate)")
    args = parser.parse_args(argv)
    has_red = _COMMANDS[args.command](args)
    return 1 if (args.strict and has_red) else 0


if __name__ == "__main__":
    raise SystemExit(main())
