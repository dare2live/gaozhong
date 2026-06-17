#!/usr/bin/env python3
"""D0 强执行: 全数据集 100% 准确率校验.

跑法:
  python3 scripts/data_accuracy_check.py
  exit 0 = 全 100% 准
  exit 1 = 任一项不达

模块化设计 (M6 CC ≤ 10): _check_* 章节函数, main 只调度.
2026-06-15 Phase 7 生成层回滚: 移除 check_5(讲义)/19(听力写作)/20(enriched 超纲) 三项
(校验已删的生成内容); check_9/10/16 改为对「仅真题」题库诚实校验.
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
    check("cefr_vocab 3052", n_cefr == 3052, f"{n_cefr}")  # 2986→3055→3052: 补 p182/183 漏抽页 + 截国家表 3 误纳
    # 4253→3982: 单一区段重写后 renjiao(2132→1957)+waiyan(2121→2025) 剔除 331+96 跨单元重复
    # /glossary 污染行 + renjiao 补回漏词。净降是去污结果(更准非更少), 下界防丢册回归。
    check("unit_vocab_intro ≥ 3900", n_uvi >= 3900, f"{n_uvi}")
    check("cefr 3 级全在", lvls == {"义教", "必修", "选必"})
    # 防回归(坑1, 强化版): 旧门 (MIN<20 AND MAX>50) 只抓"单单元塌缩+同册有兄弟>50"一种形态,
    # 漏报整册齐塌 + 完全无感 331 跨单元重复(膨胀非塌缩)。换 2 个鲁棒断言:
    # (a) 绝对地板: 任一单元 distinct word <20 = 抽取塌缩嫌疑(不依赖兄弟单元)。
    floor = con.execute("""
        WITH u AS (SELECT version_key, volume_key, unit_number, COUNT(DISTINCT word) c
                   FROM unit_vocab_intro WHERE unit_number > 0 GROUP BY 1,2,3)
        SELECT version_key, volume_key, unit_number, c FROM u WHERE c < 20 ORDER BY c
    """).fetchall()
    check("无单元词表塌缩 (绝对地板 ≥20词)", not floor,
          "无塌缩" if not floor else f"塌缩: {[(r[0],r[1],r[2],r[3]) for r in floor[:5]]}")
    # (b) 跨单元唯一性: 同版同册同词只能属 1 个单元(违反=字母总表/复习段被砸进某单元污染,
    #     破坏 §1.2 词量≤已学单元)。renjiao(331→0)+waiyan(96→0) 均重写为单一区段抽取后锁死防回归。
    xu_dup = con.execute("""
        WITH u AS (SELECT version_key, volume_key, word, COUNT(DISTINCT unit_number) k
                   FROM unit_vocab_intro WHERE unit_number>0 GROUP BY 1,2,3)
        SELECT version_key, volume_key, word, k FROM u WHERE k>1 ORDER BY k DESC
    """).fetchall()
    check("词无跨单元重复 (单一区段抽取锁, 全版本)", not xu_dup,
          "0 重复" if not xu_dup else f"{len(xu_dup)} 对: {[(r[0],r[1],r[2]) for r in xu_dup[:5]]}")


def _check_3_grammar(con):
    print("\n=== (3) 语法 ===")
    n_g = con.execute("SELECT COUNT(*) FROM grammar_items").fetchone()[0]
    n_orphan = con.execute(
        "SELECT COUNT(*) FROM grammar_items WHERE parent_id IS NOT NULL "
        "AND parent_id NOT IN (SELECT grammar_item_id FROM grammar_items)"
    ).fetchone()[0]
    check("grammar_items 行 == 108", n_g == 108, f"{n_g}")  # 106→108: 补限制性/非限制性定语从句(原_skip_line误杀)
    check("grammar DAG 无环 (audit OK)", _audit_ok(con, "grammar_dag"))
    check("grammar parent_id 引用完整", n_orphan == 0, f"orphan={n_orphan}")
    n_occ = con.execute("SELECT COUNT(*) FROM grammar_occurrences").fetchone()[0]  # §1.2 语法per-unit
    bad_occ = con.execute("SELECT COUNT(*) FROM grammar_occurrences WHERE grammar_item_id NOT IN (SELECT grammar_item_id FROM grammar_items)").fetchone()[0]
    check("grammar_occurrences 已填(§1.2 语法per-unit)", n_occ >= 15, f"{n_occ}")
    check("grammar_occurrences FK 有效", bad_occ == 0, f"{bad_occ}")


def _check_4_phrases(con):
    print("\n=== (4) 短语 ===")
    n_ph = con.execute("SELECT COUNT(*) FROM phrases").fetchone()[0]
    check("phrases > 100", n_ph > 100, f"{n_ph}")


def _check_6_graph(con):
    print("\n=== (6) 知识图谱 ===")
    n_n = con.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    n_e = con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    check("nodes ≥ 4000", n_n >= 4000, f"{n_n}")
    # 2026-06-15 去停用词污染后 tests_word 边减少 (41% 是 the/it 噪声边); 阈值从 30000 降到 20000 反映清洗后真实图谱
    check("edges ≥ 20000", n_e >= 20000, f"{n_e}")
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
    print("\n=== (9) 题库 (仅真题, Phase 7 生成层已回滚) ===")
    n_qb = con.execute("SELECT COUNT(*) FROM question_bank").fetchone()[0]
    n_nonreal = con.execute("SELECT COUNT(*) FROM question_bank WHERE origin <> 'real'").fetchone()[0]
    n_qt = con.execute("SELECT COUNT(*) FROM question_tags").fetchone()[0]
    n_orphan = con.execute(
        "SELECT COUNT(*) FROM question_tags WHERE qb_id NOT IN (SELECT qb_id FROM question_bank)"
    ).fetchone()[0]
    check("question_bank > 0 (真题)", n_qb > 0, f"{n_qb}")
    check("无合成/生成题 (origin 全 real)", n_nonreal == 0, f"非真题={n_nonreal}")
    check("question_tags > 0", n_qt > 0, f"{n_qt}")
    check("question_tags 引用完整", n_orphan == 0, f"orphan={n_orphan}")


def _check_10_qbank_options(con):
    # Phase 7 回滚后题库仅真题 (篇章格式), 选项内嵌于题干/原文; 不再按合成题的独立 options 校验.
    # D0 关注真实性: 真题 stem 必须有真实内容; 答案缺失(2024/2025 PDF 未抽答案/写作主观题)属已知 gap 非造假.
    print("\n=== (10) 题库真题内容完整性 (仅真题) ===")
    n_empty = con.execute("SELECT COUNT(*) FROM question_bank WHERE stem IS NULL OR TRIM(stem)=''").fetchone()[0]
    n_total = con.execute("SELECT COUNT(*) FROM question_bank").fetchone()[0]
    n_ans = con.execute("SELECT COUNT(*) FROM question_bank WHERE answer IS NOT NULL AND answer<>''").fetchone()[0]
    check("真题 stem 全非空 (有真实内容)", n_empty == 0, f"空={n_empty}")
    check("客观题答案有覆盖 (写作/PDF未抽属gap)", n_ans > 0, f"{n_ans}/{n_total} 有答案")


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


# _check_14..18 (图谱/xref/placement/cross_version/followup) 抽到 lib (避 god-module Rule 8)
def _check_14_graph_refs(con):
    from scripts.lib.d0_graph_qbank_check import check_graph_refs
    check_graph_refs(con, check)


def _check_15_xref(con):
    from scripts.lib.d0_graph_qbank_check import check_xref
    check_xref(con, check)


def _check_16_placement(con):
    from scripts.lib.d0_graph_qbank_check import check_placement
    check_placement(con, check)


def _check_17_cross_version(con):
    from scripts.lib.d0_graph_qbank_check import check_cross_version
    check_cross_version(con, check)


def _check_18_followup(con):
    from scripts.lib.d0_graph_qbank_check import check_followup
    check_followup(con, check)


def _check_21_exam_provenance(con):
    print("\n=== (21) 真题卷型 provenance 诚实性 (L-N/L-P/L-R, category-aware) ===")
    # 21a: 非新课标II卷 (新课标I/III/全国甲/全国乙) 的行不得标辽宁 (辽宁只用新课标II)
    bad_nonln = con.execute(
        "SELECT COUNT(*) FROM exam_questions WHERE province LIKE '辽宁%' "
        "AND paper_type IN ('新课标 I 卷','新课标 III 卷','全国甲卷','全国乙卷')"
    ).fetchone()[0]
    # 21b: 2010-2014 辽宁自主命题期, gb 数据非辽宁卷, 不得标辽宁
    bad_pre2015 = con.execute(
        "SELECT COUNT(*) FROM exam_questions WHERE year <= 2014 AND province LIKE '辽宁%'"
    ).fetchone()[0]
    # 21c: 辽宁卷的 paper_type 必为新课标II卷 (辽宁 2015 起只用新课标II)
    bad_ln_paper = con.execute(
        "SELECT COUNT(*) FROM exam_questions WHERE province LIKE '辽宁%' AND paper_type <> '新课标 II 卷'"
    ).fetchone()[0]
    # 21d: L-P smoking gun — 2021 全国甲卷 "Landscape Photographer" 行不得标辽宁
    smoking = con.execute(
        "SELECT COUNT(*) FROM exam_questions "
        "WHERE raw_question LIKE '%Landscape%Photographer%' AND province LIKE '辽宁%'"
    ).fetchone()[0]
    check("非新课标II卷(I/III/甲/乙)不冒充辽宁", bad_nonln == 0, f"{bad_nonln} 行")
    check("2010-2014 自主命题期不冒充辽宁", bad_pre2015 == 0, f"{bad_pre2015} 行")
    check("辽宁卷 paper_type 必为新课标II卷", bad_ln_paper == 0, f"{bad_ln_paper} 行")
    check("L-P smoking gun 行已诚实标注", smoking == 0, f"{smoking} 行仍标辽宁")
    # 21e: local_pdf PDF 全文完整性 (抽到 lib, 避 god-module Rule 8)
    from scripts.lib.d0_local_pdf_check import check_local_pdf_integrity
    check_local_pdf_integrity(con, check)


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


def _check_22_exam_point(con):
    """考点 canonical + 4路桥 + 薄弱环节 D0 校验 (抽到 lib/d0_exam_point_check, 避 god-module)."""
    from scripts.lib.d0_exam_point_check import check_exam_point
    check_exam_point(con, check)


def _check_23_trend_distribution(con):
    """件3: 趋势/考点分布/关联性 数值正确性 (抽到 lib/d0_trend_distribution_check)."""
    from scripts.lib.d0_trend_distribution_check import check_trend_distribution
    check_trend_distribution(con, check)


def _check_24_lesson_plan(con):
    """备课整合: 词∩真题单一计算点守恒 + 确定性 + 语法轴 FK (抽到 lib/d0_lesson_plan_check)."""
    from scripts.lib.d0_lesson_plan_check import check_lesson_plan
    check_lesson_plan(con, check)


def _check_25_exam_status(con):
    """词×真题考过状态 单一计算点一致性: province一致 + 3源一致 + #14防覆盖 (抽到 lib)."""
    from scripts.lib.d0_exam_status_check import check_exam_status
    check_exam_status(con, check)


