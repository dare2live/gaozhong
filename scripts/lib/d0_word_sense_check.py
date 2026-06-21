"""D0 word_sense 本体校验 (master A1; 坑16 防过度检测 / 坑17 新数据入门).

锁: word_sense 节点=2×确认多义词 + has_sense/expands_sense 边数一致 + 无孤儿 +
expands_sense 两端是 word_sense 且初中→高中 + provenance=对抗验证 + ceiling 跨阶段新义(上限)样本。
"""
from __future__ import annotations

import duckdb

_MULTI = ("SELECT COUNT(*) FROM (SELECT DISTINCT json_extract_string(attrs_json,'$.word') "
          "FROM nodes WHERE node_type='word_sense')")


def check_word_sense(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (34) word_sense 本体 (master A1; 跨阶段多义, 对抗验证) ===")
    n_node = con.execute("SELECT COUNT(*) FROM nodes WHERE node_type='word_sense'").fetchone()[0]
    n_word = con.execute(_MULTI).fetchone()[0]
    check("word_sense 节点 = 2×多义词 (每词初中/高中各一义项节点)", n_node == 2 * n_word, f"{n_node} 节点/{n_word} 词")
    n_has = con.execute("SELECT COUNT(*) FROM edges WHERE relation='has_sense'").fetchone()[0]
    check("has_sense 边 == word_sense 节点数 (每义项节点一条 word→sense)", n_has == n_node, f"{n_has}")
    n_exp = con.execute("SELECT COUNT(*) FROM edges WHERE relation='expands_sense'").fetchone()[0]
    check("expands_sense 边 == 多义词数 (每词一条初中→高中)", n_exp == n_word, f"{n_exp}")
    # 无孤儿 word_sense (每节点必有 has_sense 连)
    orphan = con.execute(
        "SELECT COUNT(*) FROM nodes n WHERE n.node_type='word_sense' "
        "AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.dst_id=n.concept_id AND e.relation='has_sense')"
    ).fetchone()[0]
    check("word_sense 无孤儿 (每义项节点有 has_sense)", orphan == 0, f"{orphan}")
    # expands_sense 两端 word_sense + 初中→高中 (语义方向)
    bad = con.execute(
        "SELECT COUNT(*) FROM edges WHERE relation='expands_sense' AND "
        "(src_id NOT LIKE 'word_sense:%:初中' OR dst_id NOT LIKE 'word_sense:%:高中')").fetchone()[0]
    check("expands_sense 初中→高中 (低阶→高阶, master A1)", bad == 0, f"{bad} 方向错")
    # provenance = 对抗验证 (坑16 不裸信单判断)
    bad_prov = con.execute(
        "SELECT COUNT(*) FROM edges WHERE relation='expands_sense' "
        "AND json_extract_string(evidence_json,'$.provenance')<>'dual_model_adversarial'").fetchone()[0]
    check("expands_sense provenance=dual_model_adversarial (坑16 对抗验证防过度检测)", bad_prov == 0, f"{bad_prov}")
    # ceiling 跨阶段新义样本 (天花板→上限; 防义项检测退化)
    ce = con.execute("SELECT attrs_json FROM nodes WHERE concept_id='word_sense:ceiling:高中'").fetchone()
    check("ceiling 高中新义含'上限' (跨阶段语义深化样本)", bool(ce) and "上限" in ce[0], f"{bool(ce)}")
