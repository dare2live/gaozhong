"""内容门引擎 (content_gate 域; 数据驱动单引擎 — 加门=加 content_gates.yaml 一行, 不写代码).

根治散落手写内容门: 把"DB内容 vs 第一手源"的纯SQL断言收进 backend/config/content_gates.yaml,
本引擎统一跑 → 经 CHECKERS 接进 D0 门 + CLI(单一计算点, 可复用)。PDF抽取类内容门走专用 checker。
"""
from __future__ import annotations

from pathlib import Path

import yaml

from .base import Deviation, TruthChecker

_GATES = Path(__file__).resolve().parents[3] / "backend" / "config" / "content_gates.yaml"
_OPS = {"eq": lambda a, e: a == e, "ge": lambda a, e: a >= e, "le": lambda a, e: a <= e}
_SYM = {"eq": "==", "ge": ">=", "le": "<="}


def load_gates() -> list[dict]:
    if not _GATES.exists():
        return []
    return (yaml.safe_load(_GATES.read_text(encoding="utf-8")) or {}).get("gates") or []


def _eval_gate(con, g: dict) -> Deviation | None:
    """跑一条内容门: query 出单值, 比 op/expect; 偏离→Deviation(BLOCK)."""
    op = g.get("op", "eq")
    actual = con.execute(g["query"]).fetchone()[0]
    if _OPS[op](actual, g["expect"]):
        return None
    return Deviation("content_gate", g["id"], "content_mismatch", "BLOCK",
                     f"{g.get('desc', g['id'])}: 实测{actual} 期望{_SYM[op]}{g['expect']} (源={g.get('source', '?')})")


class ContentGateChecker(TruthChecker):
    domain = "content_gate"

    def check(self, con) -> list[Deviation]:
        return [d for g in load_gates() if (d := _eval_gate(con, g))]

    def self_test(self) -> bool:
        """对抗自测: (a)注册表真加载(非空, 防路径错=空门假绿); (b)合成门 query返1 expect=0→必抓, expect=1→不误报."""
        if not load_gates():            # 防空门假绿(路径错则引擎跑0门却报0偏离, 自己犯绿门假绿)
            return False
        import duckdb
        c = duckdb.connect(":memory:")
        bad = {"id": "_t", "query": "SELECT 1", "op": "eq", "expect": 0}
        good = {"id": "_t", "query": "SELECT 1", "op": "eq", "expect": 1}
        caught = _eval_gate(c, bad) is not None
        clean = _eval_gate(c, good) is None
        c.close()
        return caught and clean
