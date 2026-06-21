"""D0 统一释义词典校验 (word_sense 地基; 坑17 新数据入强校验).

锁: 释义词典规模 (高中+初中三阶段都有) + 跨阶段 word_sense 候选 ≥300 (释义比对地基) +
power 跨阶段比对样本 (初中有能量义 + 高中加电力义, 防词典退化/源丢失)。
释义全来自教材生词表+中考词汇表 (课标只有词无释义), 不冒充课标释义。
"""
from __future__ import annotations

import duckdb

from scripts.lib.d0_baselines import B


def check_glossary(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (32) 统一逐阶段释义词典 (word_sense 地基) ===")
    by_stage = dict(con.execute(
        "SELECT stage, COUNT(*) FROM word_glosses GROUP BY stage").fetchall())
    check("释义词典三阶段都有 (初中/高中必修/高中选修)",
          all(by_stage.get(s, 0) > 0 for s in ("初中", "高中必修", "高中选修")), f"{by_stage}")
    n = con.execute("SELECT COUNT(*) FROM word_glosses").fetchone()[0]
    check("word_glosses 规模 ≥5000 (教材生词表+中考词汇表)", n >= B('word_glosses_min'), f"{n}")
    # 跨阶段 word_sense 候选 (初中+高中都有释义)
    cross = con.execute(
        "SELECT COUNT(*) FROM (SELECT word FROM word_glosses WHERE stage='初中' "
        "INTERSECT SELECT word FROM word_glosses WHERE stage LIKE '高中%')").fetchone()[0]
    check("跨阶段 word_sense 候选 ≥300 (初中∩高中有释义, 比对地基)", cross >= B('word_sense_cross_min'), f"{cross}")
    # power 跨阶段比对样本 (初中能量义 + 高中电力义)
    jr = con.execute("SELECT gloss FROM word_glosses WHERE word='power' AND stage='初中'").fetchall()
    hs = " ".join(r[0] for r in con.execute(
        "SELECT gloss FROM word_glosses WHERE word='power' AND stage LIKE '高中%'").fetchall())
    check("power 跨阶段比对可行 (初中有释义 + 高中含'电力'新义)",
          bool(jr) and "电力" in hs, f"初中={bool(jr)} 高中含电力={'电力' in hs}")
    # 释义非空 (来源诚实)
    empty = con.execute("SELECT COUNT(*) FROM word_glosses WHERE gloss IS NULL OR gloss=''").fetchone()[0]
    check("释义全非空 (教材/词表真相源, 不假填)", empty == 0, f"{empty} 空释义")
