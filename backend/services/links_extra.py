"""Extra link builders (STEP "数据补全"): tests_word / tests_grammar / theme_of_unit.

为避免 backend/services/links.py 超 250L god-module, 拆到本文件;
init_db 在 links.build_all 后调 links_extra.build_all_extra.
"""
from __future__ import annotations

import json
import re

import duckdb

from .audit.grammar_4q import TERM_TO_LABEL_KEYWORD

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'\-]{1,}")
_CTRL_RE = re.compile(r"[\x00-\x1f\x7f]")   # RC1#5: 控制字符(\x7f/制表符等)清洗, 防非法 JSON


def _clean_ctrl(s: str) -> str:
    """去控制字符 (源含 \\x7f/制表符会污染 evidence_json; json.dumps 也会转义, 此处源头清干净)."""
    return _CTRL_RE.sub(" ", s or "")

# Unit title 关键词 → 主题语境. 简短 keyword 子串匹配 (broad覆盖).
UNIT_THEME_HINTS = {
    "TEENAGE": "人与自我/生活与学习", "LIFE": "人与自我/生活与学习",
    "LEARNING": "人与自我/生活与学习", "SCHOOL": "人与自我/生活与学习",
    "STUDY": "人与自我/生活与学习", "LANGUAGE": "人与社会/历史、社会与文化",
    "TRAVEL": "人与社会/历史、社会与文化", "JOURNEY": "人与社会/历史、社会与文化",
    "SPORT": "人与自我/做人与做事", "FITNESS": "人与自我/做人与做事",
    "ACHIEVEMENT": "人与自我/做人与做事", "MORALS": "人与自我/做人与做事",
    "VALUE": "人与自我/做人与做事", "VIRTUE": "人与自我/做人与做事",
    "CAREER": "人与自我/做人与做事", "WORK": "人与自我/做人与做事",
    "JOB": "人与自我/做人与做事", "PURSUIT": "人与自我/做人与做事",
    "BODY": "人与自我/生活与学习", "HEALTHY": "人与自我/生活与学习",
    "HEALTH": "人与自我/生活与学习", "FIRST AID": "人与自我/生活与学习",
    "FOOD": "人与自我/生活与学习",
    "DISASTER": "人与自然/灾害防范",
    "WILDLIFE": "人与自然/自然生态", "ANIMAL": "人与自然/自然生态",
    "NATURE": "人与自然/自然生态", "PLANT": "人与自然/自然生态",
    "ENVIRONMENT": "人与自然/环境保护", "PROTECTION": "人与自然/环境保护",
    "SPACE": "人与自然/宇宙探索", "SEA": "人与自然/宇宙探索",
    "EXPLORATION": "人与自然/宇宙探索", "FUTURE": "人与自然/宇宙探索",
    "PARK": "人与自然/自然生态", "LAND": "人与自然/自然生态",
    "CULTURAL": "人与社会/历史、社会与文化", "CULTURE": "人与社会/历史、社会与文化",
    "HISTORY": "人与社会/历史、社会与文化", "HERITAGE": "人与社会/历史、社会与文化",
    "TRADITION": "人与社会/历史、社会与文化", "FESTIVAL": "人与社会/历史、社会与文化",
    "DIVERSE": "人与社会/历史、社会与文化", "BRIDGING": "人与社会/历史、社会与文化",
    "ATTRACTION": "人与社会/历史、社会与文化",
    "INTERNET": "人与社会/科学与技术", "TECHNOLOGY": "人与社会/科学与技术",
    "SCIENCE": "人与社会/科学与技术", "SCIENTIST": "人与社会/科学与技术",
    "ART": "人与社会/文学、艺术与体育", "POEM": "人与社会/文学、艺术与体育",
    "FICTION": "人与社会/文学、艺术与体育",
    "SHARING": "人与社会/社会服务与人际沟通",
    "MONEY": "人与社会/历史、社会与文化",
    "WELCOME": "人与自我/生活与学习",   # Welcome Unit fallback
}


def _replace(con: duckdb.DuckDBPyConnection, relation: str, rows: list) -> int:
    con.execute("DELETE FROM edges WHERE relation = ?", [relation])
    if not rows:
        return 0
    con.executemany(
        "INSERT INTO edges (src_id, dst_id, relation, weight, evidence_json) "
        "VALUES (?, ?, ?, ?, ?)",
        [(s, d, relation, w, ev) for s, d, w, ev in rows],
    )
    return len(rows)


