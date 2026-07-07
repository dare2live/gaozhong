"""沪教初中短语/句型/表达 → phrases 表 (2026-07-07 补 STEP1 缺口, 域A canonical).

产物源: data/junior_high/structured/hujiao_phrases.jsonl (scripts/extract_hujiao_phrases.py
一次性预处理, 复用高中 backend.services.extraction.phrases._scan_text 同一套规则/词表,
颗粒度与高中对齐)。写入**已有** phrases 表(不新建表), version_key='hujiao', 与高中
renjiao/waiyan 物理共存同一张表, 靠 version_key 分组即可算"初中已学 vs 高中新学"。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "data" / "junior_high" / "structured" / "hujiao_phrases.jsonl"


def load(con) -> dict:
    con.execute("DELETE FROM phrases WHERE version_key = 'hujiao'")
    if not SRC.exists():
        return {"hujiao短语新增": 0, "跳过": "源文件不存在"}
    n = 0
    with SRC.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            con.execute(
                "INSERT INTO phrases VALUES (nextval('phrase_id_seq'), 'hujiao', ?, ?, ?, ?, ?, ?)",
                [r["volume_key"], r["unit_number"], r["canonical"], r["phrase_type"],
                 r["evidence"], None],
            )
            n += 1
    return {"hujiao短语新增": n}
