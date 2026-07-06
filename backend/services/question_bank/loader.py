"""把现有真题 + 4 类合成题 → question_bank, 自动打标 (考点/教材/年份/题型).

策略:
  - 真题 (exam_questions 334) → origin='real', 标 year + question_type + tests_word/grammar tag
  - 4 合成题型按需调用对应 generator, 把每次生成结果序列化入库 (origin='rule_synth')
  - 自动 tag 从 graph edges + nodes attrs 拉

标签规则:
  - question_type:<type>  (eg 'question_type:阅读理解')
  - year:<YYYY>           (real 真题)
  - word:<lower>          (题面 token ∩ cefr_vocab)
  - grammar:<gid>         (题面/解析含中文术语)
  - difficulty:<level>    (启发式: 题面长度 + 词频)
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

import duckdb

from backend.services.thresholds import get_threshold   # 难度阈值单点 (中立 leaf, 避 question_bank→course 倒置)

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'\-]{1,}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _difficulty(text: str) -> str:
    """**题面篇幅档**(len(题面)), 非教研验证难度 (后端审计#7: 无真难度源, 此为字数代理)。
    字段名保留 difficulty(schema/compose/placement 内部码), 但教师面据实标"篇幅(长/中/短)"不冒充难度;
    且跨 source 粒度混淆(eol子题短/篇章源长), 仅作篇幅档参考。阈值读 thresholds.yaml question_bank 块。"""
    n = len(text or "")
    if n < get_threshold("question_bank.difficulty_easy_threshold", 100): return "easy"
    if n < get_threshold("question_bank.difficulty_char_threshold", 400): return "mid"
    return "hard"


def _ensure_tag(con: duckdb.DuckDBPyConnection, tag_id: str, kind: str, label: str) -> None:
    con.execute("INSERT OR REPLACE INTO tag_dictionary VALUES (?, ?, ?)", [tag_id, kind, label])


def _tag_question(con: duckdb.DuckDBPyConnection, qb_id: int, tag_id: str, weight: float = 1.0):
    con.execute("INSERT OR REPLACE INTO question_tags VALUES (?, ?, ?)",
                [qb_id, tag_id, weight])


def _insert_question(con: duckdb.DuckDBPyConnection, origin: str, origin_ref: str | None,
                      qtype: str, stem: str, options_json: str | None,
                      answer: str | None, analysis: str | None,
                      difficulty: str = "mid") -> int:
    row = con.execute(
        "INSERT INTO question_bank "
        "(qb_id, origin, origin_ref, question_type, stem, options_json, answer, analysis, "
        " difficulty, reviewed_by, created_at) "
        "VALUES (nextval('qb_id_seq'), ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?) "
        "RETURNING qb_id",
        [origin, origin_ref, qtype, stem, options_json, answer, analysis, difficulty, _now()],
    ).fetchone()
    return row[0]


def _exam_point_tags(con: duckdb.DuckDBPyConnection, origin_ref: str | None) -> list[str]:
    """真题反查 tests_exam_point 边命中的考点 (dst_id 本就是 'exam_point:<dim>:<label>' 格式tag_id).

    坑(2026-07-06 数据关联设计审查): 组卷"必含标签"输入框一直只支持 word:/unit:/question_type:/
    year:/difficulty: 五类, tag_dictionary 的 tag_kind 注释里列了 exam_point 却从未生成过——
    40节课程的 covers_exam_points 字段(如 exam_point:theme_l2:XX)在组卷标签体系里查不到, 无法
    实现"课程→组卷带着考点焦点跳转+预筛选"这个闭环, 这里补上。
    """
    if not origin_ref:
        return []
    return [r[0] for r in con.execute(
        "SELECT DISTINCT dst_id FROM edges WHERE src_id = ? AND relation = 'tests_exam_point'",
        [f"question:{origin_ref}"],
    ).fetchall()]


def _unit_tags(con: duckdb.DuckDBPyConnection, words: list[str]) -> list[str]:
    """该题命中的单词反查 introduces_word 边所属单元 (tag_id='unit:<version>/<volume>/U<n>').

    坑(同上审查): 组卷"必含标签"占位符提示 unit:waiyan/bixiu_1/U1 格式, 但 tag_dictionary 从未
    实际生成过 unit 类标签(schema注释允许≠数据存在), 是从未实现的死功能。逻辑: 该题命中的word tag
    (已限定为content_tokens∩cefr, 非停用词)若被某单元的 unit_vocab_intro 首次引入, 该题就与
    那个单元相关(供老师按"我要教这单元, 找相关真题练习"筛选), 不是"专属该单元"的排他声明。
    """
    if not words:
        return []
    ph = ",".join(["?"] * len(words))
    return [r[0] for r in con.execute(
        f"SELECT DISTINCT src_id FROM edges WHERE relation = 'introduces_word' AND dst_id IN ({ph})",
        [f"word:{w}" for w in words],
    ).fetchall()]


def _autotag(con: duckdb.DuckDBPyConnection, qb_id: int, stem: str,
              year: int | None, qtype: str, cefr: set[str], origin_ref: str | None = None) -> int:
    """Auto-tag a question; return tag count attached."""
    n = 0
    # type
    tid = f"question_type:{qtype}"
    _ensure_tag(con, tid, "question_type", qtype)
    _tag_question(con, qb_id, tid); n += 1
    # year
    if year:
        tid = f"year:{year}"
        _ensure_tag(con, tid, "year", str(year))
        _tag_question(con, qb_id, tid); n += 1
    # word tags (实词考点 = cefr ∩ stem tokens − 停用词; 2026-06-15 去停用词污染)
    from backend.services.stopwords import content_tokens
    toks = content_tokens({t.lower() for t in _TOKEN_RE.findall(stem or "")}, cefr)
    word_tags = sorted(toks)[:30]  # cap to avoid bloat
    for w in word_tags:
        tid = f"word:{w}"
        _ensure_tag(con, tid, "word", w)
        _tag_question(con, qb_id, tid); n += 1
    # exam_point tags (反查真题的 tests_exam_point 边; label = dst_id 冒号后半段, 已是人话)
    for tid in _exam_point_tags(con, origin_ref):
        _ensure_tag(con, tid, "exam_point", tid.split(":", 2)[-1])
        _tag_question(con, qb_id, tid); n += 1
    # unit tags (反查该题命中word tag所属单元, 与已生成的word_tags同源不重新算)
    for tid in _unit_tags(con, word_tags):
        _ensure_tag(con, tid, "unit", tid.split(":", 1)[-1])
        _tag_question(con, qb_id, tid); n += 1
    # difficulty
    diff = _difficulty(stem)
    tid = f"difficulty:{diff}"
    _ensure_tag(con, tid, "difficulty", diff)
    _tag_question(con, qb_id, tid); n += 1
    return n


def backfill_exam_point_tags(con: duckdb.DuckDBPyConnection) -> dict:
    """Layer 4i(考点 tests_exam_point 边就绪)后补打 exam_point 标签.

    坑(2026-07-06 全量重建实测发现): question_bank 装载在 Layer 4, 早于 tests_exam_point 边
    生成的 Layer 4i(load_exam_points/load_cognitive_skill) — _autotag() 里的 exam_point 反查
    在首次全量重建时因边还不存在而 0 命中(实测: 单独重跑load_real_questions时因边已存在于旧库
    而误判"成功", 全新重建才暴露顺序依赖)。此函数复用同一份 _exam_point_tags() 反查逻辑,
    在 Layer 4i 之后单独回填, 与 Layer 4j(weakness 重算同理由推迟到 4i 后)是同一套依赖顺序模式。
    """
    rows = con.execute(
        "SELECT qb_id, origin_ref FROM question_bank WHERE origin='real' AND origin_ref IS NOT NULL"
    ).fetchall()
    n = 0
    for qb_id, origin_ref in rows:
        for tid in _exam_point_tags(con, origin_ref):
            _ensure_tag(con, tid, "exam_point", tid.split(":", 2)[-1])
            _tag_question(con, qb_id, tid); n += 1
    return {"questions_scanned": len(rows), "exam_point_tags_attached": n}


def load_real_questions(con: duckdb.DuckDBPyConnection) -> dict:
    """Mirror exam_questions → question_bank, autotag."""
    con.execute("DELETE FROM question_tags")
    con.execute("DELETE FROM question_bank")
    cefr = {r[0] for r in con.execute("SELECT word FROM cefr_vocab").fetchall()}
    # 精确匹配「以辽宁开头」: 排除标签里含"非辽宁"的外省卷 (province LIKE '%辽宁%' 会误收)
    rows = con.execute(
        "SELECT question_id, year, question_type, raw_question, answer, analysis "
        "FROM exam_questions WHERE province LIKE '辽宁%'"
    ).fetchall()
    inserted = 0
    tags = 0
    for qid, yr, qtype, stem, ans, anl in rows:
        if not stem:
            continue
        diff = _difficulty(stem)
        qb_id = _insert_question(con, "real", qid, qtype or "未知",
                                   stem, None, ans, anl, diff)
        tags += _autotag(con, qb_id, stem, yr, qtype or "未知", cefr, origin_ref=qid)
        inserted += 1
    return {"inserted": inserted, "tags_attached": tags}


# 2026-06-15 Phase 7 生成层回滚: load_synthesized_samples + synth 解析 helper 已移除.
# 教材基石不完整前不合成样题 (项目 §1.1). question_bank 只 mirror 已核验真题.
