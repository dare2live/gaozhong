"""语篇级联合归因 (词汇学段 × 设问思维) — 2026-07-06 方法论研究落地.

背景: 词汇学段(k12.tested_word_stage_distribution)与设问思维(cognitive_skill.py)原本各自
独立算, 从未对齐到同一批语篇上看。用户提出的问题是"考查词75%基础阶, 但真实得分点是不是靠
高中训练的能力" —— 需要把两条线摆到同一批语篇上才能回答。

**语法学段维度已实测排除, 非遗漏**: 设计之初曾打算做"词汇×语法×设问思维"三线联合, 但实测
发现 tests_grammar 边只出现在 语法填空/短文改错 这两种 question_type 上, 而 cognitive_skill
只标注 阅读理解 的子题 —— 两者 question_type 完全不相交, 语法维度在当前数据结构下**必然**
是空集(不是"样本少", 是"这两条边永远不会同时出现在同一道题上")。若强行保留这个字段, 会让
读者误以为"这篇文章语法信息未知/待补", 实际是**结构性不可能**, 故诚实地不做这个维度, 而非
摆一个必空的占位字段(参考项目"宁缺毋滥, 返空>假推"原则)。

颗粒度边界(必须诚实, 不可假装更精确): tests_word 边挂在**语篇**层级(question:qid),
cognitive_skill 边挂在**子题**层级(question:qid#qN)。一篇文章的词汇边是对整篇抽取的, 无法
精确到"某道子题具体靠哪个词拿分"。本模块只做**语篇级聚合**(一篇文章N道子题里几道是推断/
几道是细节, 与同一篇文章的词汇学段占比对齐), 不做子题级归因。

era 锁 2015-2020(同 cognitive_skill_by_content 既有约束): 2021+ 子题 node 的 passage_label
只是单字母(A/B/C/D, 年内相对编号非全局唯一 question_id), 无法桥接回 'question:'+id 去 JOIN
tests_word 边(已实测验证: 2021+ 各 passage_label 桥接后 tests_word 边数=0)。

单一计算点(Rule1): 只读聚合已有两条 edge 线, 不新建 edge/表, 不重写其他服务已算好的逻辑
(词汇学段读 at_stage 边同 k12.tested_word_stage_distribution 口径; 设问思维分布读
tests_exam_point dimension=cognitive_skill 同 cognitive_skill_by_content 的 passage_label
桥接手法)。
"""
from __future__ import annotations

import duckdb

from backend.services.trend import scope

_FOUNDATION_STAGES = {"小学", "初中", "义务教育"}
_SENIOR_STAGES = {"高中必修", "高中选修"}


def _passage_skill_dist(con: duckdb.DuckDBPyConnection) -> dict[str, dict[str, int]]:
    """每语篇(2015-2020) 设问思维分布(子题计数), 复用 cognitive_skill_by_content 的
    passage_label 回指桥接手法(cognitive_skill.py::_CROSS_SQL 同款 JOIN, 未重写逻辑)。"""
    rows = con.execute(
        "SELECT 'question:'||json_extract_string(nq.attrs_json,'$.passage_label') AS pid, "
        "       ns.label AS skill "
        "FROM edges e "
        "JOIN nodes nq ON nq.concept_id = e.src_id "
        "JOIN nodes ns ON ns.concept_id = e.dst_id "
        "WHERE e.relation='tests_exam_point' AND json_extract_string(e.evidence_json,'$.dimension')='cognitive_skill' "
        "AND CAST(json_extract_string(e.evidence_json,'$.lineage.source_year') AS INT) "
        f"BETWEEN {scope.LIAONING_NATIONAL_PAPER_SINCE} AND {scope.ERA_BOUNDARY_YEAR - 1}"
    ).fetchall()
    out: dict[str, dict[str, int]] = {}
    for pid, skill in rows:
        d = out.setdefault(pid, {})
        d[skill] = d.get(skill, 0) + 1
    return out


