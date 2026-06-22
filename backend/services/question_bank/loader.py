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
    """Naive: by length. 阈值读 thresholds.yaml question_bank 块 (穷尽扫描: 原硬编码 + difficulty_char_threshold 孤儿key零消费)."""
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


def _autotag(con: duckdb.DuckDBPyConnection, qb_id: int, stem: str,
              year: int | None, qtype: str, cefr: set[str]) -> int:
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
    for w in sorted(toks)[:30]:  # cap to avoid bloat
        tid = f"word:{w}"
        _ensure_tag(con, tid, "word", w)
        _tag_question(con, qb_id, tid); n += 1
    # difficulty
    diff = _difficulty(stem)
    tid = f"difficulty:{diff}"
    _ensure_tag(con, tid, "difficulty", diff)
    _tag_question(con, qb_id, tid); n += 1
    return n


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
        tags += _autotag(con, qb_id, stem, yr, qtype or "未知", cefr)
        inserted += 1
    return {"inserted": inserted, "tags_attached": tags}


# 2026-06-15 Phase 7 生成层回滚: load_synthesized_samples + synth 解析 helper 已移除.
# 教材基石不完整前不合成样题 (项目 §1.1). question_bank 只 mirror 已核验真题.
