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


# 中考语篇填空(语法填空) analysis 字段术语简写 → 规范术语 (2026-07-07 直接查库核实20行原始
# 数据, 非委托agent臆测): "被动"(ZK-LN-2025-38)缺"语态"二字, "过去时"(ZK-LN-2025-36)缺"一般"
# 二字, 均是完整术语的口语化简写, 库内无"被动"/"过去时"独立节点 (非歧义, 唯一可能目标)。
_ZK_TERM_ALIASES = {"被动": "被动语态", "过去时": "一般过去时"}

# 逐条核实(2026-07-07): 71个grammar:jr:节点里无对应项, 不强凑(D0诚实, 宁缺毋滥):
#   名词复数(ZK-LN-2024/2025-33/37): 最接近"可数名词及其单、复数"(一/一/1), 但该节点还覆盖
#     单数形式, 非纯"复数"概念, 课标未单列"名词复数"独立节点 → 标 unmatched。
#   宾格(ZK-LN-2024-38 'me'): 71节点按词类分层(人称代词/物主代词/反身代词...), 未见"宾格"
#     (格位)独立节点 → 标 unmatched。
_ZK_TERM_UNMATCHED = {"名词复数", "宾格"}


def _extract_term(answer: str | None, analysis: str | None) -> str | None:
    """analysis = answer+类别 无分隔符拼接, 去掉answer前缀剩下即类别 (逐条核实见模块docstring)."""
    if not analysis or not analysis.startswith(answer or ""):
        return None
    return analysis[len(answer or ""):].strip() or None


def link_zhongkao_grammar(con) -> dict:
    """中考语篇填空(语法填空)20题 → grammar:jr:节点 tests_grammar边 (Phase E3).

    样本量极薄(20题, 2024/2025各10, 是唯一同时有完整answer+analysis的中考题型) — 只报
    绝对数量+命中清单, 不报占比(同坑12: 20题相对71个课标语法点不构成同一统计总体的抽样
    分子分母, 与108课标语法点vs35高中真题同理, 不做除法)。精确匹配复用
    grammar_4q.match_ids_for_term(Rule5: 该函数增至2个消费者, 不定式/比较级例外表对初高中
    taxonomy措辞一致, 无需重复定义)。须在 canonical grammar:jr: 节点(本文件load()) +
    junior/qbank.py 的 question:ZK-% 节点 均已建好之后调。
    """
    from backend.services.audit.grammar_4q import match_ids_for_term

    rows = con.execute(
        "SELECT question_id, answer, analysis FROM exam_questions_all "
        "WHERE exam_type='中考' AND question_type='语篇填空(语法填空)'"
    ).fetchall()
    items = [(cid, None, label) for cid, label in con.execute(
        "SELECT concept_id, label FROM nodes WHERE concept_id LIKE 'grammar:jr:%'").fetchall()]

    con.execute("DELETE FROM edges WHERE relation='tests_grammar' AND src_id LIKE 'question:ZK-%'")
    edges = []
    matched_terms: set[str] = set()
    unmatched_terms: set[str] = set()
    for qid, ans, anl in rows:
        term = _extract_term(ans, anl)
        if not term:
            continue
        canonical = _ZK_TERM_ALIASES.get(term, term)
        if canonical in _ZK_TERM_UNMATCHED:
            unmatched_terms.add(term)
            continue
        gids = match_ids_for_term(items, canonical, canonical)
        if not gids:
            unmatched_terms.add(term)
            continue
        matched_terms.add(term)
        ev = json.dumps({"basis": "zhongkao_yupian_tiankong_analysis", "raw_term": term,
                          "canonical_term": canonical}, ensure_ascii=False)
        for gid in gids:
            edges.append((f"question:{qid}", gid, "tests_grammar", 1.0, ev))
    if edges:
        con.executemany(
            "INSERT INTO edges (src_id, dst_id, relation, weight, evidence_json) "
            "VALUES (?, ?, ?, ?, ?)", edges)
    return {"中考语篇填空tests_grammar边": len(edges), "样本量(题数)": len(rows),
            "已匹配术语": sorted(matched_terms),
            "未匹配术语(库内无对应节点,诚实标注不强凑)": sorted(unmatched_terms)}
