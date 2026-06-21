"""主题语境真值校验器 (theme 域; 模块化扩展 — 新域=加一个 checker, 核心不动).

课标主题语境官方仅 L1(3大主题语境)+L2(10主题群)可枚举 (亲验 PDF §四(一)表2 p22-23);
"第三级"是32条段落式"内容要求"(只挂L1、一句含多概念), 非子主题词条。
曾杜撰35个theme_l3(extract_curriculum _reader不读PDF直接塞 + dual_model贴标签)→ 2026-06-21真值核验已废。
本 checker 守门: (a)官方L2 markers全在(active锚内容匹配); (b)无杜撰L3复活(边/level3/depth2节点)。
"""
from __future__ import annotations

from .base import Deviation, TruthChecker, load_anchors


def _theme_anchors() -> dict:
    return (load_anchors().get("theme") or {}).get("anchors") or {}


def _fab_counts(con) -> tuple[int, int, int]:
    """杜撰 theme_l3 在 DB 的三处落点计数 (边 / theme_contexts.level3 / theme depth2 叶节点)."""
    edge = con.execute(
        "SELECT COUNT(*) FROM edges WHERE dst_id LIKE 'exam_point:theme_l3:%' "
        "OR src_id LIKE 'exam_point:theme_l3:%'").fetchone()[0]
    ctx = con.execute(
        "SELECT COUNT(*) FROM theme_contexts WHERE level3 IS NOT NULL AND TRIM(level3)<>''").fetchone()[0]
    node = con.execute(
        "SELECT COUNT(*) FROM nodes WHERE node_type='theme' "
        "AND length(concept_id)-length(replace(concept_id,'/',''))>=2").fetchone()[0]
    return edge, ctx, node


class ThemeTruthChecker(TruthChecker):
    domain = "theme"

    def check(self, con) -> list[Deviation]:
        out: list[Deviation] = []
        anchors = _theme_anchors()
        # (a) active 锚: 官方 L2 主题群 markers 全在 (内容匹配第一手源, 防误删官方层)
        a = anchors.get("official_l1_l2") or {}
        if a.get("lifecycle") == "active":
            # theme 节点 label 是全路径(人与社会/历史、社会与文化), 取末段=L2群名比对
            present = {r[0].rsplit("/", 1)[-1] for r in con.execute(
                "SELECT label FROM nodes WHERE node_type='theme'").fetchall()}
            missing = [m for m in (a.get("markers") or []) if m not in present]
            if missing:
                out.append(Deviation("theme", "official_l1_l2", "content_mismatch", "BLOCK",
                                     f"官方L2主题群缺失(误删?): {missing}"))
        # (b) 无杜撰 L3 复活 (官方无可枚举第三级, 亲验PDF表2)
        edge, ctx, node = _fab_counts(con)
        if edge or ctx or node:
            out.append(Deviation("theme", "no_enumerable_l3", "pollution", "BLOCK",
                                 f"杜撰theme_l3复活: {edge}边 / {ctx}个level3 / {node}个depth2叶节点; "
                                 "课标主题语境无可枚举第三级(亲验PDF表2)→ 必为0"))
        return out

    def self_test(self) -> bool:
        import duckdb
        c = duckdb.connect(":memory:")
        c.execute("CREATE TABLE edges(src_id VARCHAR, dst_id VARCHAR)")
        c.execute("CREATE TABLE theme_contexts(level3 VARCHAR)")
        c.execute("CREATE TABLE nodes(concept_id VARCHAR, node_type VARCHAR, label VARCHAR)")
        c.execute("INSERT INTO edges VALUES ('question:x', 'exam_point:theme_l3:文化遗产')")  # 注入杜撰L3边
        polluted = [d for d in self.check(c) if d.kind == "pollution"]
        c.execute("DELETE FROM edges")
        clean = [d for d in self.check(c) if d.kind == "pollution"]
        c.close()
        return bool(polluted) and not clean
