"""初中课标语法项 → grammar 节点 (域A canonical; inc2, 模块化单一计算点).

命名空间 `grammar:jr:<item_id>` 防与高中 grammar(grammar:一...) 碰撞; attrs 带 stage=初中 + depth + understand_only。
在 canonical.build_all 之后调 (Layer 3x)。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
S = ROOT / "data" / "junior_high" / "structured"


def load(con) -> dict:
    """初中语法节点入库 (grammar:jr: 命名空间, stage=初中)."""
    p = S / "grammar_items.jsonl"
    if not p.exists():
        return {"初中 grammar 节点": 0}
    rows = []
    for line in p.open(encoding="utf-8"):
        r = json.loads(line)
        cid = f"grammar:jr:{r['item_id']}"
        attrs = {"stage": "初中", "depth": r.get("depth"), "level": r.get("level"),
                 "understand_only": r.get("understand_only", False), "source": "yiwu_2022_grammar"}
        rows.append((cid, "grammar", r["label"], json.dumps(attrs, ensure_ascii=False)))
    if rows:
        con.executemany("INSERT OR IGNORE INTO nodes VALUES (?, ?, ?, ?)", rows)
    return {"初中 grammar 节点": len(rows)}
