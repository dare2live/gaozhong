"""D0 词×真题考过状态 数值正确性校验 (#12/#13/#14 整改防回归).

锁死 3 个不变量 (单一计算点 exam_vocab + 单一 writer exam_coverage 的产出):
  (a) province 一致性 (#13): 无 word 节点 exam_status∈{core,HV_extra}(辽宁考过类) 而辽宁命中=0。
  (b) 3 源一致单数锁 (#12): node HV_extra 数 == vocab_classification.jsonl「真超纲·辽宁考过」数。
  (c) #14 防回归: gaokao_hit_count_ln 在节点上留存 (>0 个节点带它, 不再被整段 UPDATE 覆盖)。

check 由调用方传入 (data_accuracy_check.check), 失败追加 FAILURES。只读。
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

_JSONL = (Path(__file__).resolve().parent.parent.parent
          / "data" / "structured" / "vocab_classification.jsonl")


def _jsonl_ln_tested_count() -> int:
    """vocab_classification.jsonl「真超纲·辽宁考过」词数 (3 源之一)."""
    if not _JSONL.exists():
        return -1
    n = 0
    for line in _JSONL.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and json.loads(line).get("category") == "真超纲·辽宁考过":
            n += 1
    return n


def _province_violation(con) -> int:
    """exam_status∈{core,HV_extra}(辽宁考过类) 而 gaokao_hit_count_ln=0/缺 的节点数."""
    return con.execute("""
        SELECT COUNT(*) FROM nodes
        WHERE node_type='word'
          AND json_extract_string(attrs_json,'exam_status') IN ('core','HV_extra')
          AND COALESCE(TRY_CAST(json_extract_string(attrs_json,'gaokao_hit_count_ln') AS BIGINT), 0) = 0
    """).fetchone()[0]


def _node_hv_count(con) -> int:
    return con.execute(
        "SELECT COUNT(*) FROM nodes WHERE node_type='word' "
        "AND json_extract_string(attrs_json,'exam_status')='HV_extra'").fetchone()[0]


def _ln_retained(con) -> int:
    """带 gaokao_hit_count_ln 的 word 节点数 (#14: 不应再被覆盖成 0 个)."""
    return con.execute(
        "SELECT COUNT(*) FROM nodes WHERE node_type='word' "
        "AND json_extract_string(attrs_json,'gaokao_hit_count_ln') IS NOT NULL").fetchone()[0]


def check_exam_status(con: duckdb.DuckDBPyConnection, check) -> None:
    """词×真题考过状态 3 不变量 D0 校验 (#12/#13/#14)."""
    print("\n=== (25) 词×真题考过状态 单一计算点一致性 (#12/#13/#14) ===")
    viol = _province_violation(con)
    check("province一致性: core/HV_extra 必辽宁命中>0 (§7, #13)", viol == 0, f"{viol} 违反")

    node_hv = _node_hv_count(con)
    jsonl_ln = _jsonl_ln_tested_count()
    check("3源一致: node HV_extra == jsonl 真超纲·辽宁考过 (#12)",
          node_hv == jsonl_ln, f"node={node_hv} jsonl={jsonl_ln}")

    retained = _ln_retained(con)
    check("gaokao_hit_count_ln 节点留存>0 (#14 防覆盖)", retained > 0, f"{retained} 节点")
