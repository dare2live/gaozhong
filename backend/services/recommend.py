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


def cross_version_units(con: duckdb.DuckDBPyConnection,
                          unit_id: str) -> list[dict]:
    """跨版本同主题对照: 给一个 unit, 返回 theme 相同的另一版本 unit."""
    # find this unit's themes
    rows_t = con.execute("""
        SELECT dst_id FROM edges
        WHERE src_id = ? AND relation = 'theme_of_unit'
    """, [unit_id]).fetchall()
    themes = [r[0] for r in rows_t]
    if not themes:
        return []
    other_units = con.execute("""
        SELECT DISTINCT e.src_id FROM edges e
        WHERE e.relation = 'theme_of_unit'
          AND e.dst_id IN (""" + ",".join(["?"] * len(themes)) + """)
          AND e.src_id != ?
    """, themes + [unit_id]).fetchall()
    out = []
    for (cid,) in other_units:
        n = con.execute(
            "SELECT label FROM nodes WHERE concept_id=?", [cid]
        ).fetchone()
        out.append({"unit_id": cid, "label": n[0] if n else cid,
                     "shared_themes": themes})
    return out


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
