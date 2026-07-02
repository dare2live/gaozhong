"""端点 HTTP 契约检查 (审计 MAJOR 修复: 74% 端点无契约断言 → 契约数据化收口).

单一真相源 = backend/config/endpoint_contracts.yaml (契约数据化, 不写零散 shell 断言);
本模块 in-process 直调 ALL_ROUTES[path](params) (handler 全走 db_ro 只读连接, 无副作用),
不起 http server。每端点断言:
  1. 不抛异常
  2. 顶层返回类型匹配 (dict / list)
  3. required_keys 全在 (dict 型; 2-4 个语义键抽样)
  4. 无 'error' 键 (除非契约 allow_error — 仅 POST-body 端点 GET 探测 / 已知数据缺口)
覆盖率自检: ALL_ROUTES 有新端点而 yaml 未写契约 → FAIL (防"未断言维度永远绿");
反向亦断言 (契约指向已删端点 = 陈旧契约 → FAIL)。

用法:
  standalone:  python3 scripts/lib/endpoint_contract_check.py   (逐端点 PASS/FAIL, exit code)
  集成:        check_endpoint_contracts(con, check)             (d0_*_check 同款签名)
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
CONTRACTS_PATH = ROOT / "backend" / "config" / "endpoint_contracts.yaml"


def load_contracts() -> dict[str, dict]:
    with open(CONTRACTS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)["contracts"]


def _call(handler, params: dict) -> tuple[object, str | None]:
    """直调 handler; 返回 (response, exception_str)。"""
    try:
        return handler(params), None
    except Exception as e:  # noqa: BLE001 — "不抛异常"本身是契约, 任何异常归 FAIL 不炸整轮
        return None, f"{type(e).__name__}: {e}"


def _dict_violations(resp: dict, c: dict) -> list[str]:
    """dict 型响应的键级断言 (required_keys 全在 + 无 error 键除非 allow_error)。"""
    out: list[str] = []
    missing = [k for k in (c.get("required_keys") or []) if k not in resp]
    if missing:
        out.append(f"缺关键键 {missing}")
    if "error" in resp and not c.get("allow_error"):
        out.append(f"error 键: {str(resp['error'])[:100]}")
    return out


def _violations(resp: object, exc: str | None, c: dict) -> list[str]:
    """单端点契约断言; 返回违规描述列表 (空 = PASS)。"""
    if exc:
        return [f"抛异常 {exc}"]
    want = list if c.get("type") == "list" else dict
    if not isinstance(resp, want):
        return [f"类型 {type(resp).__name__} != {want.__name__}"]
    return _dict_violations(resp, c) if isinstance(resp, dict) else []


def run_contracts() -> tuple[list[tuple[str, list[str]]], set[str], set[str]]:
    """跑全部契约; 返回 (results=[(path, violations)], uncovered, stale)。

    uncovered = ALL_ROUTES 有端点但无契约 (新端点没写契约 → 红);
    stale     = 契约指向已不存在的端点。skip 契约不调用但计入覆盖。
    """
    from backend.api.routes import ALL_ROUTES
    contracts = load_contracts()
    skipped = {p for p, c in contracts.items() if (c or {}).get("skip")}
    uncovered = set(ALL_ROUTES) - set(contracts) - skipped
    stale = set(contracts) - set(ALL_ROUTES)
    results: list[tuple[str, list[str]]] = []
    for path in sorted(contracts):
        c = contracts[path] or {}
        if path in stale or path in skipped:
            continue
        resp, exc = _call(ALL_ROUTES[path], c.get("params") or {})
        results.append((path, _violations(resp, exc, c)))
    return results, uncovered, stale


def check_endpoint_contracts(con, check) -> None:  # noqa: ARG001 — con 保持 d0 签名; handler 自开 db_ro
    print("\n=== 端点 HTTP 契约 (endpoint_contracts.yaml 数据化; in-process 直调 ALL_ROUTES) ===")
    results, uncovered, stale = run_contracts()
    fails = [f"{p}: {'; '.join(v)}" for p, v in results if v]
    check(f"全端点契约 (n={len(results)}: 不抛异常/类型/关键键/无error)",
          not fails, " | ".join(fails[:5]))
    check("契约覆盖率 (新端点必写契约, ALL_ROUTES - contracts - skip == 空)",
          not uncovered, f"无契约端点: {sorted(uncovered)[:8]}")
    check("无陈旧契约 (契约端点都还在 ALL_ROUTES)", not stale, f"陈旧: {sorted(stale)[:8]}")


def main() -> int:
    sys.path.insert(0, str(ROOT))
    quiet = "--quiet" in sys.argv                       # moth 断言模式: 只出汇总行 (ALL PASS 锚)
    results, uncovered, stale = run_contracts()
    n_fail = 0
    for path, viols in results:
        if viols:
            n_fail += 1
            print(f"FAIL {path} — {'; '.join(viols)}")
        elif not quiet:
            print(f"PASS {path}")
    for p in sorted(uncovered):
        n_fail += 1
        print(f"FAIL {p} — ALL_ROUTES 有此端点但契约缺失 (endpoint_contracts.yaml 补契约)")
    for p in sorted(stale):
        n_fail += 1
        print(f"FAIL {p} — 契约指向已删端点 (清理 endpoint_contracts.yaml)")
    n_pass = len(results) - sum(1 for _, v in results if v)
    print(f"\n{'ALL PASS — ' if not n_fail else ''}{n_pass}/{len(results)} PASS, "
          f"{n_fail} FAIL (含覆盖率/陈旧 {len(uncovered) + len(stale)})")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
