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

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'\-]{1,}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _difficulty(text: str) -> str:
    """Naive: by length."""
    n = len(text or "")
    if n < 100: return "easy"
    if n < 400: return "mid"
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
        "INSERT INTO question_bank VALUES (nextval('qb_id_seq'), ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?) "
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
    # word tags (cefr ∩ stem tokens)
    toks = {t.lower() for t in _TOKEN_RE.findall(stem or "")} & cefr
    for w in list(toks)[:30]:  # cap to avoid bloat
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
    rows = con.execute(
        "SELECT question_id, year, question_type, raw_question, answer, analysis "
        "FROM exam_questions"
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


def load_synthesized_samples(con: duckdb.DuckDBPyConnection,
                              samples_per_type: int = 20) -> dict:
    """跑各种 generator N 次, 把生成的题入库."""
    from backend.services.exercise import cloze, grammar_fill, poc
    import random
    cefr = {r[0] for r in con.execute("SELECT word FROM cefr_vocab").fetchall()}
    units = [r[0] for r in con.execute(
        "SELECT DISTINCT 'unit:'||version_key||'/'||volume_key||'/U'||unit_number "
        "FROM units"
    ).fetchall()]
    n_total = 0
    rng = random.Random(42)
    # L1 选义题 — 每 unit 5 题
    for uid in units[:30]:  # cap
        try:
            r = poc.generate_l1_quiz(con, uid, n=5, seed=rng.randint(0, 99999))
        except Exception:
            continue
        for q in r.get("questions", []):
            qb_id = _insert_question(
                con, "rule_synth", f"l1/{uid}/{q['seq']}",
                "选义单选", q["stem"], json.dumps(q["options"], ensure_ascii=False),
                q["answer"], None, "easy")
            _autotag(con, qb_id, q["stem"], None, "选义单选", cefr)
            # tag with origin unit
            _ensure_tag(con, uid, "unit", uid.split(":", 1)[1])
            _tag_question(con, qb_id, uid)
            n_total += 1
    # cloze + grammar_fill — 各 12 篇
    for fn, qtype in [(cloze.generate_cloze, "完形填空_synth"),
                       (grammar_fill.generate_grammar_fill, "语法填空_synth")]:
        for _ in range(samples_per_type):
            try:
                r = fn(con, unit_id=None, n_blanks=8, seed=rng.randint(0, 99999))
            except Exception:
                continue
            if r.get("error"):
                continue
            stem = r.get("passage_with_blanks", "")[:1500]
            qb_id = _insert_question(
                con, "rule_synth", f"{qtype}/{rng.randint(1, 99999)}",
                qtype, stem,
                json.dumps(r.get("questions", []), ensure_ascii=False),
                None, None, "mid")
            _autotag(con, qb_id, stem, None, qtype, cefr)
            n_total += 1
    return {"synth_inserted": n_total}
