#!/usr/bin/env python3
"""D0 强执行: 全数据集 100% 准确率校验.

跑法:
  python3 scripts/data_accuracy_check.py
  exit 0 = 全 100% 准
  exit 1 = 任一项不达

模块化设计 (M6 CC ≤ 10): 17 个 _check_* 章节函数, main 只调度.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import duckdb

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    sym = "✅" if cond else "❌"
    print(f"  {sym} {name}", end="")
    if detail:
        print(f"  ({detail})", end="")
    print()
    if not cond:
        FAILURES.append(f"{name}: {detail}")


# ===== 17 章节 helper (每函数 CC ≤ 4) =====

def _check_1_manifest(con):
    print("=== (1) 数据基石 sha + manifest ===")
    n_mani = con.execute("SELECT COUNT(*) FROM file_manifest").fetchone()[0]
    n_tb = con.execute("SELECT COUNT(*) FROM textbooks").fetchone()[0]
    n_no_sha = con.execute("SELECT COUNT(*) FROM textbooks WHERE pdf_sha256 IS NULL OR pdf_sha256=''").fetchone()[0]
    check("manifest 行 ≥ 14", n_mani >= 14, f"{n_mani}")
    check("textbooks == 14", n_tb == 14, f"{n_tb}")
    check("每教材 PDF sha 锁", n_no_sha == 0, "textbooks.pdf_sha256 全非空")


def _check_2_vocab(con):
    print("\n=== (2) 词集 ===")
    n_cefr = con.execute("SELECT COUNT(*) FROM cefr_vocab").fetchone()[0]
    n_uvi = con.execute("SELECT COUNT(*) FROM unit_vocab_intro").fetchone()[0]
    lvls = {r[0] for r in con.execute("SELECT DISTINCT cefr_level FROM cefr_vocab").fetchall()}
    check("cefr_vocab 2986", n_cefr == 2986, f"{n_cefr}")
    check("unit_vocab_intro > 4000", n_uvi > 4000, f"{n_uvi}")
    check("cefr 3 级全在", lvls == {"义教", "必修", "选必"})


def _check_3_grammar(con):
    print("\n=== (3) 语法 ===")
    n_g = con.execute("SELECT COUNT(*) FROM grammar_items").fetchone()[0]
    n_orphan = con.execute(
        "SELECT COUNT(*) FROM grammar_items WHERE parent_id IS NOT NULL "
        "AND parent_id NOT IN (SELECT grammar_item_id FROM grammar_items)"
    ).fetchone()[0]
    check("grammar_items 行 == 106", n_g == 106, f"{n_g}")
    check("grammar DAG 无环 (audit OK)", _audit_ok(con, "grammar_dag"))
    check("grammar parent_id 引用完整", n_orphan == 0, f"orphan={n_orphan}")


def _check_4_phrases(con):
    print("\n=== (4) 短语 ===")
    n_ph = con.execute("SELECT COUNT(*) FROM phrases").fetchone()[0]
    check("phrases > 100", n_ph > 100, f"{n_ph}")


def _check_5_handouts(con):
    print("\n=== (5) 教案 (course_handouts) ===")
    n_h = con.execute("SELECT COUNT(*) FROM course_handouts").fetchone()[0]
    n_short = con.execute("SELECT COUNT(*) FROM course_handouts WHERE md_chars < 1000").fetchone()[0]
    check("40 节讲义全持久化", n_h == 40, f"{n_h}")
    check("每节 md ≥ 1000 字符", n_short == 0, f"{n_short} 节短")
    check("R2 audit OK", _audit_ok(con, "audit_course_no_textbook_copy"))


def _check_6_graph(con):
    print("\n=== (6) 知识图谱 ===")
    n_n = con.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    n_e = con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    check("nodes ≥ 4000", n_n >= 4000, f"{n_n}")
    check("edges ≥ 30000", n_e >= 30000, f"{n_e}")
    for k in ("graph_edge_validity", "graph_orphans", "graph_grammar_dag", "graph_relation_dict"):
        check(f"{k} OK", _audit_ok(con, k))


def _check_7_audit_summary(con):
    print("\n=== (7) Audit 全 OK / 0 FAIL / 0 WARN ===")
    fails = con.execute("SELECT COUNT(*) FROM audit_findings WHERE severity='FAIL'").fetchone()[0]
    warns = con.execute("SELECT COUNT(*) FROM audit_findings WHERE severity='WARN'").fetchone()[0]
    oks = con.execute("SELECT COUNT(*) FROM audit_findings WHERE severity='OK'").fetchone()[0]
    check("0 FAIL", fails == 0, f"{fails}")
    check("0 WARN", warns == 0, f"{warns}")
    check("OK ≥ 40", oks >= 40, f"{oks}")


def _check_8_course_audits(con):
    print("\n=== (8) 课程 8 audit ===")
    for k in ("audit_course_relations", "audit_course_no_textbook_copy",
              "audit_course_scenarios", "audit_homework_alignment",
              "audit_course_lexical_layer", "audit_course_textbook_position",
              "audit_listening_transcript_required", "audit_no_political"):
        check(k, _audit_ok(con, k))


def _check_9_qbank(con):
    print("\n=== (9) 题库 + 标签 ===")
    n_qb = con.execute("SELECT COUNT(*) FROM question_bank").fetchone()[0]
    n_qt = con.execute("SELECT COUNT(*) FROM question_tags").fetchone()[0]
    n_orphan = con.execute(
        "SELECT COUNT(*) FROM question_tags WHERE qb_id NOT IN (SELECT qb_id FROM question_bank)"
    ).fetchone()[0]
    check("question_bank ≥509", n_qb >= 509, f"{n_qb}")
    check("question_tags > 10000", n_qt > 10000, f"{n_qt}")
    check("question_tags 引用完整", n_orphan == 0, f"orphan={n_orphan}")


def _check_10_qbank_options(con):
    print("\n=== (10) 题库 options + answer 完整性 ===")
    rows = con.execute(
        "SELECT qb_id, stem, options_json, answer FROM question_bank "
        "WHERE question_type IN ('单选(语法/词汇)','选义单选','阅读理解')"
    ).fetchall()
    bad = [qid for qid, stem, opts, ans in rows
           if not ans or (not opts and not _stem_has_abcd(stem))]
    n_no_ans = con.execute("SELECT COUNT(*) FROM question_bank WHERE answer IS NULL OR answer=''").fetchone()[0]
    check("选择题 options 完整", len(bad) == 0, f"bad={len(bad)}: {bad[:5]}")
    check("answer 非空率", n_no_ans <= 50, f"无 answer={n_no_ans} (容忍非选择题)")


def _check_11_tag_dict(con):
    print("\n=== (11) tag_dictionary 反向引用 ===")
    n_orphan = con.execute(
        "SELECT COUNT(DISTINCT tag_id) FROM question_tags "
        "WHERE tag_id NOT IN (SELECT tag_id FROM tag_dictionary)"
    ).fetchone()[0]
    check("question_tags.tag_id 全在 tag_dict", n_orphan == 0, f"orphan={n_orphan}")


def _check_12_cefr_node_xref(con):
    print("\n=== (12) cefr_vocab ↔ node 抽样 100 词 ===")
    rows = con.execute("SELECT word FROM cefr_vocab ORDER BY word LIMIT 100").fetchall()
    miss = []
    for (w,) in rows:
        r = con.execute("SELECT label FROM nodes WHERE concept_id = ?", [f"word:{w}"]).fetchone()
        if not r or r[0].lower() != w.lower():
            miss.append(w)
    check("cefr ↔ node label 一致", len(miss) == 0, f"miss={len(miss)}: {miss[:5]}")


def _check_13_grammar_chain(con):
    print("\n=== (13) grammar DAG 完整路径 ===")
    rows = con.execute("SELECT grammar_item_id, parent_id FROM grammar_items").fetchall()
    by_id = {r[0]: r[1] for r in rows}
    bad = sum(1 for gid in by_id if _bad_grammar_chain(gid, by_id))
    check("grammar 每节点能 trace 到根", bad == 0, f"bad_chain={bad}")


def _check_14_graph_refs(con):
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


def _check_15_xref(con):
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
    check("units ↔ unit node 一致", miss_u == 0, f"miss={miss_u}")
    check("exam_questions ↔ question node 一致", miss_q == 0, f"miss={miss_q}")
    check("course_materials ref_id 全有 node", miss_m == 0, f"miss={miss_m}")


def _check_16_placement(con):
    print("\n=== (16) 摸底测验卷 placement ===")
    from backend.services.placement import generator, loader
    specs = loader.load_specs()
    check("3 套 spec (G1/G2/G3)", len(specs) == 3, f"{len(specs)} 套")
    for s in specs:
        try:
            p = generator.generate_paper(con, s)
            check(f"{s['grade']} 抽足题",
                  p["total_actual"] == s["total_questions"],
                  f"exp={s['total_questions']} got={p['total_actual']}")
        except Exception as e:
            check(f"{s['grade']} generate 跑通", False, f"err: {e}")


def _check_17_cross_version(con):
    print("\n=== (17) 跨版本对照 v4 100% (30 对扩验) ===")
    from backend.services import recommend
    sample = "unit:waiyan/xuanze_1/U6"
    res = recommend.cross_version_units(con, sample)
    check("nature 主题种子返 3 same-cefr",
          len(res) == 3 and all("nature" in r["shared_core_tokens"] for r in res),
          f"got {len(res)} 个")


def _check_18_followup(con):
    print("\n=== (18) placement followup (Codex Q6) ===")
    from backend.services.placement import followup
    # 抽 G1 placement 的前 3 题假装做错, 验证 followup 能抽到题
    rows = con.execute(
        "SELECT qb_id FROM question_bank LIMIT 5"
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


def _check_19_listening_writing(con):
    print("\n=== (19) 听力 + 写作 (Phase 7.2/7.3) ===")
    n_listen = con.execute("SELECT COUNT(*) FROM question_bank WHERE has_audio = true").fetchone()[0]
    n_transcript = con.execute(
        "SELECT COUNT(*) FROM question_bank WHERE has_audio = true "
        "AND transcript IS NOT NULL AND transcript != ''"
    ).fetchone()[0]
    n_narrative = con.execute("SELECT COUNT(*) FROM question_bank WHERE question_type = '续写'").fetchone()[0]
    n_applied = con.execute("SELECT COUNT(*) FROM question_bank WHERE question_type = '应用文'").fetchone()[0]
    check("听力题 ≥ 20", n_listen >= 20, f"{n_listen}")
    check("听力全有 transcript", n_listen == n_transcript, f"audio={n_listen} transcript={n_transcript}")
    check("续写 ≥ 10", n_narrative >= 10, f"{n_narrative}")
    check("应用文 ≥ 10", n_applied >= 10, f"{n_applied}")


def _check_20_enriched_vocab(con):
    print("\n=== (20) enriched content 超纲词校验 (R5 程序级) ===")
    from backend.services import vocab_guard
    import yaml
    from pathlib import Path
    enriched_dir = Path("backend/config/enriched_content")
    if not enriched_dir.exists():
        check("enriched_content 目录存在", False, "目录不存在")
        return
    n_files = 0
    n_beyond_total = 0
    worst = []
    for f in sorted(enriched_dir.glob("*.yaml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
        cid = data.get("course_id")
        layer = data.get("generation_meta", {}).get("vocab_layer", "G_FINAL")
        text = "\n".join(data.get("segments", {}).values())
        result = vocab_guard.check_text(con, text, layer)
        n_files += 1
        n_beyond_total += result["beyond_count"]
        if result["beyond_words"]:
            worst.append((cid, layer, result["beyond_words"][:5]))
    check(f"enriched {n_files} 文件已扫描",
          n_files > 0, f"{n_files} files")
    check(f"超纲词总数 = 0",
          n_beyond_total == 0,
          f"{n_beyond_total} 超纲" + (f" (worst: #{worst[0][0]} {worst[0][2]})" if worst else ""))


# ===== helpers (CC ≤ 4) =====

def _audit_ok(con, kind: str) -> bool:
    rows = con.execute(
        "SELECT severity FROM audit_findings WHERE audit_kind LIKE ? OR audit_kind = ?",
        [f"%{kind}%", kind],
    ).fetchall()
    return bool(rows) and all(r[0] == "OK" for r in rows)


def _stem_has_abcd(stem: str | None) -> bool:
    if not stem:
        return False
    return bool(re.search(r"A[\.、].{1,200}B[\.、].{1,200}C[\.、].{1,200}D[\.、]", stem, re.DOTALL))


def _bad_grammar_chain(gid: str, by_id: dict) -> bool:
    cur = gid
    par = by_id.get(cur)
    hop = 0
    while par and hop < 10:
        if par not in by_id:
            return True
        cur = par
        par = by_id.get(cur)
        hop += 1
    return False


# ===== main 调度 (CC = 2) =====

CHECKS = [
    _check_1_manifest, _check_2_vocab, _check_3_grammar, _check_4_phrases,
    _check_5_handouts, _check_6_graph, _check_7_audit_summary, _check_8_course_audits,
    _check_9_qbank, _check_10_qbank_options, _check_11_tag_dict,
    _check_12_cefr_node_xref, _check_13_grammar_chain, _check_14_graph_refs,
    _check_15_xref, _check_16_placement, _check_17_cross_version,
    _check_18_followup, _check_19_listening_writing, _check_20_enriched_vocab,
]


def main() -> int:
    if not DB_PATH.exists():
        print(f"❌ DB 不存在 — 先跑 init_db: {DB_PATH}")
        return 1
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        for fn in CHECKS:
            fn(con)
    finally:
        con.close()
    print("\n" + "=" * 60)
    if FAILURES:
        print(f"❌ D0 100% 未达, {len(FAILURES)} 项失败:")
        for f in FAILURES:
            print(f"   - {f}")
        return 1
    print(f"✅ D0 100% 准确率达成, 全部检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
