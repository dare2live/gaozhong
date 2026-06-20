"""初中课标 + 沪教词 → word 节点 (域A canonical; inc2, 模块化单一计算点).

合并 curriculum_vocab(word→stage 小学/初中) + hujiao_vocab(初中); 同词取最早 stage。
**已是高中节点的跳过** (1803 重叠词的 stage 回填在 inc3 stage_refined; 此处只新建初中独有 112)。
在 canonical.build_all (replace-all) **之后** 调 (Layer 3x), 否则被 replace 删。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
S = ROOT / "data" / "junior_high" / "structured"
_RANK = {"小学": 0, "初中": 1}


def junior_word_stages() -> dict[str, str]:
    """{word: 最早 stage} — 课标(stage列) + 沪教(初中). 同词取 rank 最小(小学<初中)."""
    best: dict[str, str] = {}
    for fn, default_stage in (("curriculum_vocab.jsonl", None), ("hujiao_vocab.jsonl", "初中")):
        p = S / fn
        if not p.exists():
            continue
        for line in p.open(encoding="utf-8"):
            r = json.loads(line)
            w, st = r["word"], (r.get("stage") or default_stage)
            if st and (w not in best or _RANK.get(st, 9) < _RANK.get(best[w], 9)):
                best[w] = st
    return best


def load(con) -> dict:
    """初中独有 word 节点入库 (stage 标注; 重叠高中词跳过留 inc3 回填)."""
    existing = {r[0] for r in con.execute("SELECT concept_id FROM nodes WHERE node_type='word'").fetchall()}
    jr = junior_word_stages()
    rows = []
    for w, st in jr.items():
        cid = f"word:{w}"
        if cid in existing:
            continue
        rows.append((cid, "word", w,
                     json.dumps({"stage": st, "source": "junior_curriculum_hujiao"}, ensure_ascii=False)))
    if rows:
        con.executemany("INSERT OR IGNORE INTO nodes VALUES (?, ?, ?, ?)", rows)
    return {"初中独有 word 节点新增": len(rows), "重叠高中节点跳过(留inc3回填)": len(jr) - len(rows)}
