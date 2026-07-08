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

from scripts.lib.db_lock import DbLocked, connect_readonly_with_retry  # 坑15 锁容错共享单点
from scripts.lib.d0_baselines import B  # 计数基线配置化(§3.5 no-hardcode); backend/config/d0_baselines.yaml

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
    check("manifest 行 ≥ 14", n_mani >= B('manifest_min'), f"{n_mani}")
    check("textbooks == 20 (高中14+初中hujiao6)", n_tb == B('textbooks'), f"{n_tb}")
    check("每教材 PDF sha 锁", n_no_sha == 0, "textbooks.pdf_sha256 全非空")


def _check_2_vocab(con):
    print("\n=== (2) 词集 ===")
    n_cefr = con.execute("SELECT COUNT(*) FROM cefr_vocab").fetchone()[0]
    n_uvi = con.execute("SELECT COUNT(*) FROM unit_vocab_intro").fetchone()[0]
    lvls = {r[0] for r in con.execute("SELECT DISTINCT cefr_level FROM cefr_vocab").fetchall()}
    check("cefr_vocab 3054", n_cefr == B('cefr_vocab'), f"{n_cefr}")  # 2986→3055→3052→3054: 补 p182/183 漏抽页 + 截国家表 3 误纳 + kilogramme/kilogram 跨行续行合并
    # 坑(2026-07-04): 'kilo (kilogramme,' 跨行截断到下一行'kilogram)', 旧版逐行独立解析丢失两变体词;
    # scripts/lib/curriculum_vocab.py._merge_unclosed_parens 修. 锁具体词存在(非只锁总数, 防总数巧合对上但内容仍错)。
    kilo_alts = {r[0] for r in con.execute(
        "SELECT word FROM cefr_vocab WHERE word IN ('kilogramme','kilogram')").fetchall()}
    check("cefr_vocab 含 kilogramme+kilogram (跨行续行合并防回归)",
          kilo_alts == {"kilogramme", "kilogram"}, f"{kilo_alts}")
    # 4253→3982: 单一区段重写后 renjiao(2132→1957)+waiyan(2121→2025) 剔除 331+96 跨单元重复
    # /glossary 污染行 + renjiao 补回漏词。净降是去污结果(更准非更少), 下界防丢册回归。
    check("unit_vocab_intro ≥ 3900", n_uvi >= B('unit_vocab_min'), f"{n_uvi}")
    check("cefr 3 级全在", lvls == {"义教", "必修", "选必"})
    # 防回归(坑1, 强化版): 旧门 (MIN<20 AND MAX>50) 只抓"单单元塌缩+同册有兄弟>50"一种形态,
    # 漏报整册齐塌 + 完全无感 331 跨单元重复(膨胀非塌缩)。换 2 个鲁棒断言:
    # (a) 绝对地板: 任一单元 distinct word <20 = 抽取塌缩嫌疑(不依赖兄弟单元)。
    # 坑(2026-07-08 Phase E4 发现): 原查询"全版本"无 version_key 过滤, 把hujiao(沪教)也计入
    # 这条为renjiao/waiyan"单一区段抽取"校准的地板——hujiao卷末"in each unit"词表逐条核实
    # 是真实教材数据(部分单元本就只引入15-19个新词, 直接读原文核实非提取错误), 不该套用
    # renjiao/waiyan的≥20地板。按version_key分流, 高中口径不变(仍是回归锁), hujiao走独立
    # 口径(暂不设硬地板, 已人工核实真实分布, 见commit)。
    floor = con.execute("""
        WITH u AS (SELECT version_key, volume_key, unit_number, COUNT(DISTINCT word) c
                   FROM unit_vocab_intro WHERE unit_number > 0 AND version_key != 'hujiao' GROUP BY 1,2,3)
        SELECT version_key, volume_key, unit_number, c FROM u WHERE c < 20 ORDER BY c
    """).fetchall()
    check("无单元词表塌缩 (绝对地板 ≥20词, 高中口径)", not floor,
          "无塌缩" if not floor else f"塌缩: {[(r[0],r[1],r[2],r[3]) for r in floor[:5]]}")
    # (b) 跨单元唯一性: 同版同册同词只能属 1 个单元(违反=字母总表/复习段被砸进某单元污染,
    #     破坏 §1.2 词量≤已学单元)。renjiao(331→0)+waiyan(96→0) 均重写为单一区段抽取后锁死防回归。
    # hujiao按version_key排除(2026-07-08实测: 31个词真实跨单元重现[如'space'在7a-U5和7a-U8
    # 各因不同义项/复现被收录], 是教材真实结构非提取污染, 逐条核实见commit)。
    xu_dup = con.execute("""
        WITH u AS (SELECT version_key, volume_key, word, COUNT(DISTINCT unit_number) k
                   FROM unit_vocab_intro WHERE unit_number>0 AND version_key != 'hujiao' GROUP BY 1,2,3)
        SELECT version_key, volume_key, word, k FROM u WHERE k>1 ORDER BY k DESC
    """).fetchall()
    check("词无跨单元重复 (单一区段抽取锁, 高中口径)", not xu_dup,
          "0 重复" if not xu_dup else f"{len(xu_dup)} 对: {[(r[0],r[1],r[2]) for r in xu_dup[:5]]}")
    # 坑(2026-07-04 全数据审计): units 表(canonical)已知道哪些册有 Welcome Unit(unit_number=0),
    # 但 vocab_renjiao.py 旧版与之脱节, 把 Welcome Unit 词条错并进 Unit 1(bixiu_1 曾 99 词
    # vs 兄弟单元 45-62)。锁: 任一册在 units 表有 unit_number=0, unit_vocab_intro 必有对应
    # unit_number=0 行(否则说明 vocab 抽取又与 units 表脱节, 词条会被错并进相邻数字单元)。
    welcome_units = con.execute(
        "SELECT version_key, volume_key FROM units WHERE unit_number=0").fetchall()
    missing_welcome_vocab = [
        (vk, vol) for vk, vol in welcome_units
        if con.execute(
            "SELECT COUNT(*) FROM unit_vocab_intro WHERE version_key=? AND volume_key=? AND unit_number=0",
            [vk, vol]).fetchone()[0] == 0
    ]
    check("units 表 Welcome Unit(unit_number=0) 与 unit_vocab_intro 同步 (不脱节错并入相邻单元)",
          not missing_welcome_vocab, f"units 表有Welcome Unit但vocab无对应行: {missing_welcome_vocab}")


