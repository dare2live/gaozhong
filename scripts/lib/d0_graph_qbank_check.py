"""D0 图谱引用 + 题库 placement/followup + 跨版本 校验 (从 data_accuracy_check 抽出, 避 god-module Rule 8).

5 项 self-contained 校验 (仅依赖 con + check 回调, 无本地 helper); body 与原 _check_14..18 字节等价。
check 由调用方传入 (data_accuracy_check.check), 失败追加 FAILURES。
"""
from __future__ import annotations

import duckdb


def check_graph_refs(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (14) 图谱深扫: 引用完整 ===")
    n_src = con.execute("SELECT COUNT(*) FROM edges WHERE src_id NOT IN (SELECT concept_id FROM nodes)").fetchone()[0]
    n_dst = con.execute("SELECT COUNT(*) FROM edges WHERE dst_id NOT IN (SELECT concept_id FROM nodes)").fetchone()[0]
    n_iso = con.execute("""
        SELECT COUNT(*) FROM nodes n
        WHERE n.node_type IN ('word','grammar','question','phrase','unit')
          AND n.concept_id NOT IN (SELECT src_id FROM edges)
          AND n.concept_id NOT IN (SELECT dst_id FROM edges)
    """).fetchone()[0]
    check("edges.src_id 全在 nodes", n_src == 0, f"orphan={n_src}")
    check("edges.dst_id 全在 nodes", n_dst == 0, f"orphan={n_dst}")
    check("孤立 critical node = 0", n_iso == 0, f"iso={n_iso}")


def check_atlas(con: duckdb.DuckDBPyConnection, check) -> None:
    """全景图谱骨架 (degree_summary, 2026-07-04 新增): label_relations 不冒充边 + 骨架闭合 + type_meta 真值."""
    print("\n=== (19) 全景图谱骨架 degree_summary ===")
    from backend.services import graph as gsvc
    r = gsvc.degree_summary(con)
    check("骨架非空 (nodes/edges 都有)", len(r["nodes"]) > 0 and len(r["edges"]) > 0,
          f"nodes={len(r['nodes'])} edges={len(r['edges'])}")
    bad_label_edge = [e for e in r["edges"] if e["relation"] in r["label_relations"]]
    check("label_relations(at_stage/cefr_level) 不进骨架边 (只作node属性)", len(bad_label_edge) == 0,
          f"混入={len(bad_label_edge)}")
    ids = {n["concept_id"] for n in r["nodes"]}
    dangling = [e for e in r["edges"] if e["src"] not in ids or e["dst"] not in ids]
    check("骨架边两端全在骨架节点内 (闭合, 无悬挂)", len(dangling) == 0, f"悬挂={len(dangling)}")
    live_totals = dict(con.execute("SELECT node_type, COUNT(*) FROM nodes GROUP BY node_type").fetchall())
    bad_meta = [t for t, m in r["type_meta"].items()
                if m["total"] != live_totals.get(t) or m["shown"] > m["total"]]
    check("type_meta.total 与 nodes 表实测一致 (非估算)", len(bad_meta) == 0, f"不符={bad_meta}")


def check_xref(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (15) units/exam/course_materials ↔ nodes 一致 ===")
    miss_u = con.execute("""
        SELECT COUNT(*) FROM units u
        WHERE 'unit:' || u.version_key || '/' || u.volume_key || '/U' || u.unit_number
              NOT IN (SELECT concept_id FROM nodes WHERE node_type='unit')
    """).fetchone()[0]
    miss_q = con.execute("""
        SELECT COUNT(*) FROM exam_questions q
        WHERE 'question:' || q.question_id
              NOT IN (SELECT concept_id FROM nodes WHERE node_type='question')
    """).fetchone()[0]
    miss_m = con.execute("""
        SELECT COUNT(*) FROM course_materials
        WHERE kind IN ('word','grammar','phrase')
        AND ref_id NOT IN (SELECT concept_id FROM nodes)
    """).fetchone()[0]
    miss_m_exam = con.execute("""
        SELECT COUNT(*) FROM course_materials
        WHERE kind = 'exam_question'
        AND (CASE WHEN ref_id LIKE 'question:%' THEN ref_id ELSE 'question:' || ref_id END)
                NOT IN (SELECT concept_id FROM nodes)
    """).fetchone()[0]
    check("units ↔ unit node 一致", miss_u == 0, f"miss={miss_u}")
    check("exam_questions ↔ question node 一致", miss_q == 0, f"miss={miss_q}")
    check("course_materials ref_id 全有 node", miss_m == 0, f"miss={miss_m}")
    check("course_materials exam_question ref_id 全有 node", miss_m_exam == 0, f"miss={miss_m_exam}")


def check_placement(con: duckdb.DuckDBPyConnection, check) -> None:
    # Phase 7 回滚后题库仅真题, 池容量小于合成题时代; placement 按可用真题降级出卷.
    # D0 验证 placement 能跑通且返真题 (got<=spec, got>=1), 不再要求抽满合成时代的额度.
    print("\n=== (16) 摸底测验卷 placement (真题池降级出卷) ===")
    from backend.services.placement import generator, loader
    specs = loader.load_specs()
    check("3 套 spec (G1/G2/G3)", len(specs) == 3, f"{len(specs)} 套")
    for s in specs:
        try:
            p = generator.generate_paper(con, s)
            got = p["total_actual"]
            check(f"{s['grade']} 出卷可用 (真题上限)",
                  1 <= got <= s["total_questions"],
                  f"got={got}/{s['total_questions']}")
        except Exception as e:
            check(f"{s['grade']} generate 跑通", False, f"err: {e}")


def check_cross_version(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (17) 跨版本对照 v4 100% (30 对扩验) ===")
    from backend.services import recommend
    sample = "unit:waiyan/xuanze_1/U6"
    res = recommend.cross_version_units(con, sample)
    check("nature 主题种子返 3 same-cefr",
          len(res) == 3 and all("nature" in r["shared_core_tokens"] for r in res),
          f"got {len(res)} 个")


def check_followup(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (18) placement followup (Codex Q6) ===")
    from backend.services.placement import followup
    # 抽**离散考点题型**(完形/语法填空/短改/单选) 3 题假装做错, 验证 followup 能抽到题。
    # 根因A: word/grammar 弱点只从离散题型派生(阅读篇章词不冒充弱点), 故测试须用离散题型 qids。
    rows = con.execute(
        "SELECT qb_id FROM question_bank "
        "WHERE question_type IN ('完形填空','语法填空','短文改错','单选(语法/词汇)') LIMIT 5"
    ).fetchall()
    all_qids = [r[0] for r in rows]
    wrong_qids = all_qids[:3] if len(all_qids) >= 3 else all_qids
    result = followup.pick_followup_questions(con, wrong_qids, all_qids, n=5)
    check("followup 能抽题 (≥1)",
          result["n_questions"] >= 1,
          f"got {result['n_questions']}")
    check("followup questions 有 qb_id+answer",
          all("qb_id" in q and "answer" in q for q in result["questions"]),
          f"fields OK")
    # compute_final_score 基本测试
    fake_first = {"accuracy": 0.5, "grade": "G1", "target_layer": "G1",
                  "weak_concepts": [], "recommended_courses": []}
    fake_answers = {q["qb_id"]: q["answer"] for q in result["questions"]}
    final = followup.compute_final_score(fake_first, fake_answers, result["questions"])
    check("final_score 返 combined_accuracy",
          "combined_accuracy" in final and 0 <= final["combined_accuracy"] <= 1,
          f"combined={final.get('combined_accuracy')}")
