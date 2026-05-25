"""讲义生成 — 1 节 → 7 段 markdown.

段顺序: hook / review / core / relations / exam_trace / practice / homework / summary
优先加载 enriched_content yaml (Phase 7.1 人工制作的完整教学内容).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import yaml

from . import homework, relations
from .loader import get_threshold as _t

ENRICHED_DIR = Path(__file__).resolve().parents[2] / "config" / "enriched_content"


def _load_enriched(course_id: int) -> dict | None:
    """加载 enriched_content yaml, 返回 segments dict 或 None."""
    for pattern in [f"g_final_{course_id}.yaml", f"g3_{course_id}.yaml",
                    f"g2_{course_id}.yaml", f"g1_{course_id}.yaml",
                    f"course_{course_id}.yaml"]:
        path = ENRICHED_DIR / pattern
        if path.exists():
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            return data.get("segments", {})
    return None

SEGMENTS = ["hook", "review", "core", "relations", "exam_trace", "practice", "homework"]


def _clink(cid: str, label: str | None = None) -> str:
    """Render concept HTML link — graph_popup.js 自动绑定点击弹联通图 + 真题."""
    safe = (label or cid).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<a class="gz-concept" data-concept="{cid}">{safe}</a>'


def render_handout(con: duckdb.DuckDBPyConnection, course: dict) -> dict[str, Any]:
    """返 {md, segments: {seg_name: text}}. 优先使用 enriched_content yaml."""
    enriched = _load_enriched(course["course_id"])
    if enriched:
        segs = {
            "hook": enriched.get("hook", _seg_hook(course)),
            "review": _seg_review(course),
            "core": enriched.get("core", _seg_core(course)),
            "relations": enriched.get("relations", _seg_relations(con, course)),
            "exam_trace": _seg_exam_trace(con, course),
            "practice": enriched.get("practice", _seg_practice(course)),
            "homework": _seg_homework(con, course),
            "summary": enriched.get("summary", ""),
        }
    else:
        segs = {
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
        label = it["id"].split(":", 1)[-1] if ":" in it["id"] else it["id"]
        lines.append(f"- **{it['kind']}**: {_clink(it['id'], label)} [{c['layer']}·{pos}]")
    return "\n".join(lines) + "\n"


def _seg_relations(con: duckdb.DuckDBPyConnection, c: dict) -> str:
    lines = ["### 关联拓展 (R1 ≥3, 点任一关联弹联通图)\n"]
    for it in c.get("core_items") or []:
        rels = relations.related_concepts(con, it["id"])
        names = ", ".join(_clink(r["id"], f"{r['type']}:{r['label']}") for r in rels[:5])
        center = _clink(it["id"], it["id"].split(":", 1)[-1])
        lines.append(f"- **{center}** → {names}")
    return "\n".join(lines) + "\n"


def _seg_exam_trace(con: duckdb.DuckDBPyConnection, c: dict) -> str:
    htags = c.get("homework_tags") or []
    if not htags:
        return "### 真题溯源\n\n(无 homework_tags, 跳过)\n"
    placeholders = ",".join("?" * len(htags))
    rows = con.execute(
        f"SELECT qb.qb_id, qb.question_type, SUBSTR(qb.stem, 1, {_t('text.stem_display_chars', 40)}), qb.origin_ref "
        f"FROM question_bank qb JOIN question_tags qt ON qt.qb_id = qb.qb_id "
        f"WHERE qt.tag_id IN ({placeholders}) AND qb.origin='real' "
        f"ORDER BY qb.qb_id LIMIT {_t('course.exam_trace_limit', 5)}",
        htags,
    ).fetchall()
    lines = ["### 真题溯源 (点题号弹原题 + 联通图)\n"]
    for qid, qt, stem, oref in rows:
        link = _clink(f"question:{oref}", f"#{qid}") if oref else f"#{qid}"
        lines.append(f"- 真题 {link} ({qt}): {stem}...")
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
    lines = ["### 课后作业 (R4: tag ⊆ 本节, 点题号弹原题 + 联通图)\n"]
    # batch 查 origin_ref → concept_id
    qb_ids = [q["qb_id"] for q in qs]
    oref_map: dict = {}
    if qb_ids:
        placeholders = ",".join("?" * len(qb_ids))
        for qid, oref in con.execute(
            f"SELECT qb_id, origin_ref FROM question_bank WHERE qb_id IN ({placeholders})",
            qb_ids,
        ).fetchall():
            oref_map[qid] = oref
    for q in qs:
        oref = oref_map.get(q["qb_id"])
        link = _clink(f"question:{oref}", f"#{q['qb_id']}") if oref else f"#{q['qb_id']}"
        lines.append(f"- {link} [{q['question_type']}, {q['difficulty']}]: {q['stem'][:40]}...")
    if not qs:
        lines.append("- (题库未命中本节 tag)")
    return "\n".join(lines) + "\n"


def _join_md(c: dict, segs: dict[str, str]) -> str:
    head = f"# 第 {c['course_id']} 节 · [{c['layer']}] {c.get('title', '(无标题)')}\n\n"
    head += f"_block_kind: {c['block_kind']} · {c.get('duration_min', 120)} min_\n\n---\n\n"
    body = "\n---\n\n".join(segs[s] for s in SEGMENTS)
    return head + body
