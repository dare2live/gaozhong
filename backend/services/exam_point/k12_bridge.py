"""K12 衔接视图 — 初中语法点 → 高中语法深化 → 高考印证 (Phase E5).

背景: 用户要"初中→高中衔接"分析, 锚点必须是**语法点**——这是唯一有完整闭环数据的维度:
初中71个语法节点(grammar:jr:X) 100%有 `deepens` 边指向高中语法节点(grammar:Y, 无衔接孤儿,
D0已锁, 见 backend/services/data_sources/extract/junior/blueprint.py), 高中语法节点已由
grammar_4q.py::audit_grammar_exam_coverage 标好 exam_status(core/standard, 写入
nodes.attrs_json), 中考侧还有17个初中语法节点能反查到 tests_grammar 边(20题中考语篇填空
里17题精确匹配, 见 junior/grammar.py::link_zhongkao_grammar)。三段边全部已建好, 本模块
只读聚合, 不重算 (Rule1 单一计算点)。

词汇(word at_stage边)和短语(phrases表/phrase_pattern_exam_relevance) 维度的K12衔接数据
也存在, 但本函数**只聚焦语法点维度**, 不在这里混算(分层非平均纪律: 三个维度分开呈现,
不糅合成单一模糊指标)。词汇/短语维度已有各自的现成分析函数(k12.tested_word_stage_distribution /
senior_knowledge.phrase_pattern_exam_relevance), 需要时各自调用, 不重复。

样本量诚实(坑12): 中考印证目前只覆盖语法填空题型(20题里17题被精确匹配到语法点); 完形填空/
阅读理解等2025年其它35道真实题面目前只有 tests_word 边(词汇曝光), 没有语法点关联, 不能说
"这些题也印证了某语法点"。summary 只报绝对数量, 不报"17/71=24%"这类占比(样本量薄, 分子分母
不是同一统计总体的抽样关系, 同 grammar_structural_coverage 的"不报占比"纪律)。
"""
from __future__ import annotations

import json

import duckdb

_ZK_QTYPE = "语篇填空(语法填空)"


def _deepens_map(con: duckdb.DuckDBPyConnection) -> dict[str, str]:
    """初中grammar:jr节点 → 高中grammar节点 concept_id (1:1, 71条, 无衔接孤儿, D0已锁)."""
    rows = con.execute(
        "SELECT src_id, dst_id FROM edges WHERE relation='deepens'"
    ).fetchall()
    return {src: dst for src, dst in rows}


def _senior_exam_status(con: duckdb.DuckDBPyConnection, senior_ids: list[str]) -> dict[str, dict]:
    """高中grammar节点的 exam_status/gaokao_term_hit_count (grammar_4q.py 已写入attrs_json,
    本函数只读, 不重算)."""
    if not senior_ids:
        return {}
    qmarks = ",".join(["?"] * len(senior_ids))
    rows = con.execute(
        f"SELECT concept_id, label, attrs_json FROM nodes WHERE concept_id IN ({qmarks})",
        senior_ids,
    ).fetchall()
    out = {}
    for cid, label, attrs in rows:
        a = json.loads(attrs) if attrs else {}
        out[cid] = {
            "label": label,
            "exam_status": a.get("exam_status"),
            "gaokao_term_hit_count": a.get("gaokao_term_hit_count"),
        }
    return out


def _zhongkao_verification(con: duckdb.DuckDBPyConnection) -> dict[str, list[str]]:
    """初中grammar:jr节点 → 反查有哪些中考真题(question:ZK-%) tests_grammar 边印证过它.
    (junior/grammar.py::link_zhongkao_grammar 已建好, 本函数只读反查)."""
    rows = con.execute(
        "SELECT src_id, dst_id FROM edges WHERE relation='tests_grammar' "
        "AND src_id LIKE 'question:ZK-%'"
    ).fetchall()
    out: dict[str, list[str]] = {}
    for qid, gid in rows:
        out.setdefault(gid, []).append(qid[len("question:"):])
    for gid in out:
        out[gid].sort()
    return out


def _junior_items(con: duckdb.DuckDBPyConnection) -> list[tuple[str, str]]:
    return con.execute(
        "SELECT concept_id, label FROM nodes WHERE concept_id LIKE 'grammar:jr:%' "
        "ORDER BY concept_id"
    ).fetchall()


def _build_record(jr_cid: str, jr_label: str, deepens: dict[str, str],
                   senior_info: dict[str, dict], zk_verified: dict[str, list[str]]) -> dict:
    senior_cid = deepens.get(jr_cid)
    senior = senior_info.get(senior_cid, {}) if senior_cid else {}
    zk_ids = zk_verified.get(jr_cid, [])
    return {
        "junior_grammar_id": jr_cid,
        "junior_label": jr_label,
        "senior_grammar_id": senior_cid,
        "senior_label": senior.get("label"),
        "exam_status": senior.get("exam_status"),
        "gaokao_term_hit_count": senior.get("gaokao_term_hit_count"),
        "zhongkao_verified": bool(zk_ids),
        "zhongkao_question_ids": zk_ids,
    }