def _passage_word_stage_mix(con: duckdb.DuckDBPyConnection, pids: list[str]) -> dict[str, dict]:
    """每语篇 tests_word 边的学段占比, 口径同 k12.tested_word_stage_distribution (at_stage 边)。"""
    if not pids:
        return {}
    qmarks = ",".join(["?"] * len(pids))
    rows = con.execute(
        f"SELECT e.src_id AS pid, COALESCE(SUBSTR(es.dst_id,7),'未分类') AS stage "
        "FROM edges e LEFT JOIN edges es ON es.src_id = e.dst_id AND es.relation='at_stage' "
        f"WHERE e.relation='tests_word' AND e.src_id IN ({qmarks})",
        pids,
    ).fetchall()
    counts: dict[str, dict[str, int]] = {}
    for pid, stage in rows:
        d = counts.setdefault(pid, {})
        d[stage] = d.get(stage, 0) + 1
    out = {}
    for pid, d in counts.items():
        tot = sum(d.values())
        out[pid] = {
            "n_words": tot,
            "foundation_pct": round(100 * sum(d.get(s, 0) for s in _FOUNDATION_STAGES) / tot, 1),
            "senior_pct": round(100 * sum(d.get(s, 0) for s in _SENIOR_STAGES) / tot, 1),
            "unclassified_pct": round(100 * d.get("未分类", 0) / tot, 1),
        }
    return out


def _by_dominant_skill(passages: list[dict]) -> dict[str, dict]:
    """按每篇语篇的主导设问技能(子题数最多的技能)分组, 看该组语篇的平均词汇学段占比是否有差异
    —— 直接回应"推断题占比高的文章, 是不是词汇也更难"这个问题(实测: 不是, 见下方数值)。
    """
    groups: dict[str, list[float]] = {}
    for p in passages:
        if not p["word_stage_mix"]:
            continue
        dom = max(p["skill_dist"].items(), key=lambda kv: kv[1])[0]
        groups.setdefault(dom, []).append(p["word_stage_mix"]["senior_pct"])
    out = {}
    for skill, vals in groups.items():
        out[skill] = {
            "n_passages": len(vals),
            "avg_word_senior_pct": round(sum(vals) / len(vals), 1),
            "thin": len(vals) < 10,
        }
    return out


def joint_attribution_by_passage(con: duckdb.DuckDBPyConnection) -> dict:
    """语篇级联合归因主入口. 返回每篇语篇的 {skill_dist, word_stage_mix} + 按主导技能分组的
    词汇学段对比(by_dominant_skill) + 样本量诚实标注(坑12: 分布门槛, <MIN_DISTRIBUTION_SAMPLE 标 thin)。
    """
    skill_dist = _passage_skill_dist(con)
    pids = sorted(skill_dist.keys())
    word_mix = _passage_word_stage_mix(con, pids)

    passages = []
    for pid in pids:
        n_subq = sum(skill_dist[pid].values())
        passages.append({
            "passage_id": pid,
            "n_subq": n_subq,
            "skill_dist": skill_dist[pid],
            "word_stage_mix": word_mix.get(pid),
        })
    n_with_word = sum(1 for p in passages if p["word_stage_mix"])
    return {
        "era": scope.ERA_OLD,
        "province_scope": "辽宁卷",
        "granularity": "语篇级(passage) — tests_word 边挂语篇层级, cognitive_skill 边挂子题层级, 无法做到子题级归因",
        "excluded_dimension_note": (
            "语法学段(tests_grammar×cognitive_skill)已实测排除: tests_grammar 只标语法填空/"
            "短文改错, cognitive_skill 只标阅读理解, question_type 完全不相交, 结构性不可能对齐"
        ),
        "n_passages": len(passages),
        "n_passages_with_word_data": n_with_word,
        "reliability_note": (
            f"n={len(passages)}篇" +
            ("" if len(passages) >= scope.MIN_DISTRIBUTION_SAMPLE
             else f"(<{scope.MIN_DISTRIBUTION_SAMPLE}, 仅方向性非精确分布, 坑12)")
        ),
        "by_dominant_skill": _by_dominant_skill(passages),
        "passages": passages,
    }
