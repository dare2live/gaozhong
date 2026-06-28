"""跨阶段 deepens 边 — 初中语法 → 高中语法 (域A; inc3, 10维语法蓝图 K12衔接核心).

中考语篇填空 = 高考语法填空考点全集 (N=2: 2024/2025 辽宁省统一卷实证)。
初中 grammar:jr 节点 → 同 label 高中 grammar 节点, 建 `deepens` 边 (低阶→高阶深化)。
匹配两路: (1) label 精确匹配 (59对); (2) 跨阶段别名 (12对, 初中↔高中课标措辞/颗粒度差异 —
时态去「时」/标点全角/非谓语括注展开/定语从句, 审计HIGH#7 衔接拱心石漏边)。别名数据化 config/grammar_stage_aliases.yaml (§3.5)。
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

_ALIAS_PATH = Path(__file__).resolve().parents[5] / "backend/config/grammar_stage_aliases.yaml"


def _load_aliases() -> dict:
    if not _ALIAS_PATH.exists():
        return {}
    return yaml.safe_load(_ALIAS_PATH.read_text(encoding="utf-8")).get("aliases", {})


def load(con) -> dict:
    """初中 grammar → 高中 grammar deepens 边 (label 精确匹配 + 跨阶段别名)."""
    jr = con.execute(
        "SELECT concept_id, label FROM nodes WHERE concept_id LIKE 'grammar:jr:%'").fetchall()
    hs = {lab: cid for cid, lab in con.execute(
        "SELECT concept_id, label FROM nodes WHERE node_type='grammar' "
        "AND concept_id NOT LIKE 'grammar:jr:%'").fetchall()}
    aliases = _load_aliases()
    ev_exact = json.dumps({"basis": "label_exact", "blueprint": "中考语篇填空↔高考语法填空 10维"},
                          ensure_ascii=False)
    ev_alias = json.dumps({"basis": "stage_alias", "blueprint": "中考语篇填空↔高考语法填空 10维",
                           "note": "初中↔高中课标措辞差异, 人工核验别名"}, ensure_ascii=False)
    edges, n_exact, n_alias = [], 0, 0
    for jr_cid, lab in jr:
        if lab in hs:
            edges.append((jr_cid, hs[lab], "deepens", 1.0, ev_exact)); n_exact += 1
        elif lab in aliases and aliases[lab] in hs:
            edges.append((jr_cid, hs[aliases[lab]], "deepens", 1.0, ev_alias)); n_alias += 1
    if edges:
        con.executemany(
            "INSERT OR IGNORE INTO edges (src_id, dst_id, relation, weight, evidence_json) "
            "VALUES (?, ?, ?, ?, ?)", edges)
    return {"deepens边(初中grammar→高中)": len(edges), "精确匹配": n_exact, "别名匹配": n_alias}
