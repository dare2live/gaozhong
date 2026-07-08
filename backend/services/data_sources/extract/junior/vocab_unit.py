"""沪教词表 unit级归属 → unit_vocab_intro (Phase E4 knowledge lineage 补全).

数据源: scripts/extract_hujiao_vocab_unit.py 产物(卷末"Words and expressions in each
unit"附录, 逐单元真实归属, 非估算) + hujiao_vocab.jsonl(pos/zh_def, 已有产物, 不重复
抽取, Rule1单一计算点)。

raw_marker 诚实留空(NULL): 原文部分词条带"*"前缀标记(如'*blog', 疑似"拓展/不要求掌握"
类标注), 现有 _ENTRY 正则(scripts/extract_hujiao_vocab.py, 抽hujiao_vocab.jsonl的既有
产物同样受限)要求词条以字母开头, 带"*"前缀的词条本就未被两份产物任一收录 — 不是本模块
新引入的缺口, 诚实留空不杜撰。

须在 junior/sections.py(units表就绪) 之后调; 调用方(init_db.py)须在此之后**重新调用**
links.build_introduces_word(con) 才能让本表数据流入 introduces_word 边(该函数是全量
replace, 高中Layer3首次调用时hujiao的units还不存在, 故必须在Layer3x本模块之后再调一次,
两次调用是同一份Rule1单一计算逻辑, 非重复实现)。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
S = ROOT / "data" / "junior_high" / "structured"
_VERSION = "hujiao"


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.open(encoding="utf-8")]


def load(con) -> dict:
    """hujiao_vocab_unit.jsonl(单元归属) JOIN hujiao_vocab.jsonl(pos/zh_def) → unit_vocab_intro.

    in_curriculum 计算口径同 backend/orchestrator/extract.py::run_vocab (Rule1单一计算点):
    词∈cefr_vocab 才算真, 不硬编码True(义务教育课标≠cefr_vocab全集, 教材本就有真超纲词)。
    """
    con.execute("DELETE FROM unit_vocab_intro WHERE version_key = ?", [_VERSION])
    cefr = {r[0].lower() for r in con.execute("SELECT word FROM cefr_vocab").fetchall()}
    gloss = {r["word"]: r for r in _load_jsonl(S / "hujiao_vocab.jsonl")}
    unit_rows = _load_jsonl(S / "hujiao_vocab_unit.jsonl")
    seen: set[tuple] = set()
    rows = []
    for r in unit_rows:
        key = (r["volume_key"], r["unit_number"], r["word"])
        if key in seen:
            continue
        seen.add(key)
        g = gloss.get(r["word"], {})
        rows.append((_VERSION, r["volume_key"], r["unit_number"], r["word"],
                      r["word"].lower() in cefr, g.get("pos"), g.get("zh_def"), None))
    if rows:
        con.executemany(
            "INSERT INTO unit_vocab_intro "
            "(version_key, volume_key, unit_number, word, in_curriculum, pos, zh_def, raw_marker) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
    n_no_gloss = sum(1 for r in unit_rows if r["word"] not in gloss)
    return {"初中unit_vocab_intro新增": len(rows), "无法匹配释义(诚实计数)": n_no_gloss}
