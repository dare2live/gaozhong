"""D0 K12 as-served correctness (k12.stage_unstaged_disclosure + k12.blueprint; 坑17 新数据必 moth AND D0 双门).

从 data_accuracy_check 委托 (避 god-module Rule8); check 由调用方传入, 失败追加 FAILURES。
跨源核验 (非同源重言): service 输出 vs 独立 SQL 重算 — 防口径漂移
(如丢 node_type 过滤让 grammar 混进 word 计数 / blueprint label JOIN 丢对) 而门不知。
"""
from __future__ import annotations

import duckdb


def check_k12_served(con: duckdb.DuckDBPyConnection, check) -> None:
    """k12 stage 披露口径闭合 + 语法蓝图 as-served 5 项 D0 校验."""
    print("\n=== (37) K12 as-served (stage 披露口径闭合 + 语法蓝图, k12 服务跨源) ===")
    from backend.services import k12
    d = k12.stage_unstaged_disclosure(con)
    n_words = con.execute("SELECT COUNT(*) FROM nodes WHERE node_type='word'").fetchone()[0]
    check("stage披露 total_words==独立SQL(word节点计数, as-served)", d["total_words"] == n_words,
          f"svc={d['total_words']} sql={n_words}")
    check("staged+unstaged==total_words (披露无词被丢)", d["staged"] + d["unstaged"] == d["total_words"],
          f"{d['staged']}+{d['unstaged']} vs {d['total_words']}")
    reason_sum = sum(d["unstaged_by_reason"].values())
    check("by_reason 求和==unstaged (未分阶披露口径闭合)", reason_sum == d["unstaged"],
          f"sum={reason_sum} unstaged={d['unstaged']}")
    bp = k12.blueprint(con)
    n_deepens = con.execute("SELECT COUNT(*) FROM edges WHERE relation='deepens'").fetchone()[0]
    check("蓝图 pairs==deepens 边独立SQL (label JOIN 不丢对)",
          bp["n"] == len(bp["pairs"]) == n_deepens,
          f"n={bp['n']} pairs={len(bp['pairs'])} sql={n_deepens}")
    n_empty = sum(1 for p in bp["pairs"]
                  if not (p.get("junior") or "").strip() or not (p.get("senior") or "").strip())
    check("蓝图每对 junior/senior label 非空", n_empty == 0, f"{n_empty} 对空label")
