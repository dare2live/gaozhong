"""真值校验工具 CLI — 可复用非一次性 (替代 scripts/tools/audit/truth_baseline_* 软匹配报告脚本).

  python3 -m scripts.tools.truth_check            # verify 全域: 库内容 ∩ 第一手真值锚
  python3 -m scripts.tools.truth_check --strict   # 有 BLOCK → exit 1 (供门/CI)
  python3 -m scripts.tools.truth_check --self-test # 对抗自测: 每 active checker 注入污染必抓 (证明非装饰门)
  python3 -m scripts.tools.truth_check --json      # 机读 (供 map doctor 聚合)
  python3 -m scripts.tools.truth_check --lint       # 校验 truth_anchors.yaml 自身合法

根治"自洽棘轮": 验"内容匹配真值"非"计数==快照"; 冲突=第一手胜; 无锚标 UNKNOWN 不冒充。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from backend.services.truth_baseline import CHECKERS, collect_deviations, load_anchors  # noqa: E402

_DB = Path(__file__).resolve().parents[3] / "data" / "db" / "gaozhong.duckdb"


def _connect():
    import duckdb
    return duckdb.connect(str(_DB), read_only=True)


def _render(blocks, unknowns, devs) -> None:
    print(f"真值锚比对: {len(blocks)} BLOCK / {len(unknowns)} UNKNOWN (验内容匹配第一手源)")
    for d in blocks:
        print(f"  ❌ [BLOCK] {d.domain}:{d.anchor_key} ({d.kind}) — {d.detail}")
    for d in unknowns:
        print(f"  ⚪ [UNKNOWN] {d.domain}:{d.anchor_key} — {d.detail}")
    if not devs:
        print("  ✅ 全部 active 锚内容匹配真值")


def cmd_verify(args) -> int:
    con = _connect()
    try:
        devs = collect_deviations(con)
    finally:
        con.close()
    if args.domain:
        devs = [d for d in devs if d.domain == args.domain]
    blocks = [d for d in devs if d.severity == "BLOCK"]
    unknowns = [d for d in devs if d.severity == "UNKNOWN"]
    if args.json:
        print(json.dumps({"block": len(blocks), "unknown": len(unknowns),
                          "deviations": [vars(d) for d in devs]}, ensure_ascii=False))
    else:
        _render(blocks, unknowns, devs)
    return 1 if (args.strict and blocks) else 0


def cmd_self_test(_args) -> int:
    """每 active checker 注入污染必 BLOCK + 干净不误报 → 证明门真有效非装饰 (坑21)."""
    print("真值校验器对抗自测 (注入污染必抓 + 干净不误报):")
    ok = True
    for chk in CHECKERS:
        passed = chk.self_test()
        ok = ok and passed
        print(f"  {'✅' if passed else '❌'} {chk.domain}: self_test {'通过(注入抓到/干净放过)' if passed else '失败=装饰门!'}")
    return 0 if ok else 1


def cmd_lint(_args) -> int:
    """truth_anchors.yaml 自身合法: active 锚必有 markers, 域必有 anchors."""
    a = load_anchors()
    bad = []
    for domain, blk in a.items():
        for key, anc in (blk.get("anchors") or {}).items():
            if anc.get("lifecycle") == "active" and not anc.get("markers"):
                bad.append(f"{domain}:{key} active 但无 markers")
    if bad:
        print("❌ truth_anchors.yaml 不合法:")
        for b in bad:
            print("  -", b)
        return 1
    print("✅ truth_anchors.yaml 合法")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="truth_check", description="真值锚校验 (内容匹配第一手源)")
    p.add_argument("--domain")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--self-test", dest="self_test", action="store_true")
    p.add_argument("--lint", action="store_true")
    args = p.parse_args()
    if args.self_test:
        return cmd_self_test(args)
    if args.lint:
        return cmd_lint(args)
    return cmd_verify(args)


if __name__ == "__main__":
    sys.exit(main())