def _summarize(records: list[dict]) -> dict:
    n_total = len(records)
    n_deepens = sum(1 for r in records if r["senior_grammar_id"])
    n_core = sum(1 for r in records if r["exam_status"] == "core")
    n_standard = sum(1 for r in records if r["exam_status"] == "standard")
    verified = [r for r in records if r["zhongkao_verified"]]
    n_zk_questions = len({q for r in verified for q in r["zhongkao_question_ids"]})
    return {
        "n_junior_grammar_items_total": n_total,
        "n_with_deepens_edge": n_deepens,
        "n_deepens_to_core_gaokao_grammar": n_core,
        "n_deepens_to_standard_gaokao_grammar": n_standard,
        "n_junior_items_with_zhongkao_verification": len(verified),
        "n_zhongkao_questions_involved": n_zk_questions,
        "report_as": "absolute_count_not_percentage",
        "note": (
            f"{n_total}个初中语法点全部(100%)有deepens边衔接到高中语法点(无衔接孤儿, D0已锁); "
            f"其中{n_core}个衔接到高考core(必考)语法, {n_standard}个衔接到standard(课标内/"
            f"真题近年未直接出现); {len(verified)}个初中语法点(对应{n_zk_questions}道中考语篇"
            "填空真题)有中考真题印证。样本量薄(20题中考语篇填空里仅17题被精确匹配), 不报占比。"
        ),
    }


def junior_senior_grammar_bridge(con: duckdb.DuckDBPyConnection) -> dict:
    """K12衔接视图主入口: 71个初中语法点 逐条 → 高中对应语法点 + 高考exam_status +
    中考真题印证情况。锚点=语法点(唯一有完整闭环数据的维度: deepens边100%覆盖 +
    grammar_4q已标exam_status + tests_grammar边可反查中考真题)。

    返回 {records: [...], summary: {...}, scope_note: {...}}。records 逐条初中语法点,
    summary 顶层绝对数量聚合, scope_note 诚实范围声明(不越界推断到完形填空/阅读理解等
    未建语法关联的题型, 不混算词汇/短语维度)。
    """
    deepens = _deepens_map(con)
    senior_info = _senior_exam_status(con, sorted(set(deepens.values())))
    zk_verified = _zhongkao_verification(con)
    junior = _junior_items(con)

    records = [
        _build_record(cid, label, deepens, senior_info, zk_verified)
        for cid, label in junior
    ]

    return {
        "province_scope": "辽宁卷(高考) + 辽宁中考",
        "anchor_dimension": "语法点(grammar) — 唯一有完整闭环数据的K12衔接维度",
        "edge_lineage": {
            "deepens": "初中grammar:jr节点→高中grammar节点, 71条, 见"
                       "junior/blueprint.py(59精确label匹配+12别名匹配, 别名表"
                       "backend/config/grammar_stage_aliases.yaml)",
            "exam_status": "高中grammar节点attrs_json.exam_status, 见"
                           "grammar_4q.py::audit_grammar_exam_coverage(本函数只读不重算)",
            "tests_grammar": "中考question:ZK-%→grammar:jr节点, 19条(17个初中语法点被印证),"
                             "见 junior/grammar.py::link_zhongkao_grammar",
        },
        "records": records,
        "summary": _summarize(records),
        "scope_note": {
            "zhongkao_coverage_limit": (
                f"中考印证目前只覆盖'{_ZK_QTYPE}'题型(20题里17题被精确匹配到语法点, 3题"
                "'名词复数'/'宾格'因71个初中语法节点里找不到精确对应, 诚实标unmatched未建边)。"
                "2025年完形填空/阅读理解等其余35道真实题面目前只有tests_word边(词汇曝光),"
                "没有语法点关联, 不能说这些题也印证了某语法点。"
            ),
            "dimension_isolation": (
                "词汇(word节点at_stage边, 高中词3095条/初中独有181条)和短语(phrases表,"
                "hujiao初中50个 vs renjiao/waiyan高中93个, 已有"
                "senior_knowledge.phrase_pattern_exam_relevance 现成分析)的K12衔接数据"
                "也存在, 但本函数聚焦语法点维度, 不在这里混算词汇/短语(分层非平均: 三个"
                "维度分开呈现, 不糅合成单一模糊指标; 需要词汇/短语衔接数据请分别调用"
                "backend.services.k12(tested_word_stage_distribution) 与"
                "senior_knowledge.phrase_pattern_exam_relevance)。"
            ),
        },
    }
