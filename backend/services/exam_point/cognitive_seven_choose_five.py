"""阅读第二节选句填空 → 理解文章结构类型 (+ L2 subtype).

分类逻辑见 structure_subtype.py; 本文件只负责入图.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import duckdb

from backend.services.exam_point.structure_subtype import (
    blank_src_ids,
    classify_structure_subtype,
    extract_blank_analysis,
    parse_option_letters,
)
from backend.services.lineage import stamp

ROOT = Path(__file__).resolve().parents[3]
DIMENSION = "cognitive_skill"
SKILL = "理解文章结构类型"
PROVENANCE = "curriculum_aligned_task"
QTYPE_SENIOR = "完形填空(七选五/语篇)"
QTYPE_JUNIOR = "阅读理解(五选四/选句填空)"
_CURRICULUM_REF = (
    "陈康等2019《中国考试》·理解文章结构类型; "
    "课标语篇知识(衔接与连贯); 阅读第二节选句填空"
)
_EOL = {
    2021: ROOT / "data/external/exam_sources/eol/2021_xgkii_english_eol.txt",
    2022: ROOT / "data/external/exam_sources/eol/2022_xgkii_english_eol.txt",
}
_JR_OCR = {
    2024: ROOT / "data/junior_high/exams/2024_liaoning/exam_ocr.txt",
    2025: ROOT / "data/junior_high/exams/2025_liaoning/exam_ocr.txt",
}


def _ensure_skill_node(con: duckdb.DuckDBPyConnection) -> str:
    pnode = f"exam_point:{DIMENSION}:{SKILL}"
    if not con.execute("SELECT 1 FROM nodes WHERE concept_id=?", [pnode]).fetchone():
        con.execute(
            "INSERT INTO nodes VALUES (?, ?, ?, ?)",
            [pnode, "exam_point", SKILL, json.dumps({"dimension": DIMENSION}, ensure_ascii=False)],
        )
    return pnode


def _emit_blank(
    con, *, src_id, year, blank_no, letter, passage_qid, snip, exam_stage,
    question_type, pnode, passage=None,
) -> tuple[int, int]:
    subtype, rule, method = classify_structure_subtype(
        snip, src_id=src_id, passage=passage, blank_no=blank_no,
    )
    qnode = f"question:{src_id}"
    n_sub = 0
    if not con.execute("SELECT 1 FROM nodes WHERE concept_id=?", [qnode]).fetchone():
        con.execute(
            "INSERT INTO nodes VALUES (?, ?, ?, ?)",
            [qnode, "question", src_id, json.dumps({
                "year": year, "province": "辽宁",
                "exam_type": "高考" if exam_stage == "gaokao" else "中考",
                "question_type": question_type, "question_number": blank_no,
                "subquestion": True, "reading_section": "选句填空",
                "passage_qid": passage_qid, "exam_stage": exam_stage,
            }, ensure_ascii=False)],
        )
        n_sub = 1
    con.execute(
        "DELETE FROM edges WHERE src_id=? AND relation='tests_exam_point' "
        "AND json_extract_string(evidence_json,'$.dimension')=?",
        [qnode, DIMENSION],
    )
    lineage = stamp(
        con, source_year=year, source_qid=src_id, provenance=PROVENANCE,
        derived_by="cognitive_structure_task@v3",
        version_kinds={
            "exam_paper": "liaoning_gaokao" if exam_stage == "gaokao" else "shenyang_zhongkao",
            "curriculum": "gaozhong" if exam_stage == "gaokao" else "yiwu",
        },
    )
    evidence = {
        "dimension": DIMENSION, "provenance": PROVENANCE, "skill": SKILL,
        "subtype": subtype, "subtype_method": method, "subtype_rule": rule,
        "subtype_analysis": (snip[:240] if snip else None),
        "task": "阅读第二节-选句填空", "blank_no": blank_no, "option": letter,
        "passage_qid": passage_qid, "exam_stage": exam_stage,
        "curriculum_ref": _CURRICULUM_REF, "lineage": lineage,
    }
    con.execute(
        "INSERT INTO edges (src_id, dst_id, relation, weight, evidence_json) VALUES (?, ?, ?, ?, ?)",
        [qnode, pnode, "tests_exam_point", 1.0, json.dumps(evidence, ensure_ascii=False)],
    )
    return n_sub, 1, subtype, method


def _passage_for_year(con, year: int, fallback_raw: str) -> str:
    eol = _EOL.get(year)
    if eol and eol.exists():
        return eol.read_text(encoding="utf-8", errors="ignore")
    parts = [r[0] or "" for r in con.execute(
        "SELECT raw_question FROM exam_questions WHERE province LIKE '辽宁%' "
        "AND question_type=? AND year=? ORDER BY question_id",
        [QTYPE_SENIOR, year],
    ).fetchall()]
    bundled = "\n".join(parts)
    return bundled if len(bundled) > len(fallback_raw or "") else (fallback_raw or bundled)


def load_seven_choose_five_structure(con: duckdb.DuckDBPyConnection) -> dict:
    rows = con.execute(
        "SELECT question_id, year, answer, analysis, raw_question FROM exam_questions "
        "WHERE province LIKE '辽宁%' AND question_type=? AND year BETWEEN 2015 AND 2026 "
        "ORDER BY year, question_id",
        [QTYPE_SENIOR],
    ).fetchall()
    pnode = _ensure_skill_node(con)
    n_edge = n_sub = 0
    subtype_counts: Counter = Counter()
    method_counts: Counter = Counter()
    years: set[int] = set()
    cache: dict[int, str] = {}
    for qid, year, answer, analysis, raw in rows:
        year = int(year)
        cache.setdefault(year, _passage_for_year(con, year, raw or ""))
        passage = cache[year]
        snips = extract_blank_analysis(analysis)
        for src_id, blank_no, letter in blank_src_ids(qid, answer):
            snip = snips.get(blank_no, "")
            s, e, st, meth = _emit_blank(
                con, src_id=src_id, year=year, blank_no=blank_no, letter=letter,
                passage_qid=qid, snip=snip, exam_stage="gaokao",
                question_type=QTYPE_SENIOR, pnode=pnode, passage=passage,
            )
            n_sub += s
            n_edge += e
            subtype_counts[st] += 1
            method_counts[meth] += 1
            years.add(year)
    return {
        "seven_structure_edges": n_edge, "seven_structure_subq_nodes": n_sub,
        "seven_structure_years": sorted(years), "seven_structure_passages": len(rows),
        "seven_structure_subtypes": dict(subtype_counts),
        "seven_structure_methods": dict(method_counts),
    }


def load_junior_sentence_gap_structure(con: duckdb.DuckDBPyConnection) -> dict:
    rows = con.execute(
        "SELECT origin_ref, answer, analysis FROM question_bank "
        "WHERE origin_ref LIKE 'ZK-LN-%' AND question_type=? ORDER BY origin_ref",
        [QTYPE_JUNIOR],
    ).fetchall()
    pnode = _ensure_skill_node(con)
    n_edge = n_sub = 0
    subtype_counts: Counter = Counter()
    ocr_cache: dict[int, str] = {}
    for origin_ref, answer, analysis in rows:
        ym = re.search(r"ZK-LN-(\d{4})-(\d+)$", origin_ref)
        if not ym:
            continue
        year, blank_no = int(ym.group(1)), int(ym.group(2))
        if year not in ocr_cache:
            p = _JR_OCR.get(year)
            ocr_cache[year] = p.read_text(encoding="utf-8", errors="ignore") if p and p.exists() else ""
        letter = (parse_option_letters(answer) or [None])[0]
        snip = (analysis or "")[:300]
        s, e, st, _meth = _emit_blank(
            con, src_id=origin_ref, year=year, blank_no=blank_no, letter=letter,
            passage_qid=re.sub(r"-\d+$", "-gap", origin_ref), snip=snip,
            exam_stage="zhongkao", question_type=QTYPE_JUNIOR, pnode=pnode,
            passage=ocr_cache[year],
        )
        n_sub += s
        n_edge += e
        subtype_counts[st] += 1
    return {
        "junior_gap_structure_edges": n_edge, "junior_gap_structure_nodes": n_sub,
        "junior_gap_structure_subtypes": dict(subtype_counts),
    }


def load_junior_curriculum_reading_skills(con: duckdb.DuckDBPyConnection) -> dict:
    from backend.services.exam_point.cognitive_curriculum import _load_rules

    compiled = {
        skill: [re.compile(p) for p in (cfg.get("stem_any") or [])]
        for skill, cfg in (_load_rules().get("skills") or {}).items()
    }
    compiled.setdefault("理解主旨要义", [])
    compiled["理解主旨要义"].extend([
        re.compile(r"(?i)best title"), re.compile(r"(?i)mainly about"),
        re.compile(r"最佳标题|标题"), re.compile(r"主旨|大意"),
    ])
    rows = con.execute(
        "SELECT origin_ref, stem FROM question_bank WHERE origin_ref LIKE 'ZK-LN-%' "
        "AND question_type='阅读理解(四选一)' ORDER BY origin_ref"
    ).fetchall()
    n_edge = n_sub = 0
    by_skill: Counter = Counter()
    for origin_ref, stem in rows:
        ym = re.search(r"ZK-LN-(\d{4})-", origin_ref)
        if not ym:
            continue
        year = int(ym.group(1))
        stem_q = (stem or "").split("|")[0].strip()
        skill = next((sk for sk, pats in compiled.items() if any(p.search(stem_q) for p in pats)), None)
        if not skill:
            continue
        qnode = f"question:{origin_ref}"
        if not con.execute("SELECT 1 FROM nodes WHERE concept_id=?", [qnode]).fetchone():
            con.execute(
                "INSERT INTO nodes VALUES (?, ?, ?, ?)",
                [qnode, "question", origin_ref, json.dumps({
                    "year": year, "province": "辽宁", "exam_type": "中考",
                    "question_type": "阅读理解(四选一)", "subquestion": True, "exam_stage": "zhongkao",
                }, ensure_ascii=False)],
            )
            n_sub += 1
        pnode = f"exam_point:{DIMENSION}:{skill}"
        if not con.execute("SELECT 1 FROM nodes WHERE concept_id=?", [pnode]).fetchone():
            con.execute(
                "INSERT INTO nodes VALUES (?, ?, ?, ?)",
                [pnode, "exam_point", skill, json.dumps({"dimension": DIMENSION}, ensure_ascii=False)],
            )
        con.execute(
            "DELETE FROM edges WHERE src_id=? AND relation='tests_exam_point' "
            "AND json_extract_string(evidence_json,'$.dimension')=?",
            [qnode, DIMENSION],
        )
        lineage = stamp(
            con, source_year=year, source_qid=origin_ref, provenance="curriculum_aligned_stem",
            derived_by="cognitive_junior_stem@v1",
            version_kinds={"exam_paper": "shenyang_zhongkao", "curriculum": "yiwu"},
        )
        con.execute(
            "INSERT INTO edges (src_id, dst_id, relation, weight, evidence_json) VALUES (?, ?, ?, ?, ?)",
            [qnode, pnode, "tests_exam_point", 1.0, json.dumps({
                "dimension": DIMENSION, "provenance": "curriculum_aligned_stem", "stem": stem_q,
                "curriculum_ref": "义务教育英语课程标准2022 + 陈康等阅读技能操作化",
                "exam_stage": "zhongkao", "lineage": lineage,
            }, ensure_ascii=False)],
        )
        n_edge += 1
        by_skill[skill] += 1
    return {"junior_reading_skill_edges": n_edge, "junior_reading_nodes": n_sub,
            "junior_reading_by_skill": dict(by_skill)}


def structure_subtype_distribution(con: duckdb.DuckDBPyConnection, exam_stage: str = "gaokao") -> dict:
    rows = con.execute(
        "SELECT json_extract_string(evidence_json,'$.subtype'), "
        "CAST(json_extract_string(evidence_json,'$.lineage.source_year') AS INT) "
        "FROM edges WHERE relation='tests_exam_point' "
        "AND json_extract_string(evidence_json,'$.dimension')=? "
        "AND json_extract_string(evidence_json,'$.provenance')=? "
        "AND COALESCE(json_extract_string(evidence_json,'$.exam_stage'),'gaokao')=?",
        [DIMENSION, PROVENANCE, exam_stage],
    ).fetchall()
    by_sub: Counter = Counter()
    by_year: dict[int, Counter] = defaultdict(Counter)
    for sub, yr in rows:
        sub = sub or "句际衔接"
        by_sub[sub] += 1
        if yr:
            by_year[int(yr)][sub] += 1
    tot = sum(by_sub.values())
    return {
        "parent_skill": SKILL, "exam_stage": exam_stage, "n_total": tot,
        "by_subtype": sorted(
            [{"label": k, "n": v, "pct": round(100 * v / tot, 1) if tot else 0} for k, v in by_sub.items()],
            key=lambda x: -x["n"]),
        "by_year": {y: dict(c) for y, c in sorted(by_year.items())},
        "unknown_n": by_sub.get("unknown", 0),
        "note": "L2 全覆盖: analysis/curated/discourse/fallback; unknown 必须为 0",
    }
