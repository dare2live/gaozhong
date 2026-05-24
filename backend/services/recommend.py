"""教师端"知识图谱产品化" 查询: 按城市/单元推学习路径, 高频考词, 跨版本对照.
都是 graph 上 SQL+BFS 组合, 单一计算点 (架构 Rule 1).
"""
from __future__ import annotations

import duckdb


def city_curriculum(con: duckdb.DuckDBPyConnection, city: str) -> dict:
    """城市 → 教材版本 → 7 册 unit 列表 + 累计已学词数."""
    row = con.execute("""
        SELECT publisher_short FROM liaoning_city_textbook_choice
        WHERE city = ? AND subject = '英语'
    """, [city]).fetchone()
    if not row:
        return {"error": f"city not found: {city}"}
    pub = row[0]
    ver_map = {"外研版": "waiyan", "人教版": "renjiao"}
    ver = ver_map.get(pub, pub)
    units = con.execute("""
        SELECT volume_key, unit_number, title_en, page_start, page_end
        FROM units WHERE version_key = ?
        ORDER BY volume_key, unit_number
    """, [ver]).fetchall()
    # 累计已学词 (per unit, distinct word)
    word_acc: dict[tuple, int] = {}
    for vol, un, *_ in units:
        n = con.execute("""
            SELECT COUNT(DISTINCT word) FROM unit_vocab_intro
            WHERE version_key=? AND volume_key=? AND unit_number<=?
        """, [ver, vol, un]).fetchone()[0]
        word_acc[(vol, un)] = n
    return {
        "city": city, "publisher": pub, "version_key": ver,
        "units": [{
            "volume_key": v, "unit_number": un, "title": t,
            "page_start": ps, "page_end": pe,
            "cumulative_words_learned": word_acc.get((v, un), 0),
        } for v, un, t, ps, pe in units],
    }


def top_exam_words(con: duckdb.DuckDBPyConnection, limit: int = 30) -> list[dict]:
    """高频考词 — 按 tests_word edge 度数排序."""
    rows = con.execute("""
        SELECT n.label AS word,
               COUNT(*) AS exam_freq,
               MAX(n.attrs_json) AS attrs
        FROM edges e
        INNER JOIN nodes n ON n.concept_id = e.dst_id
        WHERE e.relation = 'tests_word' AND n.node_type = 'word'
        GROUP BY n.label
        ORDER BY exam_freq DESC LIMIT ?
    """, [limit]).fetchall()
    return [{"word": r[0], "exam_freq": r[1], "attrs": r[2]} for r in rows]


_TITLE_STOPWORDS = {
    # 编号/连接
    "unit", "a", "an", "the", "of", "in", "on", "at", "to", "for", "with",
    "and", "or", "but", "by", "from", "as", "is", "are", "be",
    # 排序虚词 (避 "first/second" 误归类为主题)
    "first", "second", "third", "one", "two", "three", "new", "old",
    # 常空词
    "welcome", "introduction", "review", "project",
    # 标题被节选到内容时混入的高频虚词 (100% 准目标排雷)
    "all", "any", "this", "that", "these", "those", "some", "every",
    "good", "bad", "very", "more", "most", "less", "least",
    "what", "who", "how", "why", "when", "where",
    "make", "made", "get", "got", "have", "has", "had", "will", "would",
    "can", "could", "should", "must", "may", "might",
    "match", "complete", "fill", "answer", "discuss", "write",
    "lifelong", "lifeline", "lifelike",   # life 词族但语义≠生活
    "people", "person", "things", "thing", "way", "ways",
    # 教学高频惯用 (非主题)
    "lessons", "lesson", "practice", "exercise", "homework",
    # 介词/副词扩展 (P2.1 30 对验证暴露 — around/using/across 等单独不构成主题)
    "around", "across", "into", "onto", "over", "under", "above", "below",
    "through", "between", "beyond", "along", "among", "behind", "before",
    "after", "during", "since", "until", "without", "within",
    "using", "use", "used", "uses", "applying", "applied",
    "doing", "done", "saying", "said", "going", "gone", "seeing", "seen",
    "comes", "coming", "came", "becomes", "becoming", "became",
    # 单独动词太宽泛
    "learn", "learning", "learner",
    "look", "looking", "looked", "looks",
    "think", "thinking", "thought",
}

# 名词词族归一 (手工小词典 — 覆盖教材常见主题词的形态变化)
_LEMMA_MAP = {
    "natural": "nature", "nurturing": "nature",
    "exploring": "exploration", "explore": "exploration", "exploration": "exploration",
    "arts": "art", "artistic": "art", "amazing": "art",  # "amazing art" → art
    "eating": "food", "eat": "food", "foods": "food",
    "cultural": "culture", "cultures": "culture",
    "scientific": "science", "sciences": "science",
    "historical": "history", "histories": "history",
    "natural sciences": "science",
}


