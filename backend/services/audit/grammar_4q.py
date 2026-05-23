"""课标语法 × 真题 4 象限分类 (类比 vocab exam_coverage 4q).

中文术语 grep 真题题面 + 解析 (analysis) 命中:
  - 定语从句 / 状语从句 / 宾语从句 / 主语从句 / 表语从句 / 同位语从句
  - 非谓语动词 / 动名词 / 不定式 / 分词
  - 时态: 现在完成 / 过去完成 / 一般将来 / 现在进行 / 过去进行 ...
  - 被动语态 / 虚拟语气 / 倒装 / 强调 / 省略
  - 主谓一致 / 比较级 / 最高级 / 比较句

写 grammar.attrs.exam_status (类似 vocab):
  core      : 课标 ∩ 真题考过
  standard  : 课标内但真题未印证 (近年)
"""
from __future__ import annotations

import re

import duckdb

from ._common import finding

# 关键词 → grammar label substring (用于反向 lookup grammar_items.label)
TERM_TO_LABEL_KEYWORD = {
    "定语从句":   "定语从句",
    "状语从句":   "状语从句",
    "宾语从句":   "宾语从句",
    "主语从句":   "主语从句",
    "表语从句":   "表语从句",
    "同位语从句": "同位语从句",
    "非谓语":     "非谓语",
    "动名词":     "动名词",
    "不定式":     "动词不定式",
    "分词":       "分词",
    "现在完成":   "现在完成",
    "过去完成":   "过去完成",
    "一般将来":   "一般将来",
    "现在进行":   "现在进行",
    "过去进行":   "过去进行",
    "被动语态":   "被动语态",
    "虚拟语气":   "虚拟语气",
    "倒装":       "倒装",
    "强调":       "强调",
    "省略":       "省略",
    "主谓一致":   "主谓一致",
    "比较级":     "比较级",
    "最高级":     "最高级",
    "感叹句":     "感叹句",
    "疑问句":     "疑问句",
    "祈使句":     "祈使句",
}


def _terms_in_exam(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Count how many exam questions mention each term in raw_question+analysis."""
    rows = con.execute("SELECT raw_question, analysis FROM exam_questions").fetchall()
    cnt: dict[str, int] = {t: 0 for t in TERM_TO_LABEL_KEYWORD}
    for q, a in rows:
        blob = (q or "") + " " + (a or "")
        for t in TERM_TO_LABEL_KEYWORD:
            if t in blob:
                cnt[t] += 1
    return cnt


def _collect_core_ids(items: list[tuple], hits: dict[str, int]) -> set[str]:
    core: set[str] = set()
    for term in hits:
        kw = TERM_TO_LABEL_KEYWORD[term]
        for gid, label in items:
            if kw in (label or ""):
                core.add(gid)
    return core


def _count_for_item(label: str, term_counts: dict[str, int]) -> int:
    return sum(c for t, c in term_counts.items()
               if c > 0 and TERM_TO_LABEL_KEYWORD[t] in (label or ""))


def _hint_for(status: str) -> str:
    return ("课标语法+高考印证, 必教" if status == "core"
            else "课标内, 真题近年未直接出现, 常规教学")


def audit_grammar_exam_coverage(con: duckdb.DuckDBPyConnection) -> list[dict]:
    term_counts = _terms_in_exam(con)
    hits = {t: n for t, n in term_counts.items() if n > 0}
    items = con.execute(
        "SELECT grammar_item_id, label FROM grammar_items"
    ).fetchall()
    core_ids = _collect_core_ids(items, hits)

    for gid, label in items:
        status = "core" if gid in core_ids else "standard"
        cnt = _count_for_item(label, term_counts)
        attrs = ('{"exam_status": "%s", "gaokao_term_hit_count": %d, '
                 '"teaching_hint": "%s"}' % (status, cnt, _hint_for(status)))
        con.execute("UPDATE nodes SET attrs_json=? WHERE concept_id=?",
                    [attrs, f"grammar:{gid}"])

    top_hits = dict(sorted(hits.items(), key=lambda kv: -kv[1])[:10])
    return [finding("grammar_exam_4q", "OK",
                    target="grammar exam_status mapping",
                    expected="core+standard 全覆盖",
                    actual=f"core={len(core_ids)} standard={len(items)-len(core_ids)} total={len(items)}",
                    note=f"hits 关键词: {top_hits}")]
