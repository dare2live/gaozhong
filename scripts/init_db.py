"""DB 重建 + 数据装载 + canonical/links/audit 全流程.

实际工作下沉到:
  backend/orchestrator/load.py      Layer 2 主表/manifest
  backend/orchestrator/extract.py   Layer 2 extraction pipeline
  backend/services/canonical.py     nodes
  backend/services/links*.py        edges
  backend/services/audit/__init__.py  审计
本脚本只调度.
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.orchestrator import extract, load  # noqa: E402
from backend.services import audit, canonical, links, links_extra  # noqa: E402

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"
SCHEMA_DIR = ROOT / "backend" / "db" / "schema"   # 模块化: 按域拆 NN_*.sql, 按序加载 (2026-06-20)


def _load_schema(con) -> None:
    """按序加载模块化 schema (00_curriculum → 06_course 域分模块)."""
    for sql_file in sorted(SCHEMA_DIR.glob("*.sql")):
        con.execute(sql_file.read_text(encoding="utf-8"))


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists(): DB_PATH.unlink()
    con = duckdb.connect(str(DB_PATH))
    _load_schema(con)

    print("\n=== Layer 0: 真相源版本注册表 (PIT/血缘横切地基, docs/kg_layer_design.md §3) ===")
    from backend.services.lineage import load_versions
    print(f"  {load_versions(con)}")

    print("=== Layer 2: main tables + textbooks ===")
    for k, v in load.load_main_tables(con).items():
        print(f"  {k}: {v}")
    print(f"  textbooks: {load.load_textbooks(con)}")

    print("\n=== Layer 2: exam mirror ===")
    print(f"  {extract.run_exam_extract(con)}")

    print("\n=== Layer 2a: EOL 真题入库 (2021/2022 辽宁新高考全国II卷, 替换 GAOKAO 混合卷占位) ===")
    from backend.services.imports import eol_import
    print(f"  {eol_import.import_eol_exams(con)}")

    print("\n=== Layer 2a2: 2026 真题入库 (辽宁新高考全国II卷, 锦宏镜像PDF+双通道转录, group级) ===")
    from backend.services.imports import xgkii2026_import
    print(f"  {xgkii2026_import.import_xgkii_2026(con)}")

    print("\n=== Layer 2a3: 2024/2025 local_pdf 真题入库 (前移自原 Layer 4g, 2026-06-26 架构修) ===")
    # 必须早于 Layer 3 边构建: 原在 Layer 4g(canonical/links 之后) → build_tests_word/exam_point 跑时
    # 这些行未入库 → tests_word 漏年(实证 2024/25 曾 0 边)。全部真题入库归位 Layer 2a*, 早于派生层。
    # import_policies(污染/缺题干门) + sources.yaml(PDF路径) 驱动, 见 scripts/import_recent_exams.py。
    from scripts.import_recent_exams import import_pdfs
    print(f"  {import_pdfs(con)}")

    print("\n=== Layer 2b: 真题 cross-verify 门禁 (宪法 §8.3) ===")
    try:
        from scripts.tools.audit.cross_verify_pdf import verify_year, PDF_MAP
        for yr in sorted(PDF_MAP.keys()):
            r = verify_year(yr, con=con)
            status = r.get("overall", r.get("status", "?"))
            n_fail = r.get("summary", {}).get("fail", 0)
            n_total = sum(r.get("summary", {}).values()) if "summary" in r else 0
            print(f"  {yr}: {status} ({n_total - n_fail}/{n_total} pass)")
            if status == "FAIL":
                raise RuntimeError(f"cross_verify FAIL for {yr} — 结构化数据与 PDF 不一致, 拒绝入库")
    except ImportError:
        print("  cross_verify_pdf 未安装, 跳过 (首次建库)")
    except RuntimeError as e:
        print(f"  ❌ {e}")
        raise

    print("\n=== Layer 2: textbook units ===")
    tu = extract.run_textbook_units(con)
    print(f"  {tu['summary']}, loaded={tu['loaded']}")

    print("\n=== Layer 2: vocab (waiyan + renjiao) ===")
    print(f"  {extract.run_vocab(con)}")

    print("\n=== Layer 2: 统一逐阶段释义词典 (word_sense 地基; 教材生词表+中考词汇表) ===")
    from backend.services.glossary import build_glossary
    print(f"  {build_glossary(con)}")

    print("\n=== Layer 2: fix titles (scope) ===")
    print(f"  {extract.run_fix_titles(con)}")

    print("\n=== Layer 2: sections ===")
    print(f"  {extract.run_sections(con)}")

    print("\n=== Layer 2: section_text ===")
    print(f"  {extract.run_section_text(con)}")

    print("\n=== Layer 2: phrases ===")
    print(f"  {extract.run_phrases(con)}")

    print("\n=== Layer 2: province refine ===")
    print(f"  {extract.run_province_refine(con)}")

    print("\n=== Layer 2: section flags ===")
    print(f"  {extract.run_section_flags(con)}")

    print("\n=== Layer 2: grammar occurrences (§1.2 语法 per-unit) ===")
    print(f"  {extract.run_grammar_occurrences(con)}")

    print(f"\n  file_manifest: {load.load_file_manifest(con)}")

    print("\n=== Layer 2x: 初中/中考子系统 (单库, exam_type/stage 判别; K12设计) ===")
    from backend.services.data_sources.extract.junior import exam as junior_exam
    print(f"  {junior_exam.load(con)}")

    print("\n=== Layer 3: canonical (nodes) ===")
    for k, v in canonical.build_all(con).items():
        print(f"  nodes.{k}: {v}")
    print(f"  TOTAL nodes: {con.execute('SELECT COUNT(*) FROM nodes').fetchone()[0]}")

    print("\n=== Layer 3: links (edges) ===")
    for k, v in links.build_all(con).items():
        print(f"  edges.{k}: {v}")
    for k, v in links_extra.build_all_extra(con).items():
        print(f"  edges.{k}: {v}")
    print(f"  edges.derive_from: {extract.run_derive_edges(con)}")
    print(f"  TOTAL edges: {con.execute('SELECT COUNT(*) FROM edges').fetchone()[0]}")

    print("\n=== Layer 3w: 超纲词分层 vocab_classification (P0-3: 接进主链, tests_word边后自动重生成) ===")
    # 前置链外手工脚本 → 现入主链: 新卷→超纲分层全自动, 消除手工 build_vocab + file_sha 级联 (复用写连接)
    from scripts.build_vocab_classification import build as build_vocab_classification
    print(f"  vocab_classification: {dict(build_vocab_classification(con))}")

    print("\n=== Layer 3x: 初中节点 (域A; word/grammar, stage 标注; inc2; 在全部高中word节点建完后跑计数才准) ===")
    from backend.services.data_sources.extract.junior import (
        vocab as junior_vocab, grammar as junior_grammar, stage_link as junior_stage_link,
        stage_backfill as junior_stage_backfill, blueprint as junior_blueprint,
        phrases as junior_phrases, sections as junior_sections,
        grammar_occurrence as junior_grammar_occurrence)
    print(f"  {junior_vocab.load(con)}")
    print(f"  {junior_grammar.load(con)}")
    print(f"  {junior_stage_link.load(con)}")
    print(f"  {junior_stage_backfill.load(con)}")   # inc3: 高中词 stage 回填
    print(f"  {junior_blueprint.load(con)}")          # inc3: 10维 deepens 边
    print(f"  {junior_sections.load(con)}")           # Phase E1: 初中units/sections/section_text地基
    print(f"  {junior_grammar_occurrence.extract_junior_grammar_occurrences(con)}")  # Phase E4: 语法单元lineage
    print(f"  {junior_phrases.load(con)}")            # 2026-07-07: 初中短语/句型/表达(须在Layer2高中phrases之后, 避免被其blanket DELETE清空)

    print("\n=== Layer 3y: 考试词典 (Canonical 词本体; 课标∪教材真超纲, 真题作旗) ===")
    from backend.services.exam_dictionary import build_exam_dictionary
    print(f"  {build_exam_dictionary(con)}")

    print("\n=== Layer 3z: word_sense 本体 (master A1; 跨阶段多义, 双模型判断+对抗验证) ===")
    from backend.services.word_sense import build_word_senses
    print(f"  {build_word_senses(con)}")

    print("\n=== Layer 4: question_bank 装载 (真题 + 合成题 + 自动打标) ===")
    qb = extract.run_question_bank(con)
    print(f"  {qb}")

    print("\n=== Layer 4b: OCR 上下文修复字典 (用户 2026-05-24) ===")
    ofd = extract.run_ocr_fix_dict(con)
    print(f"  ocr fixes: {ofd['fixes_built']}/{ofd['unknown_tokens']}, examples: {ofd['examples'][:4]}")

    # 2026-06-15 Phase 7 生成层回滚: 续写/应用文/听力/阅读练习均为生成范文,
    # 教材基石不完整前不入库 (项目 §1.1). question_bank 只保留已核验真题.
    print(f"\n  qb total (仅真题): {con.execute('SELECT COUNT(*) FROM question_bank').fetchone()[0]}")
    print(f"  tags total: {con.execute('SELECT COUNT(*) FROM tag_dictionary').fetchone()[0]}")
    print(f"  question_tags: {con.execute('SELECT COUNT(*) FROM question_tags').fetchone()[0]}")

    print("\n=== Layer 4a2: 中考真题→question_bank镶入 + tests_grammar边 (Phase E3, 须在本Layer4"
          "\n              load_real_questions之后调, 否则被其blanket DELETE清空question_bank) ===")
    from backend.services.data_sources.extract.junior import qbank as junior_qbank
    from backend.services.data_sources.extract.junior import grammar as junior_grammar
    from backend.services.data_sources.extract.junior import exam_point as junior_exam_point
    print(f"  {junior_qbank.load(con)}")
    print(f"  {junior_qbank.link_tests_word(con)}")
    print(f"  {junior_grammar.link_zhongkao_grammar(con)}")
    print(f"  {junior_exam_point.load(con)}")
    print(f"  {junior_qbank.prune_orphan_question_nodes(con)}")

    print("\n=== Layer 4c: 40 节课程灌库 (5.5 init_courses 用户 2026-05-24) ===")
    from backend.services.course import init_courses
    cs = init_courses.run(con)
    print(f"  {cs}")

    print("\n=== Layer 4e: 学生档案 demo (5.6 #39) ===")
    from backend.services import students as students_seed
    print(f"  {students_seed.seed_demo(con)}")

    # (Layer 4g 2024/2025 local_pdf 导入已前移到 Layer 2a3 — 必须早于 Layer 3 边构建, 见上)

    print("\n=== Layer 4i: 考点 canonical 维度 (件2: genre/theme 双模型标注 → edges) ===")
    from backend.services.exam_point import (load_exam_points, bridge_exam_point_themes,
                                             load_cognitive_skill)
    print(f"  {load_exam_points(con)}")
    print(f"  桥接考点主题↔教材主题(4路追溯): {bridge_exam_point_themes(con)}")
    print(f"  设问类型金矿(KG-A1, 子题级explicit_label+血缘): {load_cognitive_skill(con)}")
    from backend.services.exam_point import materialize_cooccurrence
    print(f"  考点共现关联性入图(co_occurs, 跨维era分层): {materialize_cooccurrence(con)}")
    from backend.services.theme_vocab import build_theme_vocabulary
    print(f"  主题特征词汇关联性(characterizes_theme, 辽宁区分度): {build_theme_vocabulary(con)}")

    # 坑(2026-07-06 全量重建实测发现): question_bank(Layer4)装载早于tests_exam_point边(Layer4i)
    # 生成, autotag()内的exam_point反查首次全量重建时0命中(边还不存在)——同Layer4j(weakness)
    # 的依赖顺序模式, 在4i边就绪后单独回填。
    from backend.services.question_bank import loader as qb_loader
    print(f"  组卷考点标签回填(exam_point, 4i边就绪后): {qb_loader.backfill_exam_point_tags(con)}")

    print("\n=== Layer 4j: 学情薄弱环节重算 (4i 考点边就绪后, 错题→真考点→薄弱; 取代Layer4e的token派生) ===")
    from backend.services import weakness
    print(f"  {weakness.recompute_all(con)}")

    print("\n=== Layer 3: audit ===")
    for k, v in audit.run_all(con).items():
        print(f"  {k}: {v}")
    n_fail = con.execute("SELECT COUNT(*) FROM audit_findings WHERE severity='FAIL'").fetchone()[0]
    n_warn = con.execute("SELECT COUNT(*) FROM audit_findings WHERE severity='WARN'").fetchone()[0]
    print(f"  审计: {n_fail} FAIL, {n_warn} WARN")
    print(f"\nDB ready: {DB_PATH.relative_to(ROOT)}")
    con.close()


if __name__ == "__main__":
    main()