def cross_version_units(con: duckdb.DuckDBPyConnection,
                          unit_id: str, limit: int = 3) -> list[dict]:
    """跨版本同主题对照 — 100% 准目标 (2026-05-24 用户硬约束).

    算法 (宁缺毋滥):
      1. 候选必须共享 ≥1 个 level1 主题 (theme_of_unit)
      2. 标题核心名词 (去停用词 + lemma 归一) 必须 ≥1 共享
      3. 按 jaccard(标题核心词) DESC 排序
      4. 限 top N (默认 3); 0 候选 → 返空, 不假推
    """
    src_title = _get_label(con, unit_id)
    src_tokens = _title_core_tokens(src_title)
    src_themes = _unit_themes(con, unit_id)
    if not src_tokens or not src_themes:
        return []
    candidates = _candidate_unit_ids(con, unit_id, src_themes)
    out: list[dict] = []
    for cid in candidates:
        c_title = _get_label(con, cid)
        c_tokens = _title_core_tokens(c_title)
        common = src_tokens & c_tokens
        if not common:
            continue   # 100% 准: 标题核心词无交集 = 不推
        union = src_tokens | c_tokens
        jacc = round(len(common) / len(union), 3) if union else 0
        out.append({
            "unit_id": cid, "label": c_title,
            "shared_core_tokens": sorted(common),
            "jaccard": jacc,
            "shared_themes": src_themes,
        })
    out.sort(key=lambda x: -x["jaccard"])
    return out[:limit]


def _get_label(con: duckdb.DuckDBPyConnection, concept_id: str) -> str:
    r = con.execute("SELECT label FROM nodes WHERE concept_id = ?", [concept_id]).fetchone()
    return r[0] if r else concept_id


def _unit_themes(con: duckdb.DuckDBPyConnection, unit_id: str) -> list[str]:
    return [r[0] for r in con.execute(
        "SELECT dst_id FROM edges WHERE src_id = ? AND relation = 'theme_of_unit'",
        [unit_id],
    ).fetchall()]


def _candidate_unit_ids(con: duckdb.DuckDBPyConnection,
                          unit_id: str, themes: list[str]) -> list[str]:
    placeholders = ",".join(["?"] * len(themes))
    rows = con.execute(
        f"SELECT DISTINCT src_id FROM edges "
        f"WHERE relation='theme_of_unit' AND dst_id IN ({placeholders}) "
        f"AND src_id <> ?",
        themes + [unit_id],
    ).fetchall()
    return [r[0] for r in rows]


_TITLE_MAX_TOKENS = 6   # 标题被节选到内容时, 只取前 N token 作主题判断


def _title_core_tokens(title: str) -> set[str]:
    """从 unit 标题抽核心主题 token (去 UNIT 号 → 取前 N token → 去停用词 → lemma 归一).

    例:
      "UNIT 1 A new start"        → {start}
      "UNIT 6 Nurturing nature"   → {nature}      (nurturing → nature)
      "UNIT 4 Amazing art"        → {art}         (amazing → art)
      "UNIT 1 Food for thought"   → {food, thought}
      "UNIT 5 WORKING THE LAND My lifelong pursuit is to keep all..." → {working, land}
        (后面内容截掉, 'all' 'lifelong' 入停用词)
    """
    import re
    if not title:
        return set()
    cleaned = re.sub(r"\bUNIT\s*\d+\b", " ", title, flags=re.IGNORECASE)
    cleaned = re.sub(r"[^A-Za-z一-鿿 ]", " ", cleaned)
    raw_tokens = [t.lower() for t in cleaned.split() if len(t) >= 3]
    # 限前 N token (避免标题被内容污染)
    raw_tokens = raw_tokens[:_TITLE_MAX_TOKENS]
    tokens = set(raw_tokens) - _TITLE_STOPWORDS
    return {_LEMMA_MAP.get(t, t) for t in tokens}


def unit_exam_alignment(con: duckdb.DuckDBPyConnection,
                          unit_id: str) -> dict:
    """给一个 unit, 返回该 unit 引入词 ∩ 历年真题考过的词的统计."""
    # words introduced in this unit
    intro = {r[0].split(":", 1)[1] for r in con.execute("""
        SELECT dst_id FROM edges WHERE src_id=? AND relation='introduces_word'
    """, [unit_id]).fetchall()}
    if not intro:
        return {"unit_id": unit_id, "intro_total": 0,
                "exam_overlap": 0, "examples": []}
    # of these, how many tested in real exam? — via tests_word edge in reverse
    overlap = []
    for w in list(intro):
        cnt = con.execute("""
            SELECT COUNT(*) FROM edges WHERE relation='tests_word'
              AND dst_id = ?
        """, [f"word:{w}"]).fetchone()[0]
        if cnt > 0:
            overlap.append((w, cnt))
    overlap.sort(key=lambda x: -x[1])
    return {
        "unit_id": unit_id,
        "intro_total": len(intro),
        "exam_overlap": len(overlap),
        "examples": [{"word": w, "exam_freq": c} for w, c in overlap[:20]],
    }
