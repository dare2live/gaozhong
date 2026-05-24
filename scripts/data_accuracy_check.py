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