def _check_4_phrases(con):
    print("\n=== (4) 短语 ===")
    n_ph = con.execute("SELECT COUNT(*) FROM phrases").fetchone()[0]
    check("phrases > 100", n_ph > 100, f"{n_ph}")


def _check_6_graph(con):
    print("\n=== (6) 知识图谱 ===")
    n_n = con.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    n_e = con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    check("nodes ≥ 4000", n_n >= B('nodes_min'), f"{n_n}")
    # 2026-06-15 去停用词污染后 tests_word 边减少 (41% 是 the/it 噪声边); 阈值从 30000 降到 20000 反映清洗后真实图谱
    check("edges ≥ 20000", n_e >= B('edges_min'), f"{n_e}")
    for k in ("graph_edge_validity", "graph_orphans", "graph_grammar_dag", "graph_relation_dict"):
        check(f"{k} OK", _audit_ok(con, k))


def _check_7_audit_summary(con):
    print("\n=== (7) Audit 全 OK / 0 FAIL / 0 WARN ===")
    fails = con.execute("SELECT COUNT(*) FROM audit_findings WHERE severity='FAIL'").fetchone()[0]
    warns = con.execute("SELECT COUNT(*) FROM audit_findings WHERE severity='WARN'").fetchone()[0]
    oks = con.execute("SELECT COUNT(*) FROM audit_findings WHERE severity='OK'").fetchone()[0]
    check("0 FAIL", fails == 0, f"{fails}")
    check("0 WARN", warns == 0, f"{warns}")
    check("OK ≥ 40", oks >= B('audit_ok_min'), f"{oks}")


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
    # 21a-21d: 非新课标II卷不冒充辽宁 / 2010-14自主命题期不标辽宁 / 辽宁paper_type必II卷 / L-P smoking gun
    bad_nonln = con.execute(
        "SELECT COUNT(*) FROM exam_questions WHERE province LIKE '辽宁%' "
        "AND paper_type IN ('新课标 I 卷','新课标 III 卷','全国甲卷','全国乙卷')"
    ).fetchone()[0]
    bad_pre2015 = con.execute(
        "SELECT COUNT(*) FROM exam_questions WHERE year <= 2014 AND province LIKE '辽宁%'"
    ).fetchone()[0]
    bad_ln_paper = con.execute(
        "SELECT COUNT(*) FROM exam_questions WHERE province LIKE '辽宁%' AND paper_type <> '新课标 II 卷'"
    ).fetchone()[0]
    smoking = con.execute(
        "SELECT COUNT(*) FROM exam_questions "
        "WHERE raw_question LIKE '%Landscape%Photographer%' AND province LIKE '辽宁%'"
    ).fetchone()[0]
    check("非新课标II卷(I/III/甲/乙)不冒充辽宁", bad_nonln == 0, f"{bad_nonln} 行")
    check("2010-2014 自主命题期不冒充辽宁", bad_pre2015 == 0, f"{bad_pre2015} 行")
    check("辽宁卷 paper_type 必为新课标II卷", bad_ln_paper == 0, f"{bad_ln_paper} 行")
    check("L-P smoking gun 行已诚实标注", smoking == 0, f"{smoking} 行仍标辽宁")
    # 21e/21f: local_pdf 全文 + EOL raw_question 完整性 (抽到 lib 避 god-module Rule 8)
    from scripts.lib.d0_local_pdf_check import check_local_pdf_integrity
    from scripts.lib.d0_eol_check import check_eol_integrity
    check_local_pdf_integrity(con, check)
    check_eol_integrity(con, check)
    # 21g: 高考计数正向锁 (审计: 防漂移; B1去重后基线=466/182 非陈旧472/188; 增减须显式改基线)
    n_gk, n_ln = con.execute(
        "SELECT COUNT(*), COUNT(*) FILTER (WHERE province LIKE '辽宁%') FROM exam_questions").fetchone()
    check("高考真题计数基线 466 (B1 去重后; 改动须显式更新基线防漂移)", n_gk == B('gaokao_total'), f"{n_gk}")
    check("高考辽宁卷计数基线 182 (新课标II §7)", n_ln == B('gaokao_liaoning'), f"{n_ln}")


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


