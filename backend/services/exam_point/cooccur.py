"""考点关联性分析 (件3 第三条腿 — 知识点关联性) — 同题共现的跨轴考点对.

核心竞争力第三腿: "辽宁新高考 哪些考点常一起考" (如 记叙文⨯人与社会, 说明文⨯人与自我)。
- 单一计算点 (Rule 1): 从 tests_exam_point 边自连算一次, **不落表** (188辽宁行~10ms, 物化只增 staleness §3.5);
- 按卷制 era 分层 (PIT §3.1, 不混算 2021 断点);
- co_n>=min_co 守门 (一次性同现不算"常一起考", 防伪关联);
- **跨轴 only**: theme_context(L1)与 theme_l2(L2) 同属 theme 轴, 互为 taxonomy 嵌套 (L2⊂L1 定义性同现),
  不是命题关联, 排除; 只保留 genre⨯theme 等跨轴对 (真命题模式)。
"""
from __future__ import annotations

import json

import duckdb

from backend.services.trend import scope
from backend.services.exam_point.loader import SUBQ_SOURCE_LIKE

_THEME_AXIS = {"theme_context", "theme_l2"}  # L1/L2 同属 theme 轴, 互相嵌套非命题关联


def _axis(dim: str | None) -> str:
    """考点维度 → 概念轴; theme L1/L2 归一为 theme 轴 (跨轴判定用)."""
    return "theme" if dim in _THEME_AXIS else (dim or "?")


def exam_point_cooccurrence(con: duckdb.DuckDBPyConnection, min_co: int = 2) -> dict:
    """辽宁考点跨轴共现 (同题≥min_co次), 按 era 分层 + 可信度门. 返回 {province_scope, min_co, by_era}."""
    era = scope.era_sql("q.year")
    rows = con.execute(f"""
        SELECT {era} AS era,
               json_extract_string(ea.evidence_json,'$.dimension') AS a_dim, na.label AS a_label,
               json_extract_string(eb.evidence_json,'$.dimension') AS b_dim, nb.label AS b_label,
               COUNT(DISTINCT q.question_id) AS co_n
        FROM edges ea
        JOIN edges eb ON ea.src_id = eb.src_id AND ea.dst_id < eb.dst_id
             AND ea.relation = 'tests_exam_point' AND eb.relation = 'tests_exam_point'
        JOIN exam_questions q ON ('question:' || q.question_id) = ea.src_id AND q.province LIKE '辽宁%'
             AND q.source_repo NOT LIKE '{SUBQ_SOURCE_LIKE}'
        JOIN nodes na ON na.concept_id = ea.dst_id
        JOIN nodes nb ON nb.concept_id = eb.dst_id
        GROUP BY 1, 2, 3, 4, 5
        HAVING COUNT(DISTINCT q.question_id) >= ?
    """, [min_co]).fetchall()
    diag = scope.diagnose(con)["by_segment"]
    by_era: dict[str, dict] = {}
    for era_v, a_dim, a_label, b_dim, b_label, co_n in rows:
        if _axis(a_dim) == _axis(b_dim):
            continue  # 同轴 (theme L1⨯L2) = taxonomy 嵌套, 非命题关联
        slot = by_era.setdefault(era_v, {"pairs": []})
        slot["pairs"].append({"a_dim": a_dim, "a_label": a_label,
                              "b_dim": b_dim, "b_label": b_label, "co_n": co_n})
    for era_v, slot in by_era.items():
        slot["pairs"].sort(key=lambda p: -p["co_n"])
        seg = diag.get(era_v, {})
        # 可信度门: era 总题不足 → 共现只作 raw count 参考, 不报为可信关联 (谄媚死防线)
        slot["distribution_eligible"] = bool(seg.get("distribution_eligible"))
        slot["era_total_questions"] = seg.get("total", 0)
    return {"province_scope": "辽宁卷", "min_co": min_co,
            "layered_by": "卷制 era (PIT §3.1)", "by_era": by_era}


def materialize_cooccurrence(con: duckdb.DuckDBPyConnection, min_co: int = 3) -> dict:
    """co_occurs 关联性入图 (调 exam_point_cooccurrence 单算 + 持久化, 关联性成 KG 一等公民).

    单一计算点 (Rule1): 共现仍只在 exam_point_cooccurrence 算一次, 本函数只持久化其输出。
    一边/对 (跨 era 合一行, era 拆分进 evidence.by_era 守 PIT §3.1); 只落 distribution_eligible era +
    min_co≥3 (防一次性同现伪关联, 谄媚死防线)。UNIQUE(src,dst,relation) 故同对跨 era 聚到一行。
    """
    con.execute("DELETE FROM edges WHERE relation = 'co_occurs'")
    data = exam_point_cooccurrence(con, min_co=min_co)
    pairs: dict[tuple, dict] = {}
    for era_v, slot in data["by_era"].items():
        if not slot.get("distribution_eligible"):
            continue
        for p in slot["pairs"]:
            a = f"exam_point:{p['a_dim']}:{p['a_label']}"
            b = f"exam_point:{p['b_dim']}:{p['b_label']}"
            key = (a, b) if a < b else (b, a)
            ev = pairs.setdefault(key, {"by_era": {}, "a_dim": p["a_dim"], "b_dim": p["b_dim"]})
            ev["by_era"][era_v] = p["co_n"]
    for (a, b), ev in pairs.items():
        total = sum(ev["by_era"].values())
        con.execute(
            "INSERT INTO edges (src_id, dst_id, relation, weight, evidence_json) VALUES (?, ?, ?, ?, ?)",
            [a, b, "co_occurs", float(total),
             json.dumps({"by_era": ev["by_era"], "total_co_n": total, "provenance": "cooccur_derived",
                         "a_dim": ev["a_dim"], "b_dim": ev["b_dim"]}, ensure_ascii=False)])
    return {"co_occurs 边": len(pairs), "min_co": min_co}
