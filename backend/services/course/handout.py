"""讲义生成 — 1 节 → 7 段 markdown.

段顺序: hook / review / core / relations / exam_trace / practice / homework
"""
from __future__ import annotations

from typing import Any

import duckdb

from . import homework, relations

SEGMENTS = ["hook", "review", "core", "relations", "exam_trace", "practice", "homework"]


def render_handout(con: duckdb.DuckDBPyConnection, course: dict) -> dict[str, Any]:
    """返 {md, segments: {seg_name: text}}."""
    segs: dict[str, str] = {
        "hook": _seg_hook(course),
        "review": _seg_review(course),
        "core": _seg_core(course),
        "relations": _seg_relations(con, course),
        "exam_trace": _seg_exam_trace(con, course),
        "practice": _seg_practice(course),
        "homework": _seg_homework(con, course),
    }
    md = _join_md(course, segs)
    return {"md": md, "segments": segs, "n_segments": len(segs)}


def _seg_hook(c: dict) -> str:
    theme = c.get("themes_main") or "(主题待补)"
    return f"### 开场 hook (Time/NatGeo/SciAm 风)\n\n本节主题: **{theme}**\n建议导入: 一段相关新闻片段或图片 (3-5 min).\n"


def _seg_review(c: dict) -> str:
    return f"### 上节复习 (5 题 quick check)\n\n抽自上节作业同 tag 的 5 题, 5-10 min.\n"


def _seg_core(c: dict) -> str:
    lines = ["### 核心教学\n"]
    for it in c.get("core_items") or []:
        pos = it.get("position", "(无位置)")
        lines.append(f"- **{it['kind']}: {it['id']}** [{c['layer']}·{pos}]")
    return "\n".join(lines) + "\n"


def _seg_relations(con: duckdb.DuckDBPyConnection, c: dict) -> str:
    lines = ["### 关联拓展 (R1 ≥3)\n"]
    for it in c.get("core_items") or []:
        rels = relations.related_concepts(con, it["id"])
        names = ", ".join(f"{r['type']}:{r['label']}" for r in rels[:5])
        lines.append(f"- **{it['id']}** → {names}")
    return "\n".join(lines) + "\n"


def _seg_exam_trace(con: duckdb.DuckDBPyConnection, c: dict) -> str:
    htags = c.get("homework_tags") or []
    if not htags:
        return "### 真题溯源\n\n(无 homework_tags, 跳过)\n"
    placeholders = ",".join("?" * len(htags))
    rows = con.execute(
        f"SELECT qb.qb_id, qb.question_type, SUBSTR(qb.stem, 1, 80) "
        f"FROM question_bank qb JOIN question_tags qt ON qt.qb_id = qb.qb_id "
        f"WHERE qt.tag_id IN ({placeholders}) AND qb.origin='real' "
        f"ORDER BY qb.qb_id LIMIT 5",
        htags,
    ).fetchall()
    lines = ["### 真题溯源\n"]
    for qid, qt, stem in rows:
        lines.append(f"- 真题 #{qid} ({qt}): {stem}...")
    if not rows:
        lines.append("- (近 5 年真题暂无直接命中)")
    return "\n".join(lines) + "\n"


def _seg_practice(c: dict) -> str:
    scens = c.get("themes_aux") or []
    lines = ["### 场景练习 (R3 ≥3 场景)\n"]
    lines.append(f"- 主选: {c.get('themes_main') or '(待补)'}")
    for s in scens:
        lines.append(f"- 副选: {s}")
    return "\n".join(lines) + "\n"


def _seg_homework(con: duckdb.DuckDBPyConnection, c: dict) -> str:
    qs = homework.pick_homework(con, c.get("homework_tags") or [])
    lines = ["### 课后作业 (R4: tag ⊆ 本节)\n"]
    for q in qs:
        lines.append(f"- #{q['qb_id']} [{q['question_type']}, {q['difficulty']}]: {q['stem'][:60]}...")
    if not qs:
        lines.append("- (题库未命中本节 tag, 待 #37 灌齐题库标签)")
    return "\n".join(lines) + "\n"


def _join_md(c: dict, segs: dict[str, str]) -> str:
    head = f"# 第 {c['course_id']} 节 · [{c['layer']}] {c.get('title', '(无标题)')}\n\n"
    head += f"_block_kind: {c['block_kind']} · {c.get('duration_min', 120)} min_\n\n---\n\n"
    body = "\n---\n\n".join(segs[s] for s in SEGMENTS)
    return head + body