def build_tests_word(con: duckdb.DuckDBPyConnection) -> int:
    """question → word: 题面实词 (cefr ∩ lemmatize token − 停用词) 即建 edge (评估考点).

    2026-06-15: 去停用词污染 — 旧版把 the/it/to 等功能词也建边, 41% tests_word 是噪声.
    2026-06-17: 改用 exam_vocab._lemma_tokens (lemmatize + 去停用词) — 与 exam_status
    单一计算点同口径, 否则 'absorbed'(题面) vs 'absorb'(cefr) 无 lemmatize 漏建边 →
    exam_status='core' 却无 tests_word 边 (Rule1 不一致, 347→~0)。
    """
    from nltk.stem import WordNetLemmatizer

    from backend.services.exam_vocab import _lemma_tokens
    lemm = WordNetLemmatizer()
    # 可分类词集 = cefr ∪ 教材词 (与 exam_coverage 分类集同口径)。
    # 旧版只 & cefr → 教材课标派生/屈折词(assessment/announcement, 不在 cefr 但被
    # is_real_over 折进 core) 漏建边 → exam_status='core' 却无 tests_word 边 (Rule1 不一致)。
    classifiable = {r[0] for r in con.execute("SELECT word FROM cefr_vocab").fetchall()}
    classifiable |= {r[0] for r in con.execute(
        "SELECT DISTINCT word FROM unit_vocab_intro WHERE unit_number>0").fetchall()}
    rows: list[tuple] = []
    for qid, qtext in con.execute(
        "SELECT question_id, raw_question FROM exam_questions"
    ).fetchall():
        if not qtext:
            continue
        toks = _lemma_tokens(qtext, lemm) & classifiable   # _lemma_tokens 已去停用词
        for w in toks:
            rows.append((f"question:{qid}", f"word:{w}", 1.0, None))
    return _replace(con, "tests_word", rows)


# RC1#4 (后端审计): tests_grammar 只对**离散语法考点题型**建边。阅读理解/完形/七选五结构上不考离散语法
# (原对全题型子串匹配 → 7条落阅读理解=确证误报, 污染 lesson_plan"教此语法→高考这么考")。
_GRAMMAR_QTYPES = ("语法填空", "单选(语法/词汇)", "短文改错")


def _most_specific_grammar_match(items: list[tuple], kw: str, blob: str) -> tuple[str, str] | None:
    """kw 命中的候选(父+子共享同一 keyword 子串, 如"定语从句"同时命中父节点和限制性/非限制性
    两个子节点)里, 只挑 blob 文本真正支持的最具体一个 (坑2026-07-04: 旧版子串命中就全挂,
    18.9%~53.3%的边过度归因到文本根本没区分的子类目). 候选 label 本身(比 kw 更具体的
    完整表述, 如"限制性定语从句")必须整串出现在 blob 才算命中; label==kw 的 umbrella
    节点总是候选(它就是被命中的这个泛化 term 本身)。多个仍命中时取 label 最长(最具体)的。"""
    matched = [(gid, label) for gid, label in items
               if kw in (label or "") and (label == kw or label in blob)]
    if not matched:
        return None
    return max(matched, key=lambda x: len(x[1]))


def build_tests_grammar(con: duckdb.DuckDBPyConnection) -> int:
    """question → grammar: 题面 / analysis 含中文语法术语即建 edge (仅离散语法题型, 见 _GRAMMAR_QTYPES).

    坑(2026-07-04 全数据审计, province无过滤修): 旧版无 province 过滤(88%非辽宁题的边混入
    edges表), 现改按 §7 辽宁口径限定(与 audit/grammar_4q.py._terms_in_exam 同口径, 不
    冒充辽宁语法考查); 父子过度归因见 _most_specific_grammar_match。
    """
    items = con.execute(
        "SELECT grammar_item_id, label FROM grammar_items"
    ).fetchall()
    rows: list[tuple] = []
    qmarks = ",".join("?" * len(_GRAMMAR_QTYPES))
    for qid, qtext, anl in con.execute(
        f"SELECT question_id, raw_question, analysis FROM exam_questions "
        f"WHERE question_type IN ({qmarks}) AND province LIKE '辽宁%'", list(_GRAMMAR_QTYPES)
    ).fetchall():
        blob = (qtext or "") + " " + (anl or "")
        for term, kw in TERM_TO_LABEL_KEYWORD.items():
            if term not in blob:
                continue
            hit = _most_specific_grammar_match(items, kw, blob)
            if hit:
                gid, _ = hit
                rows.append((f"question:{qid}", f"grammar:{gid}",
                             1.0, json.dumps({"term": term}, ensure_ascii=False)))
    # dedup (src, dst)
    dedup = {}
    for r in rows:
        dedup[(r[0], r[1])] = r
    return _replace(con, "tests_grammar", list(dedup.values()))


