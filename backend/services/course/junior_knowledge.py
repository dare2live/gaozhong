"""初中知识点详情(语法+词汇+短语三轴lineage整合) + 课程生成器 (Phase E4, 2026-07-08).

组织轴 = 46个真实教材单元(唯一有完整lineage的粒度), 不套用高中40节那套命题频次驱动
逻辑(用户明确纠正: 初中中考数据太薄[仅40题打了考点标签]撑不起频次分配, 高中40节本身
也待改进不该照抄)。每节课 = 1个真实教材单元, 挂载该单元的语法/词汇/短语真实lineage +
K12衔接(deepens到高中) + 中考真题印证(如有)。

n_lessons 默认 None = 用真实46单元(不硬编码任何数字, 遵循"模块+数据+配置文件"); 传参
时走最大余数法压缩/扩展(复用 course.syllabus 同款 _alloc/_adjust, Rule5 第2消费者)。

样本量诚实(坑12): 中考验证目前只覆盖语法(10个语法点/17题)和词汇(45题1846词边)两个维度,
短语维度暂无中考侧验证(zhongkao短语未建边, 见E3b范围声明); 不跨维度混算成单一"重要性
分数"，三轴分开陈列。
"""
from __future__ import annotations

import duckdb

from backend.services.course.syllabus import _adjust
from backend.services.thresholds import get_threshold

_VERSION = "hujiao"


def _units_in_order(con: duckdb.DuckDBPyConnection) -> list[tuple[str, int, str]]:
    return con.execute(
        "SELECT volume_key, unit_number, title_en FROM units WHERE version_key=? "
        "ORDER BY CASE volume_key WHEN '7a' THEN 1 WHEN '7b' THEN 2 WHEN '8a' THEN 3 "
        "WHEN '8b' THEN 4 WHEN '9a' THEN 5 WHEN '9b' THEN 6 END, unit_number",
        [_VERSION],
    ).fetchall()


def _grammar_for_unit(con: duckdb.DuckDBPyConnection, vol: str, unit: int) -> list[dict]:
    """该单元Grammar板块教的语法点 + K12衔接(deepens) + 中考真题印证(tests_grammar反查)."""
    rows = con.execute(
        "SELECT go.grammar_item_id, n.label FROM grammar_occurrences go "
        "JOIN nodes n ON n.concept_id = 'grammar:jr:' || go.grammar_item_id "
        "WHERE go.version_key=? AND go.volume_key=? AND go.unit_number=?",
        [_VERSION, vol, unit],
    ).fetchall()
    out = []
    for gid, label in rows:
        jr_cid = f"grammar:jr:{gid}"
        senior = con.execute(
            "SELECT dst_id FROM edges WHERE relation='deepens' AND src_id=?", [jr_cid]
        ).fetchone()
        exam_status = None
        if senior:
            r = con.execute("SELECT attrs_json FROM nodes WHERE concept_id=?", [senior[0]]).fetchone()
            if r and r[0]:
                import json
                exam_status = json.loads(r[0]).get("exam_status")
        zk = con.execute(
            "SELECT DISTINCT SUBSTR(src_id, 10) FROM edges WHERE relation='tests_grammar' AND dst_id=?",
            [jr_cid],
        ).fetchall()
        out.append({"grammar_item_id": gid, "label": label,
                    "senior_exam_status": exam_status,
                    "zhongkao_verified_questions": sorted(q for (q,) in zk)})
    return out


def _vocab_for_unit(con: duckdb.DuckDBPyConnection, vol: str, unit: int) -> dict:
    """该单元引入的词 + 学段(at_stage边) + 中考真实曝光(tests_word反查)."""
    rows = con.execute(
        "SELECT word, pos, zh_def FROM unit_vocab_intro "
        "WHERE version_key=? AND volume_key=? AND unit_number=?", [_VERSION, vol, unit],
    ).fetchall()
    words = []
    for w, pos, zh in rows:
        stage_row = con.execute(
            "SELECT dst_id FROM edges WHERE relation='at_stage' AND src_id=?", [f"word:{w}"]
        ).fetchone()
        zk_n = con.execute(
            "SELECT COUNT(*) FROM edges WHERE relation='tests_word' AND dst_id=? "
            "AND src_id LIKE 'question:ZK-%'", [f"word:{w}"],
        ).fetchone()[0]
        words.append({"word": w, "pos": pos, "zh_def": zh,
                      "stage": stage_row[0].replace("stage:", "") if stage_row else None,
                      "zhongkao_exposure_count": zk_n})
    n_overrun = sum(1 for w in words if w["stage"] in ("高中必修", "高中选修", "校本超纲"))
    return {"words": words, "n_total": len(words), "n_overrun": n_overrun}