# 检查 22-29 全是 "委托到 lib 的 check_X(con, check)" 统一形 → 数据驱动 dispatch (避 god-module + 样板).
# (序号, 模块, 函数): 22考点/23趋势分布/24备课/25考过状态/26教材section/27中考/28多租户/29版本注册表.
_LIB_CHECKS = [
    ("d0_exam_point_check", "check_exam_point"),
    ("d0_exam_point_check", "check_coverage"),
    ("d0_exam_point_check", "check_syllabus"),
    ("d0_exam_point_check", "check_grammar_stats"),
    ("d0_graph_qbank_check", "check_atlas"),
    ("d0_trend_distribution_check", "check_trend_distribution"),
    ("d0_lesson_plan_check", "check_lesson_plan"),
    ("d0_exam_status_check", "check_exam_status"),
    ("d0_textbook_sections_check", "check_textbook_sections"),
    ("d0_zhongkao_check", "check_zhongkao"),
    ("d0_zhongkao_check", "check_qbank_grammar_link"),
    ("d0_zhongkao_check", "check_k12_grammar_bridge"),
    ("d0_zhongkao_check", "check_junior_exam_point"),
    ("d0_zhongkao_check", "check_zhongkao_exam_focus"),
    ("d0_tenant_check", "check_tenant_isolation"),
    ("d0_versions_check", "check_versions"),
    ("d0_versions_check", "check_liaoning_official_data"),
    ("d0_cognitive_skill_check", "check_cognitive_skill"),
    ("d0_cognitive_skill_check", "check_cognitive_cross"),
    ("d0_cognitive_skill_check", "check_joint_attribution"),
    ("d0_cognitive_skill_check", "check_cloze_answer_word_stage"),
    ("d0_senior_knowledge_check", "check_grammar_structural_coverage"),
    ("d0_senior_knowledge_check", "check_phrase_pattern_exam_relevance"),
    ("d0_senior_knowledge_check", "check_cloze_collocation_structural_subset"),
    ("d0_junior_sections_check", "check_junior_sections"),
    ("d0_junior_sections_check", "check_junior_grammar_occurrences"),
    ("d0_junior_sections_check", "check_junior_vocab_unit"),
    ("d0_junior_sections_check", "check_junior_syllabus"),
    ("d0_junior_sections_check", "check_junior_unit_content"),
    ("d0_phrases_check", "check_phrases"),
    ("d0_stage_check", "check_stage"),
    ("d0_stage_check", "check_tested_word_stage"),
    ("d0_glossary_check", "check_glossary"),
    ("d0_exam_dict_check", "check_exam_dict"),
    ("d0_word_sense_check", "check_word_sense"),
    ("d0_cooccur_check", "check_cooccur"),
    ("d0_theme_vocab_check", "check_theme_vocab"),
    ("d0_theme_vocab_check", "check_theme_of_unit"),
    ("d0_vocab_quality_check", "check_vocab_quality"),
    ("d0_governance_check", "check_ocr_fix_dictionary"),
    ("d0_governance_check", "check_student_answers_demo_transparency"),
    ("d0_governance_check", "check_real_student_isolation"),
    ("d0_k12_served_check", "check_k12_served"),
    ("endpoint_contract_check", "check_endpoint_contracts"),   # 维度38: 75端点 HTTP 契约 (endpoint_contracts.yaml, 审计MAJOR修)
    ("d0_grammar_check", "check_grammar"),   # (3) 语法(从本文件抽出, 2026-07-08 god-module瘦身)
]