_SHORT_HINT_LEN = 4  # <此长度的关键词强制词边界匹配 (坑2026-07-04: "ART"子串命中"st-ART"/"e-ARTh")


def _hint_matches(keyword: str, title_upper: str) -> bool:
    """短关键词(<4字符, 易在别的单词里当子串命中)强制词边界匹配; 长关键词保留子串匹配
    (故意的词干匹配, 如 TRAVEL 命中 TRAVELLING 是设计内行为, 词边界会打断这类合法匹配)."""
    if len(keyword) < _SHORT_HINT_LEN:
        return re.search(r"\b" + re.escape(keyword) + r"\b", title_upper) is not None
    return keyword in title_upper


def build_theme_of_unit(con: duckdb.DuckDBPyConnection) -> int:
    """unit → theme: hardcoded UNIT_THEME_HINTS + title_en substring match (短关键词词边界, 见 _hint_matches)."""
    units = con.execute(
        "SELECT version_key, volume_key, unit_number, title_en FROM units"
    ).fetchall()
    rows: list[tuple] = []
    for ver, vol, un, title in units:
        title_upper = (title or "").upper()
        for keyword, theme_id in UNIT_THEME_HINTS.items():
            if _hint_matches(keyword, title_upper):
                rows.append((
                    f"unit:{ver}/{vol}/U{un}", f"theme:{theme_id}", 1.0,
                    json.dumps({"matched_keyword": keyword,
                                 "title": title}, ensure_ascii=False),
                ))
                break   # one theme per unit
    return _replace(con, "theme_of_unit", rows)


def build_introduces_phrase(con: duckdb.DuckDBPyConnection) -> int:
    """unit → phrase. Auto-create phrase nodes (concept_id = 'phrase:<sha8>')."""
    import hashlib
    rows_p = con.execute(
        "SELECT version_key, volume_key, unit_number, canonical, phrase_type, evidence "
        "FROM phrases"
    ).fetchall()
    node_rows: list[tuple] = []
    edge_rows: list[tuple] = []
    seen_nodes: set[str] = set()
    for ver, vol, un, canon, ptype, ev in rows_p:
        sha = hashlib.sha1(f"{canon}/{ptype}".encode("utf-8")).hexdigest()[:8]
        cid = f"phrase:{sha}"
        if cid not in seen_nodes:
            seen_nodes.add(cid)
            # RC1#5: 用 json.dumps 生成 JSON (默认转义控制字符+引号), 不再手拼只转双引号 —
            # 手拼会让源含 \x7f/制表符的 canon/ev 产出非法 JSON, 全表 json_extract 直接崩。
            node_rows.append((cid, "phrase", canon,
                              json.dumps({"canonical": _clean_ctrl(canon), "type": ptype}, ensure_ascii=False)))
        edge_rows.append((
            f"unit:{ver}/{vol}/U{un}", cid, 1.0,
            json.dumps({"evidence": _clean_ctrl((ev or "")[:200])}, ensure_ascii=False),
        ))
    if node_rows:
        con.executemany("INSERT OR REPLACE INTO nodes VALUES (?, ?, ?, ?)", node_rows)
    return _replace(con, "introduces_phrase", edge_rows)


def build_all_extra(con: duckdb.DuckDBPyConnection) -> dict:
    return {
        "tests_word": build_tests_word(con),
        "tests_grammar": build_tests_grammar(con),
        "theme_of_unit": build_theme_of_unit(con),
        "introduces_phrase": build_introduces_phrase(con),
    }