def _phrases_for_unit(con: duckdb.DuckDBPyConnection, vol: str, unit: int) -> list[dict]:
    """该单元教材短语 + 是否在高中真题库(renjiao/waiyan)复现."""
    rows = con.execute(
        "SELECT canonical, phrase_type FROM phrases "
        "WHERE version_key=? AND volume_key=? AND unit_number=?", [_VERSION, vol, unit],
    ).fetchall()
    senior = {c.strip().lower() for (c,) in con.execute(
        "SELECT DISTINCT canonical FROM phrases WHERE version_key != ?", [_VERSION]).fetchall()}
    return [{"canonical": c, "phrase_type": t, "recurs_in_senior_textbook": c.strip().lower() in senior}
            for c, t in rows]


def unit_knowledge_profile(con: duckdb.DuckDBPyConnection, vol: str, unit: int, title_en: str) -> dict:
    """单个教材单元的三轴知识点lineage整合(不跨轴混算重要性分数, 坑12分层非平均)."""
    return {
        "volume_key": vol, "unit_number": unit, "title_en": title_en,
        "grammar": _grammar_for_unit(con, vol, unit),
        "vocab": _vocab_for_unit(con, vol, unit),
        "phrases": _phrases_for_unit(con, vol, unit),
        "scope_note": "中考真题印证仅覆盖语法(10点/17题)+词汇(45题1846词边)两轴; "
                      "短语轴暂无中考侧验证边(E3b范围声明); 三轴不混算单一重要性分数。",
    }


def _lessons_uncompressed(con: duckdb.DuckDBPyConnection,
                          units: list[tuple[str, int, str]]) -> list[dict]:
    """不压缩: 每单元独立1节(真实教学进度, 默认路径)."""
    return [{"seq": seq, "segment_id": f"jr-seg-{seq:02d}",
            **unit_knowledge_profile(con, vol, unit, title)}
            for seq, (vol, unit, title) in enumerate(units, 1)]


def _merge_vocab(profiles: list[dict]) -> dict:
    return {"words": [w for p in profiles for w in p["vocab"]["words"]],
            "n_total": sum(p["vocab"]["n_total"] for p in profiles),
            "n_overrun": sum(p["vocab"]["n_overrun"] for p in profiles)}


def _merge_group(con: duckdb.DuckDBPyConnection, seq: int,
                 group: list[tuple[str, int, str]]) -> dict:
    """压缩路径: 一组连续单元的三轴lineage拼合成1节(不跨轴混算, 各轴列表直接拼接)."""
    profiles = [unit_knowledge_profile(con, v, u, t) for v, u, t in group]
    units_covered = [{"volume_key": v, "unit_number": u, "title_en": t} for v, u, t in group]
    grammar = [g for p in profiles for g in p["grammar"]]
    phrases = [ph for p in profiles for ph in p["phrases"]]
    return {"seq": seq, "segment_id": f"jr-seg-{seq:02d}", "units_covered": units_covered,
            "grammar": grammar, "vocab": _merge_vocab(profiles), "phrases": phrases,
            "scope_note": profiles[0]["scope_note"] if profiles else None}


def _lessons_compressed(con: duckdb.DuckDBPyConnection, units: list[tuple[str, int, str]],
                        n_lessons: int) -> list[dict]:
    """压缩: 按最大余数法把单元分组进n_lessons节(复用course.syllabus同款_adjust, Rule5)."""
    base = [len(units) // n_lessons] * n_lessons
    raw = [len(units) / n_lessons] * n_lessons
    alloc = _adjust(base, raw, len(units))
    lessons, idx = [], 0
    for seq, k in enumerate(alloc, 1):
        lessons.append(_merge_group(con, seq, units[idx:idx + k]))
        idx += k
    return lessons


def junior_syllabus(con: duckdb.DuckDBPyConnection, n_lessons: int | None = None) -> dict:
    """初中课程生成器: 46个真实单元逐一整合三轴lineage; n_lessons=None时不压缩(真实单元数)。

    与高中 course.syllabus 的关键区别(用户2026-07-08纠正): 高中按命题频次(theme_l2)最大
    余数法分配, 初中数据太薄撑不起该逻辑, 改用真实教材单元1:1(或config指定n_lessons时走
    同一套_adjust最大余数法压缩/合并, 逻辑复用不重写)。
    """
    units = _units_in_order(con)
    if n_lessons is None:
        n_lessons = get_threshold("course.total_courses_junior", len(units))
    lessons = (_lessons_uncompressed(con, units) if n_lessons >= len(units)
               else _lessons_compressed(con, units, n_lessons))
    return {"n_lessons": len(lessons), "n_units_total": len(units), "lessons": lessons,
            "organizing_axis": "真实教材单元进度(非命题频次, 与高中course.syllabus方法论"
                                "刻意不同, 见模块docstring)",
            "content": None}
