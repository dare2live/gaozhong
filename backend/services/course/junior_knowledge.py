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
from backend.services.vocab_pos import pos_distribution

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
    return {"words": words, "n_total": len(words), "n_overrun": n_overrun,
            "pos_distribution": pos_distribution(words)}


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


def _passages_for_unit(con: duckdb.DuckDBPyConnection, vol: str, unit: int) -> list[dict]:
    """教材正文: section_text.raw_text join sections 取标题/类型, 按 seq.

    与高中 textbook_content._passages 同一写法(Rule5 第2消费者), 唯一差异是 version_key
    固定 hujiao(初中单版本, 不像高中要按 waiyan/renjiao 参数切换), 故不强行抽公用函数
    (四列SQL, 抽共享反而多一层间接, 奥卡姆剃刀——两处保持写法一致即可, 不是同一份代码)。
    """
    from backend.api.db import rows_to_dicts
    return rows_to_dicts(con.execute(
        "SELECT st.seq AS seq, s.kind AS kind, s.title AS title, st.raw_text AS text, st.n_chars AS n_chars, "
        "s.is_narrative AS is_narrative, s.is_applied AS is_applied, s.is_listening AS is_listening "
        "FROM section_text st "
        "LEFT JOIN sections s ON s.version_key=st.version_key AND s.volume_key=st.volume_key "
        "  AND s.unit_number=st.unit_number AND s.seq=st.seq "
        "WHERE st.version_key=? AND st.volume_key=? AND st.unit_number=? ORDER BY st.seq",
        [_VERSION, vol, unit]))


def unit_content(con: duckdb.DuckDBPyConnection, vol: str, unit: int) -> dict:
    """初中单元内容直出DB: 知识点(语法+词汇+短语, 复用unit_knowledge_profile) + 教材正文(section_text).

    与高中 textbook_content.unit_content 的对应关系(基础库 jr_jichu 页, 2026-07-08):
    高中版多一层"辽宁高考命中次数/课标类目考查占比"的考查徽章聚合(exam_vocabulary/
    exam_grammar_stats), 初中没有同构的第一手考查统计表——unit_knowledge_profile 已经把
    对应的中考验证信息(zhongkao_verified_questions/zhongkao_exposure_count)做成"是否被
    验证过"的列表/计数, 不是占比, 直接复用不重新发明一套百分比口径(坑30: 没有第一手考查边
    的维度不能为了凑"每类都有重点标注"而编一个新指标)。
    """
    title_row = con.execute(
        "SELECT title_en FROM units WHERE version_key=? AND volume_key=? AND unit_number=?",
        [_VERSION, vol, unit],
    ).fetchone()
    title_en = title_row[0] if title_row else None
    profile = unit_knowledge_profile(con, vol, unit, title_en)
    passages = _passages_for_unit(con, vol, unit)
    return {
        "version_key": _VERSION, "volume_key": vol, "unit_number": unit, "title_en": title_en,
        "knowledge": {
            "grammar": profile["grammar"], "vocab": profile["vocab"]["words"],
            "vocab_n": profile["vocab"]["n_total"], "vocab_n_overrun": profile["vocab"]["n_overrun"],
            "vocab_pos_distribution": profile["vocab"]["pos_distribution"],
            "phrases": profile["phrases"],
        },
        "passages": passages, "passages_n": len(passages),
        "scope_note": profile["scope_note"],
        "note": "初中(沪教牛津hujiao)单元知识点(语法/词汇/短语)+正文均直出DB "
                "(grammar_occurrences/unit_vocab_intro/phrases/section_text), 不依赖PDF。"
                "词后stage=学段归属(高中必修/选修=超纲); 语法后中考验证题号=已被中考真题印证; "
                "短语无中考侧验证边(诚实分层, 见scope_note).",
    }


def _lessons_uncompressed(con: duckdb.DuckDBPyConnection,
                          units: list[tuple[str, int, str]]) -> list[dict]:
    """不压缩: 每单元独立1节(真实教学进度, 默认路径)."""
    from backend.services.course.junior_content import content_for_jr_seq

    return [
        {
            "seq": seq,
            "segment_id": f"jr-seg-{seq:02d}",
            **unit_knowledge_profile(con, vol, unit, title),
            "content": content_for_jr_seq(seq),
        }
        for seq, (vol, unit, title) in enumerate(units, 1)
    ]


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
    # compressed path has no per-lesson content mount yet (pilot = uncompressed 46)
    n_with_content = sum(1 for l in lessons if l.get("content"))
    return {
        "n_lessons": len(lessons),
        "n_units_total": len(units),
        "n_with_content": n_with_content,
        "lessons": lessons,
        "organizing_axis": "真实教材单元进度(非命题频次, 与高中course.syllabus方法论"
        "刻意不同, 见模块docstring)",
        # top-level content reserved null; bodies live on lessons[].content (pass-only)
        "content": None,
    }
