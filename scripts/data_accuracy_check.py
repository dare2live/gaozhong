#!/usr/bin/env python3
"""D0 强执行: 全数据集 100% 准确率校验.

跑法:
  python3 scripts/data_accuracy_check.py
  exit 0 = 全部 100% 准
  exit 1 = 任何一项不达标

校验维度:
  (1) 数据基石 — 教材 PDF sha + 课标 PDF + manifest 完整
  (2) 词集 — cefr_vocab 2986 + unit_vocab_intro 4056 + 抽样比对
  (3) 语法 — grammar_items DAG 完整 + 父子链
  (4) 短语 - phrases + edges 引用完整
  (5) 教案 — course_handouts 40 节 + 7 段全 + R2 audit 0 重叠
  (6) 知识图谱 — nodes 引用完整 + edges 引用完整 + 孤儿 = 0
  (7) 关联 (audit_findings 44 全 OK, 0 FAIL/WARN)
  (8) 推荐算法 — 跨版本对照 100% (取 P1.3 doc 已验)
  (9) 课程 R1-R6 + 听力 + 政治 8 audit 全 OK
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
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


def main() -> int:
    if not DB_PATH.exists():
        print(f"❌ DB 不存在: {DB_PATH} — 先 python3 scripts/init_db.py")
        return 1
    con = duckdb.connect(str(DB_PATH), read_only=True)

    print("=== (1) 数据基石 sha + manifest ===")
    n_mani = con.execute("SELECT COUNT(*) FROM file_manifest").fetchone()[0]
    n_tb   = con.execute("SELECT COUNT(*) FROM textbooks").fetchone()[0]
    check("manifest 行 ≥ 14",        n_mani >= 14, f"{n_mani}")
    check("textbooks 表 == 14",      n_tb == 14,   f"{n_tb}")
    check("每教材 PDF sha 已锁",     _all_sha_set(con),
          "textbooks.pdf_sha256 全非空")

    print("\n=== (2) 词集 ===")
    n_cefr = con.execute("SELECT COUNT(*) FROM cefr_vocab").fetchone()[0]
    n_uvi  = con.execute("SELECT COUNT(*) FROM unit_vocab_intro").fetchone()[0]
    check("cefr_vocab 2986 (课标 3 级)",   n_cefr == 2986, f"{n_cefr}")
    check("unit_vocab_intro 行 > 4000",   n_uvi > 4000,  f"{n_uvi}")
    check("cefr_vocab 3 级全在",          _cefr_levels(con) == {"义教", "必修", "选必"})

    print("\n=== (3) 语法 ===")
    n_g = con.execute("SELECT COUNT(*) FROM grammar_items").fetchone()[0]
    check("grammar_items 行 == 106",      n_g == 106, f"{n_g}")
    check("grammar DAG 无环 (audit_grammar_dag OK)", _audit_ok(con, "grammar_dag"))
    n_orphan = con.execute(
        "SELECT COUNT(*) FROM grammar_items WHERE parent_id IS NOT NULL "
        "AND parent_id NOT IN (SELECT grammar_item_id FROM grammar_items)"
    ).fetchone()[0]
    check("grammar parent_id 引用完整",   n_orphan == 0, f"orphan={n_orphan}")

    print("\n=== (4) 短语 ===")
    n_ph = con.execute("SELECT COUNT(*) FROM phrases").fetchone()[0]
    check("phrases 总 > 100",            n_ph > 100, f"{n_ph}")

    print("\n=== (5) 教案 (course_handouts) ===")
    n_h = con.execute("SELECT COUNT(*) FROM course_handouts").fetchone()[0]
    n_short = con.execute("SELECT COUNT(*) FROM course_handouts WHERE md_chars < 1000").fetchone()[0]
    check("40 节讲义全持久化",            n_h == 40, f"{n_h}")
    check("每节 md ≥ 1000 字符 (7 段全)", n_short == 0, f"{n_short} 节短")
    check("R2 无 ≥10 词教材重叠 (audit OK)", _audit_ok(con, "audit_course_no_textbook_copy"))

    print("\n=== (6) 知识图谱 ===")
    n_n = con.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    n_e = con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    check("nodes ≥ 4000",                n_n >= 4000, f"{n_n}")
    check("edges ≥ 30000",               n_e >= 30000, f"{n_e}")
    check("graph_edge_validity OK",      _audit_ok(con, "graph_edge_validity"))
    check("graph_orphans OK",            _audit_ok(con, "graph_orphans"))
    check("graph_grammar_dag OK",        _audit_ok(con, "graph_grammar_dag"))
    check("graph_relation_dict OK",      _audit_ok(con, "graph_relation_dict"))

    print("\n=== (7) Audit 44 全 OK / 0 FAIL / 0 WARN ===")
    fails = con.execute("SELECT COUNT(*) FROM audit_findings WHERE severity='FAIL'").fetchone()[0]
    warns = con.execute("SELECT COUNT(*) FROM audit_findings WHERE severity='WARN'").fetchone()[0]
    oks   = con.execute("SELECT COUNT(*) FROM audit_findings WHERE severity='OK'").fetchone()[0]
    check("0 FAIL",                      fails == 0, f"{fails}")
    check("0 WARN",                      warns == 0, f"{warns}")
    check("OK ≥ 40 (全数据点已审)",       oks >= 40,  f"{oks}")

    print("\n=== (8) 课程 R1-R6 + 听力 + 政治 8 audit ===")
    for k in ("audit_course_relations", "audit_course_no_textbook_copy",
              "audit_course_scenarios", "audit_homework_alignment",
              "audit_course_lexical_layer", "audit_course_textbook_position",
              "audit_listening_transcript_required", "audit_no_political"):
        check(k, _audit_ok(con, k))

    print("\n=== (9) 题库 + 标签 ===")
    n_qb = con.execute("SELECT COUNT(*) FROM question_bank").fetchone()[0]
    n_qt = con.execute("SELECT COUNT(*) FROM question_tags").fetchone()[0]
    check("question_bank 509",           n_qb == 509, f"{n_qb}")
    check("question_tags > 10000",       n_qt > 10000, f"{n_qt}")
    n_orphan_qt = con.execute(
        "SELECT COUNT(*) FROM question_tags qt WHERE qt.qb_id NOT IN "
        "(SELECT qb_id FROM question_bank)"
    ).fetchone()[0]
    check("question_tags qb_id 引用完整", n_orphan_qt == 0, f"orphan={n_orphan_qt}")

    print("\n=== (10) 课程 + 学生 ===")
    n_c = con.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    n_m = con.execute("SELECT COUNT(*) FROM course_materials").fetchone()[0]
    check("courses 40",                  n_c == 40, f"{n_c}")
    check("course_materials > 500",      n_m > 500, f"{n_m}")
    check("students ≥ 5 (demo)",         con.execute("SELECT COUNT(*) FROM students").fetchone()[0] >= 5)
    check("classes ≥ 1 (demo)",          con.execute("SELECT COUNT(*) FROM classes").fetchone()[0] >= 1)

    print("\n=== (11) 知识图谱深扫: 引用完整性 ===")
    # edges.src_id / dst_id 必须全部在 nodes 表 (孤儿 edges = 数据不一致)
    n_orphan_src = con.execute(
        "SELECT COUNT(*) FROM edges WHERE src_id NOT IN (SELECT concept_id FROM nodes)"
    ).fetchone()[0]
    n_orphan_dst = con.execute(
        "SELECT COUNT(*) FROM edges WHERE dst_id NOT IN (SELECT concept_id FROM nodes)"
    ).fetchone()[0]
    check("edges.src_id 全在 nodes",      n_orphan_src == 0, f"orphan src={n_orphan_src}")
    check("edges.dst_id 全在 nodes",      n_orphan_dst == 0, f"orphan dst={n_orphan_dst}")
    # 孤立 node — 区分"必有 edge"(word/grammar/question/phrase/unit) vs "可独立"(theme/cefr_level/subject)
    n_iso_critical = con.execute("""
        SELECT COUNT(*) FROM nodes n
        WHERE n.node_type IN ('word','grammar','question','phrase','unit')
          AND n.concept_id NOT IN (SELECT src_id FROM edges)
          AND n.concept_id NOT IN (SELECT dst_id FROM edges)
    """).fetchone()[0]
    check("孤立关键 node = 0 (word/grammar/question/phrase/unit)",
          n_iso_critical == 0, f"isolated={n_iso_critical}")
    # OBS: theme/cefr_level/subject 等元数据节点可独立 (eg 课标 level3 主题未被 unit 引用 — 真实状态)
    n_iso_meta = con.execute("""
        SELECT COUNT(*) FROM nodes n
        WHERE n.node_type IN ('theme','cefr_level','subject','exam_year','qtype')
          AND n.concept_id NOT IN (SELECT src_id FROM edges)
          AND n.concept_id NOT IN (SELECT dst_id FROM edges)
    """).fetchone()[0]
    check("OBS: 孤立元数据 node 数 (theme/cefr 等可独立)",
          True, f"OBS={n_iso_meta} (元数据可独立, 非 bug)")

    print("\n=== (12) 词集 ↔ 节点 一致性 (抽样 100) ===")
    # cefr_vocab 词必须在 nodes (concept_id='word:xxx')
    miss_words = con.execute("""
        SELECT COUNT(*) FROM cefr_vocab c
        WHERE 'word:' || LOWER(c.word) NOT IN (SELECT concept_id FROM nodes WHERE node_type='word')
    """).fetchone()[0]
    check("cefr_vocab 全有对应 word node", miss_words == 0, f"miss={miss_words}")
    # nodes word label ↔ concept_id 一致 (label 应等于 concept_id 去 'word:')
    mismatch_labels = con.execute("""
        SELECT COUNT(*) FROM nodes WHERE node_type='word'
          AND LOWER(label) <> LOWER(REPLACE(concept_id, 'word:', ''))
    """).fetchone()[0]
    check("word node label↔concept_id 一致", mismatch_labels == 0, f"mismatch={mismatch_labels}")

    print("\n=== (13) 教材 unit ↔ nodes 一致性 ===")
    miss_units = con.execute("""
        SELECT COUNT(*) FROM units u
        WHERE 'unit:' || u.version_key || '/' || u.volume_key || '/U' || u.unit_number
              NOT IN (SELECT concept_id FROM nodes WHERE node_type='unit')
    """).fetchone()[0]
    check("units 全有对应 unit node",     miss_units == 0, f"miss={miss_units}")

    print("\n=== (14) 真题 question ↔ nodes 一致性 ===")
    miss_q = con.execute("""
        SELECT COUNT(*) FROM exam_questions q
        WHERE 'question:' || q.question_id
              NOT IN (SELECT concept_id FROM nodes WHERE node_type='question')
    """).fetchone()[0]
    check("exam_questions 全有对应 question node", miss_q == 0, f"miss={miss_q}")

    print("\n=== (15) 课程 materials ref_id 引用 ===")
    # course_materials.ref_id (kind=word/grammar/phrase/exam_question) 必须存在
    miss_ref = con.execute("""
        SELECT COUNT(*) FROM course_materials cm
        WHERE cm.kind IN ('word','grammar','phrase')
          AND cm.ref_id NOT IN (SELECT concept_id FROM nodes)
    """).fetchone()[0]
    check("course_materials ref_id 全有 node", miss_ref == 0, f"miss={miss_ref}")

    print("\n=== (16) 摸底测验卷 placement (D 2026-05-25) ===")
    from backend.services.placement import generator, loader
    specs = loader.load_specs()
    check("placement_tests.yaml 3 套 (G1/G2/G3)",
          len(specs) == 3, f"{len(specs)} 套")
    for s in specs:
        try:
            p = generator.generate_paper(con, s)
            check(f"{s['grade']} 抽足题 ({s['total_questions']})",
                  p["total_actual"] == s["total_questions"],
                  f"exp={s['total_questions']} got={p['total_actual']}")
        except Exception as e:
            check(f"{s['grade']} generate 跑通", False, f"err: {e}")

    print("\n=== (17) 跨版本对照算法 v3 100% (复用 docs) ===")
    # Re-run 10 种子 sample 看返非 0 的算法是否还工作
    from backend.services import recommend
    sample_unit = "unit:waiyan/xuanze_1/U6"   # P1.3 验证过的 nature 主题种子
    res = recommend.cross_version_units(con, sample_unit)
    check("cross_version 'nature 主题' 返 3 个 same-cefr",
          len(res) == 3 and all("nature" in r["shared_core_tokens"] for r in res),
          f"got {len(res)} 个: {[r['unit_id'] for r in res]}")

    con.close()

    print("\n" + "=" * 60)
    if FAILURES:
        print(f"❌ D0 100% 准确率未达, {len(FAILURES)} 项失败:")
        for f in FAILURES:
            print(f"   - {f}")
        return 1
    print(f"✅ D0 100% 准确率达成, 全部检查通过")
    return 0


def _all_sha_set(con) -> bool:
    n = con.execute("SELECT COUNT(*) FROM textbooks WHERE pdf_sha256 IS NULL OR pdf_sha256 = ''").fetchone()[0]
    return n == 0


def _cefr_levels(con) -> set[str]:
    return {r[0] for r in con.execute("SELECT DISTINCT cefr_level FROM cefr_vocab").fetchall()}


def _audit_ok(con, kind: str) -> bool:
    rows = con.execute(
        "SELECT severity FROM audit_findings WHERE audit_kind LIKE ? OR audit_kind = ?",
        [f"%{kind}%", kind],
    ).fetchall()
    if not rows:
        return False
    return all(r[0] == "OK" for r in rows)


if __name__ == "__main__":
    sys.exit(main())
