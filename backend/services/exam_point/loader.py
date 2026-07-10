"""考点 canonical 维度入库 (件2) — 双模型标注 artifact → nodes(exam_point) + edges(tests_exam_point).

来源: data/structured/exam_point/genre_theme_labels.jsonl (双模型分类, 一致=dual_model_agree)。
诚实红线:
  - **只落 dual_model_agree / cross_verified 且非 NA** 的边 (歧义 needs_review / 无正文 NA 不入,
    宁缺毋滥); cross_verified=analysis 显式体裁句交叉验证升档(坑16)。
  - 节点**懒建**: 只为实际出现的考点 label 建 exam_point 节点, 避免 taxonomy 全集造 orphan。
取代 tests_word 把整篇实词当"考点"的 token 假象 (critic 盲点 #2)。
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

from backend.services.trend import scope

ROOT = Path(__file__).resolve().parents[3]
_EP_DIR = ROOT / "data" / "structured" / "exam_point"
LABELS_PATH = _EP_DIR / "genre_theme_labels.jsonl"
THEME_L2_PATH = _EP_DIR / "theme_l2_labels.jsonl"
# 注: 课标主题语境官方仅 L1(3大主题)+ L2(10主题群) 可枚举 (亲验 PDF 表2)。
# 曾有 theme_l3(35"子主题")= 杜撰 taxonomy + dual_model 贴标签, 经真值核验已废 (2026-06-21)。

# 标注字段 dimension → exam_point node 维度名 (与 taxonomy node_id_pattern 对齐)
# theme=L1(3大主题, 粗) 与 theme_l2=课标官方10主题群(细) 并存 (Rule 6 可扩展; L2 含 L1)
_DIMENSIONS = (("genre", "genre_prov", "genre"),
               ("theme", "theme_prov", "theme_context"))


def point_node_id(dimension: str, label: str) -> str:
    return f"exam_point:{dimension}:{label}"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def ensure_point_node(con: duckdb.DuckDBPyConnection, dimension: str, label: str) -> bool:
    """懒建 exam_point 节点 (只为实际出现的考点); 返回是否新建."""
    nid = point_node_id(dimension, label)
    if con.execute("SELECT 1 FROM nodes WHERE concept_id = ?", [nid]).fetchone():
        return False
    con.execute("INSERT INTO nodes VALUES (?, ?, ?, ?)",
                [nid, "exam_point", label, json.dumps({"dimension": dimension}, ensure_ascii=False)])
    return True


def add_point_edge(con: duckdb.DuckDBPyConnection, qnode: str, dimension: str,
                    label, prov, cue) -> tuple[int, int, int]:
    """落一条 question→exam_point 边 (dual_model_agree / cross_verified, 非 NA). 返回 (nodes+, edges+, skipped)."""
    if label == "NA" or not label:
        return (0, 0, 0)
    if prov not in ("dual_model_agree", "cross_verified"):
        return (0, 0, 1)
    nm = int(ensure_point_node(con, dimension, label))
    pnode = point_node_id(dimension, label)
    if con.execute("SELECT 1 FROM edges WHERE src_id=? AND dst_id=? AND relation='tests_exam_point'",
                   [qnode, pnode]).fetchone():
        return (nm, 0, 0)
    con.execute(
        "INSERT INTO edges (src_id, dst_id, relation, weight, evidence_json) VALUES (?, ?, ?, ?, ?)",
        [qnode, pnode, "tests_exam_point", 1.0,
         json.dumps({"dimension": dimension, "provenance": prov, "cue": (cue or "")[:200]},
                    ensure_ascii=False)])
    return (nm, 1, 0)


def node_exists(con: duckdb.DuckDBPyConnection, concept_id: str) -> bool:
    return bool(con.execute("SELECT 1 FROM nodes WHERE concept_id = ?", [concept_id]).fetchone())


def load_exam_points(con: duckdb.DuckDBPyConnection, labels_path: Path = LABELS_PATH,
                     theme_l2_path: Path = THEME_L2_PATH) -> dict:
    """读标注 artifact → 落 exam_point 节点 + tests_exam_point 边 (只 dual_model_agree, 非 NA).

    两源: genre_theme_labels(genre + theme L1 3大主题) + theme_l2_labels(课标官方10主题群)。
    (Rule5 2026-07-07: labels_path/theme_l2_path 参数化, 供 junior/exam_point.py 第2消费者
    传初中artifact路径复用同一套逻辑, 默认值保持高中原调用点不变。)
    """
    nodes_made = edges_made = skipped = 0
    for row in read_jsonl(labels_path):
        qnode = f"question:{row['question_id']}"
        if not node_exists(con, qnode):
            continue
        for label_key, prov_key, dimension in _DIMENSIONS:
            nm, em, sk = add_point_edge(con, qnode, dimension,
                                        row.get(label_key), row.get(prov_key), row.get("evidence"))
            nodes_made += nm; edges_made += em; skipped += sk
    l2_rows = read_jsonl(theme_l2_path)
    for row in l2_rows:
        qnode = f"question:{row['question_id']}"
        if not node_exists(con, qnode):
            continue
        nm, em, sk = add_point_edge(con, qnode, "theme_l2",
                                    row.get("theme_l2"), row.get("prov"), row.get("evidence"))
        nodes_made += nm; edges_made += em; skipped += sk
    return {"labels": len(read_jsonl(labels_path)), "theme_l2_labels": len(l2_rows),
            "nodes_made": nodes_made, "edges_made": edges_made, "skipped_needs_review": skipped}


# 卷制断点 (PIT §3.1) 走 trend.scope 单点, 不再各自硬编码 2021 (与 segment() 同口径)。
_ERA_SQL = scope.era_sql("q.year")

# 篇章级口径 (RC1 后端审计 #1, 2026-06-27): genre/theme 是**篇章属性**(整篇一个体裁/主题群);
# eol 2021/2022 源按**子题**存(每篇 N 行)→ 这些维度若按子题计, 1 篇 25 子题 = 记 25 次(失真~5x:
# 记叙文 55.8% 实为子题膨胀, 篇章级真值~30%; "命题迁移 +24pt"是纯口径伪迁移)。
# 故 genre/theme/theme_l2 的分布/共现**排除子题级源**, 与篇章级年份(2015-20/2023-26)apples-to-apples。
# cognitive_skill 是**子题属性**(每子题 1 题型, 审计 100/100 对账正确), 不在此列, 照常计子题。
# 2021/2022 待 eol 篇章重建后再以篇章级纳入 genre/theme(当前 schema 无篇章边界, 见 docs)。
PASSAGE_LEVEL_DIMS = ("genre", "theme_context", "theme_l2")
SUBQ_SOURCE_LIKE = "eol_xgkii%"   # 子题级源鉴别 (source_repo); 单一真相源, cooccur 等复用
# SQL 片段: 篇章级维度边须来自非子题级源 (cognitive_skill 维度不受限)
_PASSAGE_DIM_SQL = (
    "NOT (json_extract_string(e.evidence_json, '$.dimension') IN ('genre','theme_context','theme_l2') "
    f"AND q.source_repo LIKE '{SUBQ_SOURCE_LIKE}')")


def bridge_exam_point_themes(con: duckdb.DuckDBPyConnection) -> dict:
    """桥接 exam_point 主题考点 ↔ 教材 theme 节点 (同课标主题群) — 补 4 路追溯断缝.

    真题 → exam_point:theme_l2:历史社会文化 → (theme_aligns) → theme:人与社会/历史社会文化
    → (theme_of_unit) → 教材单元。让老师从"这题考某主题"跳到"哪个教材单元也讲该主题"。
    匹配: L1 exam_point:theme_context:{X} → theme:{X}; L2 exam_point:theme_l2:{X} → theme:%/{X}(2级路径)。
    (官方仅 L1/L2 两级; 杜撰 L3 桥已废, 见 load_exam_points 注。)
    """
    made = 0
    # L1: theme_context → theme:{label}
    for ep, tgt in con.execute(
        "SELECT ep.concept_id, t.concept_id FROM nodes ep "
        "JOIN nodes t ON t.node_type='theme' AND t.concept_id = 'theme:' || ep.label "
        "WHERE ep.concept_id LIKE 'exam_point:theme_context:%'").fetchall():
        made += _bridge_edge(con, ep, tgt)
    # L2: theme_l2 → theme:{L1}/{label} (2 级路径: 恰 1 个斜杠)
    for ep, tgt in con.execute(
        "SELECT ep.concept_id, t.concept_id FROM nodes ep "
        "JOIN nodes t ON t.node_type='theme' AND t.concept_id LIKE 'theme:%/' || ep.label "
        "  AND length(t.concept_id) - length(replace(t.concept_id, '/', '')) = 1 "
        "WHERE ep.concept_id LIKE 'exam_point:theme_l2:%'").fetchall():
        made += _bridge_edge(con, ep, tgt)
    return {"theme_aligns_edges": made}


def _bridge_edge(con: duckdb.DuckDBPyConnection, src: str, dst: str) -> int:
    if con.execute("SELECT 1 FROM edges WHERE src_id=? AND dst_id=? AND relation='theme_aligns'",
                   [src, dst]).fetchone():
        return 0
    con.execute(
        "INSERT INTO edges (src_id, dst_id, relation, weight, evidence_json) VALUES (?, ?, ?, ?, ?)",
        [src, dst, "theme_aligns", 1.0, '{"basis":"同课标主题群"}'])
    return 1


def exam_point_distribution(con: duckdb.DuckDBPyConnection,
                            dimension: str | None = None) -> dict:
    """辽宁考点分布 — **按卷制 era 分层 + 占比** (单一计算点, 从 tests_exam_point 边算一次).

    用户 2026-06-15 纠偏: 不取全历史平均(会抹掉时间轴结构), 分时间轴/卷制分层看 (PIT §3.1)。
    返回 {era: {dimension: [{label, n, pct}]}}, 每段内 dimension 各 label 占比独立计。
    """
    rows = con.execute(f"""
        SELECT {_ERA_SQL} AS era,
               json_extract_string(e.evidence_json, '$.dimension') AS dim,
               n.label, COUNT(*) AS c
        FROM edges e
        JOIN nodes n ON n.concept_id = e.dst_id
        JOIN exam_questions q
          ON ('question:' || q.question_id) = e.src_id AND q.province LIKE '辽宁%'
        WHERE e.relation = 'tests_exam_point'
          AND {_PASSAGE_DIM_SQL}
        GROUP BY 1, 2, 3
    """).fetchall()
    totals: dict[tuple, int] = {}
    for era, dim, _label, c in rows:
        totals[(era, dim)] = totals.get((era, dim), 0) + c
    by_era: dict[str, dict[str, list]] = {}
    for era, dim, label, c in rows:
        if dimension and dim != dimension:
            continue
        by_era.setdefault(era, {}).setdefault(dim, []).append(
            {"label": label, "n": c, "pct": round(100 * c / totals[(era, dim)], 1)})
    for era in by_era:
        for dim in by_era[era]:
            by_era[era][dim].sort(key=lambda r: -r["n"])
    return by_era


def exam_point_shift(con: duckdb.DuckDBPyConnection, top: int = 6) -> dict:
    """命题迁移 — 新旧 era 占比做差 (审计HIGH#18; 派生事实在 service 算一次, 前端不重算 Rule1).

    返回 {dimension: [{label, then_pct, now_pct, delta, n_new, n_old}]} 按 |delta| 降序 top N。
    era 同 distribution 分层 (NEW=最新卷制在前); <2 era 无可迁移返 {}。
    坑(2026-07-06 数据关联设计审查): 结论卡"最大命题迁移"条原完全不显示样本量(比同卡b条更不
    透明), n_new/n_old 补上样本数, 供前端小样本时降级/标注方向性(不影响delta本身算法, 单一计算点)。
    """
    by_era = exam_point_distribution(con)
    eras = sorted(by_era, reverse=True)
    if len(eras) < 2:
        return {"eras": eras, "by_dimension": {}}
    new_era, old_era = eras[0], eras[1]
    dims = {d for era in by_era.values() for d in era}
    out: dict[str, list] = {}
    for dim in dims:
        old_map = {x["label"]: x for x in by_era.get(old_era, {}).get(dim, [])}
        rows = [{"label": x["label"], "then_pct": old_map.get(x["label"], {}).get("pct", 0.0),
                 "now_pct": x["pct"], "delta": round(x["pct"] - old_map.get(x["label"], {}).get("pct", 0.0), 1),
                 "n_new": x["n"], "n_old": old_map.get(x["label"], {}).get("n", 0)}
                for x in by_era.get(new_era, {}).get(dim, [])]
        rows.sort(key=lambda r: -abs(r["delta"]))
        out[dim] = rows[:top]
    return {"eras": [new_era, old_era], "by_dimension": out}
