"""课标语法 × 真题 4 象限分类 (类比 vocab exam_coverage 4q).

中文术语 grep 真题题面 + 解析 (analysis) 命中:
  - 定语从句 / 状语从句 / 宾语从句 / 主语从句 / 表语从句 / 同位语从句
  - 非谓语动词 / 动名词 / 不定式 / 分词
  - 时态: 现在完成 / 过去完成 / 一般将来 / 现在进行 / 过去进行 ...
  - 被动语态 / 虚拟语气 / 倒装 / 强调 / 省略
  - 主谓一致 / 比较级 / 最高级 / 比较句

写 grammar.attrs.exam_status (类似 vocab, **辽宁卷口径** §7):
  core      : 课标 ∩ 辽宁真题考过
  standard  : 课标内但辽宁真题未印证 (近年)
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
    # 2026-07-07 缺口2b调研补(知识点颗粒度审查): 逐条核实25条未匹配语法题型题解析文本,
    # 发现2条(短文改错)有真实中文解析但命中不了任何既有关键词(其余23条是2021/2022 EOL
    # 答案核验机械占位文本+2024/25/26空analysis, 已知的真解析文本缺失天花板, 见moth
    # grammar_category_pct断言, 非本次可修范围)。这10个新词均已核实(a)在真实解析文本里
    # 逐字出现过 (b)grammar_items表有label完全相等的对应行(_most_specific_grammar_match
    # 的label==kw分支可命中), "固定搭配"/"there be句型"因grammar_items无对应行故不收录
    # (收了也永远匹配不上, 不是遗漏是这两者本就不属于108项官方语法点)。
    "冠词":       "冠词",
    "介词":       "介词",
    "连词":       "连词",
    "名词":       "名词",
    "形容词":     "形容词",
    "副词":       "副词",
    "序数词":     "序数词",
    "情态动词":   "情态动词",
    "人称代词":   "人称代词",
    "一般过去":   "一般过去",
    # 2026-07-07 坑25修复: "非谓语"原值"非谓语"在grammar_items无精确label(实际label=
    # "动词的非谓语形式"), 旧版kw-in-label子串规则能凑巧命中, 改精确匹配后须订正为真实label。
    "非谓语":     "动词的非谓语形式",
}

# 2026-07-07 坑25 (子串跨枝/跨层误配, workflow独立复算实证发现): 旧版 `kw in label` 全局子串对
# "名词"/"形容词"/"副词"/"介词" 会误配到*完全不同分支*的"名词短语/形容词短语/副词短语/介词短语"
# (parent_id="三/2"=短语, 与名词等的parent="一"无关); 对"被动语态"/"现在完成"会误配到*同分支更具体
# 的兄弟/子节点*("现在完成时的被动语态"等7个复合时态×语态节点、"现在完成进行"), 泛化提及"被动语态"
# 不能证实这些复合形态被专门考过(过度归因, 同坑7模式)。精确匹配 + 按类分层例外, 逐条已核实
# (workflow独立复算+对抗审查, 2026-07-07):
# 从句族: 限制性/非限制性等是同一从句机制的文体变体(非独立维度), 精确命中后含子孙合理。
_CLAUSE_FAMILY_TERMS = {"定语从句", "状语从句", "宾语从句", "主语从句", "表语从句", "同位语从句"}
# 前缀例外: label=term概念官方名+括注用法说明, 库内该前缀唯一(已核实无同前缀其他节点), 非歧义子串。
_PREFIX_MATCH_EXCEPTIONS = {"不定式": "动词不定式"}
# 子串枚举例外: 课标未单列该概念独立节点(比较级/最高级并入"形容词/副词的比较级和最高级"复合节点),
# 枚举具体目标(非泛化子串规则), 不会引入新的跨枝误配。
_SUBSTRING_ENUM_EXCEPTIONS = {
    "比较级": {"形容词的比较级和最高级", "副词的比较级和最高级"},
    "最高级": {"形容词的比较级和最高级", "副词的比较级和最高级"},
}


def _terms_in_exam(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Count 辽宁真题 mentioning each grammar term (§7 辽宁口径, 不混外省冒充辽宁)。"""
    rows = con.execute(
        "SELECT raw_question, analysis FROM exam_questions WHERE province LIKE '辽宁%'"
    ).fetchall()
    cnt: dict[str, int] = {t: 0 for t in TERM_TO_LABEL_KEYWORD}
    for q, a in rows:
        blob = (q or "") + " " + (a or "")
        for t in TERM_TO_LABEL_KEYWORD:
            if t in blob:
                cnt[t] += 1
    return cnt


def _descendants_of(items: list[tuple], gid: str) -> set[str]:
    """gid 的全部子孙(经 parent_id 链, BFS)。"""
    children: dict[str, set[str]] = {}
    for cid, pid, _label in items:
        if pid:
            children.setdefault(pid, set()).add(cid)
    out: set[str] = set()
    frontier = {gid}
    while frontier:
        nxt = set().union(*(children.get(p, set()) for p in frontier)) - out
        if not nxt:
            break
        out |= nxt
        frontier = nxt
    return out


def _match_ids_for_term(items: list[tuple], term: str, kw: str) -> set[str]:
    """term → grammar_item_id 精确匹配 (替代旧版全局 kw-in-label 子串, 坑25)。

    优先级: (1) 子串枚举例外(比较级/最高级复合节点) (2) 前缀例外(不定式) (3) 精确相等,
    从句族额外含子孙(文体变体非独立维度) (4) 默认仅精确相等, 不泛化。
    """
    if term in _SUBSTRING_ENUM_EXCEPTIONS:
        targets = _SUBSTRING_ENUM_EXCEPTIONS[term]
        return {gid for gid, _pid, label in items if label in targets}
    prefix = _PREFIX_MATCH_EXCEPTIONS.get(term)
    if prefix:
        return {gid for gid, _pid, label in items if (label or "").startswith(prefix)}
    exact = {gid for gid, _pid, label in items if label == kw}
    if term in _CLAUSE_FAMILY_TERMS:
        for gid in list(exact):
            exact |= _descendants_of(items, gid)
    return exact


def _match_sets(items: list[tuple], hits: dict[str, int]) -> dict[str, set[str]]:
    """单一计算点: 每 term 各自匹配的 gid 集合, 供 core_ids 与逐 gid 命中计数复用同一份匹配结果。"""
    return {term: _match_ids_for_term(items, term, TERM_TO_LABEL_KEYWORD[term]) for term in hits}


def _collect_core_ids(match_sets: dict[str, set[str]]) -> set[str]:
    core: set[str] = set()
    for ids in match_sets.values():
        core |= ids
    return core


def _count_for_item(gid: str, term_counts: dict[str, int], match_sets: dict[str, set[str]]) -> int:
    return sum(term_counts[t] for t, ids in match_sets.items() if gid in ids)


def _hint_for(status: str) -> str:
    return ("课标语法+高考印证, 必教" if status == "core"
            else "课标内, 真题近年未直接出现, 常规教学")


def audit_grammar_exam_coverage(con: duckdb.DuckDBPyConnection) -> list[dict]:
    term_counts = _terms_in_exam(con)
    hits = {t: n for t, n in term_counts.items() if n > 0}
    items = con.execute(
        "SELECT grammar_item_id, parent_id, label FROM grammar_items"
    ).fetchall()
    matches = _match_sets(items, hits)
    core_ids = _collect_core_ids(matches)

    for gid, _pid, label in items:
        status = "core" if gid in core_ids else "standard"
        cnt = _count_for_item(gid, term_counts, matches)
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
