"""设问类型 cognitive_skill 维度 — 子题级"怎么想" (KG层 A1 金矿; docs/kg_layer_design §2/§5).

真相源 = gaokao 教研解析显式题型标签 (explicit_label, 强于 dual_model)。坑16 已证: 光看设问句
inference 双模型会系统性低估"推断"(估15% 真相50%, 0分歧却一起错) → 必用解析显式标签。
子题级 (每子题考一种思维), 非 passage 级 — 子题 node(node_type=question, attrs.subquestion)
+ tests_exam_point(dimension=cognitive_skill) + stamp 血缘。子题 ID 空间(EN-XGKII-*)不入
exam_questions, 故 cognitive_skill 分布独立计 (单一计算点), 不混 genre/theme 的 passage 级分布。
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import duckdb

from backend.services.lineage import stamp
from backend.services.trend import scope

ROOT = Path(__file__).resolve().parents[3]
_SUBQ = ROOT / "data" / "structured" / "exam_subquestions" / "xgkii_2021_2025_subquestions.jsonl"
DIMENSION = "cognitive_skill"

# 教研解析题型 → 教育部考试中心《中国高考评价体系》7理解性技能 (官方真相源映射; 非阅读理解题不强标)
_SKILL_MAP = {
    "推理判断题": "推断",
    "细节理解题": "理解具体信息",
    "主旨大意题": "理解主旨要义",
    "词义猜测题": "理解词汇",
    "词句猜测题": "理解词汇",
}


def _skill_of(analysis: str | None) -> str | None:
    m = re.match(r"^([一-鿿]+题)", (analysis or "").strip())
    return _SKILL_MAP.get(m.group(1)) if m else None


def _ensure_node(con, cid: str, ntype: str, label: str, attrs: dict) -> int:
    if con.execute("SELECT 1 FROM nodes WHERE concept_id = ?", [cid]).fetchone():
        return 0
    con.execute("INSERT INTO nodes VALUES (?, ?, ?, ?)",
                [cid, ntype, label, json.dumps(attrs, ensure_ascii=False)])
    return 1


def _truth_valid_years(rows: list[dict]) -> set[int]:
    """入库即对真值锚交叉 (truth_anchor_protocol): 该年子题内容须含辽宁新高考II卷锚 markers,
    否则=源被误标(如 subquestions/mirror 2021 实为全国甲卷 Take a view), 剔除不入辽宁 cognitive_skill。
    """
    from collections import defaultdict

    from backend.services.truth_baseline import load_anchors
    anchors = load_anchors().get("exam", {}).get("anchors", {})
    by_year: dict[int, str] = defaultdict(str)
    for r in rows:
        by_year[int(r["year"])] += " " + (r.get("stem") or "") + " " + str(r.get("analysis") or "")
    valid = set()
    for y, txt in by_year.items():
        a = anchors.get(f"{y}:辽宁:gaokao")
        if a and a.get("lifecycle") == "active" and all(m.lower() in txt.lower() for m in a["markers"]):
            valid.add(y)
    return valid


def load_cognitive_skill(con: duckdb.DuckDBPyConnection) -> dict:
    """子题级设问类型入图: 子题node + exam_point:cognitive_skill节点 + tests_exam_point边(explicit_label+血缘).

    入库即对真值锚交叉: 源年内容不匹配辽宁II卷真值锚 → 剔除(防 mirror 2021甲卷误标混入辽宁, §7)。
    """
    rows = [json.loads(ln) for ln in _SUBQ.read_text(encoding="utf-8").splitlines() if ln.strip()]
    valid_years = _truth_valid_years(rows)
    n_sub = n_pt = n_edge = skipped = skip_mislabel = 0
    for r in rows:
        skill = _skill_of(r.get("analysis"))
        if not skill:                                  # 非阅读理解技能(完形/其他) 诚实不强标
            skipped += 1
            continue
        qid, year = r["id"], int(r["year"])
        if year not in valid_years:                    # 真值锚未过 = 源误标(甲卷冒辽宁), 剔除
            skip_mislabel += 1
            continue
        qnode = f"question:{qid}"                       # node_type=question 满足 tests_exam_point src 约束
        n_sub += _ensure_node(con, qnode, "question", qid, {
            "year": year, "province": r.get("province", "辽宁"), "exam_type": "高考",
            "passage_label": r.get("passage_label"), "question_number": r.get("question_number"),
            "question_type": r.get("question_type"), "subquestion": True})
        pnode = f"exam_point:{DIMENSION}:{skill}"
        n_pt += _ensure_node(con, pnode, "exam_point", skill, {"dimension": DIMENSION})
        if con.execute("SELECT 1 FROM edges WHERE src_id=? AND dst_id=? AND relation='tests_exam_point'",
                       [qnode, pnode]).fetchone():
            continue
        lineage = stamp(con, source_year=year, source_qid=qid, provenance="explicit_label",
                        derived_by="cognitive_skill@v1",
                        version_kinds={"exam_paper": "liaoning_gaokao", "curriculum": "gaozhong"})
        con.execute(
            "INSERT INTO edges (src_id, dst_id, relation, weight, evidence_json) VALUES (?, ?, ?, ?, ?)",
            [qnode, pnode, "tests_exam_point", 1.0,
             json.dumps({"dimension": DIMENSION, "provenance": "explicit_label", "lineage": lineage},
                        ensure_ascii=False)])
        n_edge += 1
    return {"子题node": n_sub, "cognitive_skill节点": n_pt, "tests_exam_point边": n_edge,
            "skipped(非阅读技能)": skipped, "skipped(真值锚未过=源误标甲卷)": skip_mislabel}


def cognitive_skill_distribution(con: duckdb.DuckDBPyConnection) -> dict:
    """设问类型分布 (单一计算点; 子题级 cognitive_skill 边按卷制 era 分层, 辽宁).

    子题 node 不 join exam_questions → era 从边 lineage.source_year 取(scope.segment); 全辽宁(标注源即辽宁§7)。
    """
    rows = con.execute(
        "SELECT n.label, json_extract_string(e.evidence_json, '$.lineage.source_year') "
        "FROM edges e JOIN nodes n ON n.concept_id = e.dst_id "
        "WHERE e.relation='tests_exam_point' "
        "AND json_extract_string(e.evidence_json, '$.dimension') = ?", [DIMENSION]).fetchall()
    by_era: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for label, yr in rows:
        era = scope.segment(int(yr)) if yr else "unknown"
        by_era[era][label] += 1
    out = {}
    for era, d in by_era.items():
        tot = sum(d.values())
        out[era] = sorted(
            [{"label": k, "n": v, "pct": round(100 * v / tot, 1)} for k, v in d.items()],
            key=lambda x: -x["n"])
    return {"dimension": DIMENSION, "province_scope": "辽宁卷",
            "provenance": "explicit_label (教研解析显式标签, 强于双模型)",
            "official_ref": "教育部考试中心《中国高考评价体系》7理解性技能",
            "n_total": len(rows), "by_era": out}