# ===== main 调度 (CC = 2) =====

# 2026-06-15 Phase 7 生成层回滚: 移除 _check_5(讲义) / _check_19(听力写作) /
# _check_20(enriched 超纲) — 这些断言生成内容存在, 内容已删故不再校验.
CHECKS = [
    _check_1_manifest, _check_2_vocab, _check_3_grammar, _check_4_phrases,
    _check_6_graph, _check_7_audit_summary, _check_8_course_audits,
    _check_9_qbank, _check_10_qbank_options, _check_11_tag_dict,
    _check_12_cefr_node_xref, _check_13_grammar_chain, _check_14_graph_refs,
    _check_15_xref, _check_16_placement, _check_17_cross_version,
    _check_18_followup,
    _check_21_exam_provenance,
    _check_22_exam_point,
    _check_23_trend_distribution,
    _check_24_lesson_plan,
    _check_25_exam_status,
]


class _DbLocked(Exception):
    """DB 被其它写连接占用 (疑 init_db 重建中) — 瞬时运行态, 非数据错误."""


def _connect_readonly_with_retry(attempts: int = 4, wait_s: float = 2.0):
    """读连接; 锁冲突时重试(瞬时锁自愈), 仍锁抛 _DbLocked (流程级根治假阳性).

    DuckDB 单写者: init_db 重建持写锁时, 本进程读连接会撞锁报 IOException。
    那不是"数据错了", 是"DB 正被重建" — 重试几次, 仍锁则延后, 不冒充 D0 违反。
    """
    import time
    last = None
    for _ in range(attempts):
        try:
            return duckdb.connect(str(DB_PATH), read_only=True)
        except Exception as e:  # noqa: BLE001 — 仅锁冲突重试, 其它原样抛
            if "lock" not in str(e).lower():
                raise
            last = e
            time.sleep(wait_s)
    raise _DbLocked(str(last))


def main() -> int:
    if not DB_PATH.exists():
        print(f"❌ DB 不存在 — 先跑 init_db: {DB_PATH}")
        return 1
    try:
        con = _connect_readonly_with_retry()
    except _DbLocked as e:
        print("⏸ D0 校验延后: DB 被写连接占用 (疑 init_db 重建中), 非数据错误。"
              f"\n   重建完成后下次自动校验。详情: {e}")
        return 3  # 延后 (stop_gate 视为非阻断, 区别于 1=真 D0 失败)
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