def _run_lib_checks(con):
    """跑全部 lib 委托检查 (22-29); 每条 lib 自带 print 表头 + check() 断言."""
    import importlib
    for mod, fn in _LIB_CHECKS:
        getattr(importlib.import_module(f"scripts.lib.{mod}"), fn)(con, check)


def _check_truth_anchors(con):
    """真值锚校验 (验内容匹配第一手源, 非计数自洽; 根治自洽棘轮). 单算点在 truth_baseline 模块."""
    from backend.services.truth_baseline import run_truth_checks
    run_truth_checks(con, check)


# ===== main 调度 (CC=2). Phase7 回滚移除 _check_5/19/20 (断言已删生成内容) =====
CHECKS = [
    _check_1_manifest, _check_2_vocab, _check_4_phrases,
    _check_6_graph, _check_7_audit_summary, _check_8_course_audits,
    _check_9_qbank, _check_10_qbank_options, _check_11_tag_dict,
    _check_12_cefr_node_xref, _check_13_grammar_chain, _check_14_graph_refs,
    _check_15_xref, _check_16_placement, _check_17_cross_version,
    _check_18_followup,
    _check_21_exam_provenance,
    _run_lib_checks,             # 22-29: 数据驱动委托 lib (_LIB_CHECKS)
    _check_truth_anchors,        # 真值锚: 验内容匹配第一手源(非自洽棘轮)
]


def main() -> int:
    if not DB_PATH.exists():
        print(f"❌ DB 不存在 — 先跑 init_db: {DB_PATH}")
        return 1
    try:
        con = connect_readonly_with_retry(DB_PATH)
    except DbLocked as e:
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
