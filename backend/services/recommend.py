"""教师端"知识图谱产品化" 查询: 按城市/单元推学习路径, 高频考词, 跨版本对照.
都是 graph 上 SQL+BFS 组合, 单一计算点 (架构 Rule 1).
"""
from __future__ import annotations

import duckdb

from backend.services import canonical, vocab


def cities(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """辽宁地市 → 教材版本短名 (city 选择器数据源; 前端不 hardcode 城市名/版本).

    走 canonical.city_version_rows 单一查询点 (同表多处 SELECT 收口, 防 schema 漂移)。
    """
    return [{"city": c, "publisher": p} for c, p, _ in canonical.city_version_rows(con)]


def city_curriculum(con: duckdb.DuckDBPyConnection, city: str) -> dict:
    """城市 → 教材版本 → 7 册 unit 列表 + 累计已学词数 (city→version 走 canonical 单点)."""
    pub = next((p for c, p, _ in canonical.city_version_rows(con) if c == city), None)
    if pub is None:
        return {"error": f"city not found: {city}"}
    ver_map = {v: k for k, v in canonical.VERSION_KEY_TO_SHORT.items()}   # 短名→version_key (canonical 单点反查)
    ver = ver_map.get(pub, pub)
    units = con.execute("""
        SELECT volume_key, unit_number, title_en, page_start, page_end
        FROM units WHERE version_key = ?
        ORDER BY volume_key, unit_number
    """, [ver]).fetchall()
    # 累计已学词 (per unit, distinct word) — 后端审计#1 修: 原 volume_key=? 把累计锁单册内每跨册重置
    # (bixiu_2 u1 不含 bixiu_1, 末单元 198 vs 真实整版本 ~2025, 低估~10x; 是 D0§1.2 "词量≤已学单元"
    # 越纲判断输入, 低估会误判可学词越纲)。改按学习序列 running distinct: 前序册全部 + 本册≤本单元。
    # volume_key 字典序恰=教学序 (bixiu_1<bixiu_2<bixiu_3<xuanze_1..4), DISTINCT 跨册去重(学过一次算一次)。
    word_acc: dict[tuple, int] = {}
    for vol, un, *_ in units:
        n = con.execute("""
            SELECT COUNT(DISTINCT word) FROM unit_vocab_intro
            WHERE version_key=? AND (volume_key < ? OR (volume_key = ? AND unit_number <= ?))
        """, [ver, vol, vol, un]).fetchone()[0]
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
    """高频考词 — 辽宁卷**离散考点题型**考查度数排序 (根因A+§7: 原无 province/题型过滤 → top10 全是
    make/one/time 阅读篇章功能词; 收口到辽宁离散题型, 与 vocab._TESTED_QTYPES 同口径)."""
    rows = con.execute("""
        SELECT n.label AS word,
               COUNT(*) AS exam_freq,
               MAX(n.attrs_json) AS attrs
        FROM edges e
        INNER JOIN nodes n ON n.concept_id = e.dst_id
        JOIN exam_questions q ON q.question_id = SUBSTR(e.src_id, 10)
        WHERE e.relation = 'tests_word' AND n.node_type = 'word'
          AND q.province LIKE '辽宁%'
          AND q.question_type IN ('完形填空','语法填空','短文改错','单选(语法/词汇)')
        GROUP BY n.label
        ORDER BY exam_freq DESC LIMIT ?
    """, [limit]).fetchall()
    return [{"word": r[0], "exam_freq": r[1], "attrs": r[2]} for r in rows]


def courses_for_student_weakness(con: duckdb.DuckDBPyConnection, student_id: str) -> list[dict]:
    """学生弱点考点 → 推荐教该考点的课节 (单一计算点; 图谱桥 Rule3, 路由不自写 JOIN)。

    弱点是**考点级** exam_point:theme_l2:X, 课材是**单元级** → 必走主题桥:
      student_weakness → theme_aligns → theme → theme_of_unit → 教材单元 → course_materials → course。
    旧 route 的 `cm.ref_id=sw.concept_id` 直配 by-construction 永远0命中(考点前缀≠词/单元前缀)。
    仅 theme 维度弱点可经此桥落到单元; genre/设问类维度无单元映射 → 诚实返空(非假装推荐)。
    命中数还取决于 course_materials 对该主题单元的覆盖(现 demo 12 单元, 稀疏属正常诚实降级)。
    """
    rows = con.execute(
        "SELECT DISTINCT c.course_id, c.layer, c.title, sw.concept_id, sw.weakness_score "
        "FROM student_weakness sw "
        "JOIN edges ta ON ta.src_id = sw.concept_id AND ta.relation = 'theme_aligns' "
        "JOIN edges tu ON tu.dst_id = ta.dst_id AND tu.relation = 'theme_of_unit' "
        "JOIN course_materials cm ON cm.ref_id = tu.src_id "
        "JOIN courses c ON c.course_id = cm.course_id "
        "WHERE sw.student_id = ? "
        "ORDER BY sw.weakness_score DESC LIMIT 20",
        [student_id]).fetchall()
    return [{"course_id": r[0], "layer": r[1], "title": r[2],
             "weak_concept": r[3], "score": r[4]} for r in rows]


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
    """给一个 unit, 返回该 unit 引入词 ∩ 历年真题考过的词的统计.

    单一计算点 (Rule 1): 委托 services.vocab.unit_word_exam_alignment, 与 lesson_plan /
    备课整合 同源, 不在此重写 JOIN。
    """
    return vocab.unit_word_exam_alignment(con, unit_id)
