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
SCHEMA_PATH = ROOT / "backend" / "db" / "schema.sql"


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists(): DB_PATH.unlink()
    con = duckdb.connect(str(DB_PATH))
    con.execute(SCHEMA_PATH.read_text(encoding="utf-8"))

    print("=== Layer 2: main tables + textbooks ===")
    for k, v in load.load_main_tables(con).items():
        print(f"  {k}: {v}")
    print(f"  textbooks: {load.load_textbooks(con)}")

    print("\n=== Layer 2: exam mirror ===")
    print(f"  {extract.run_exam_extract(con)}")

    print("\n=== Layer 2a: EOL 真题入库 (2021/2022 辽宁新高考全国II卷, 替换 GAOKAO 混合卷占位) ===")
    from backend.services.imports import eol_import
    print(f"  {eol_import.import_eol_exams(con)}")

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

    print(f"\n  file_manifest: {load.load_file_manifest(con)}")

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

    print("\n=== Layer 4: question_bank 装载 (真题 + 合成题 + 自动打标) ===")
    qb = extract.run_question_bank(con)
    print(f"  {qb}")

    print("\n=== Layer 4b: OCR 上下文修复字典 (用户 2026-05-24) ===")
    ofd = extract.run_ocr_fix_dict(con)
    print(f"  ocr fixes: {ofd['fixes_built']}/{ofd['unknown_tokens']}, examples: {ofd['examples'][:4]}")

    print("\n=== Layer 4c: 宪法合规检查 (P4: 生成前强制) ===")
    from datetime import datetime, timezone
    now_str = datetime.now(timezone.utc).isoformat()
    try:
        from backend.services.constitution import check_compliance
        compliance = check_compliance()
        print(f"  宪法 P4 合规: year_weights={list(compliance['year_weights'].keys())}, audit_required={compliance['audit_required']}")
    except Exception as e:
        print(f"  宪法检查跳过 (首次建库): {e}")

    # 2026-06-15 Phase 7 生成层回滚: 续写/应用文/听力/阅读练习均为生成范文,
    # 教材基石不完整前不入库 (项目 §1.1). question_bank 只保留已核验真题.
    print(f"\n  qb total (仅真题): {con.execute('SELECT COUNT(*) FROM question_bank').fetchone()[0]}")
    print(f"  tags total: {con.execute('SELECT COUNT(*) FROM tag_dictionary').fetchone()[0]}")
    print(f"  question_tags: {con.execute('SELECT COUNT(*) FROM question_tags').fetchone()[0]}")

    print("\n=== Layer 4c: 40 节课程灌库 (5.5 init_courses 用户 2026-05-24) ===")
    from backend.services.course import init_courses
    cs = init_courses.run(con)
    print(f"  {cs}")

    print("\n=== Layer 4e: 学生档案 demo (5.6 #39) ===")
    from backend.services import students as students_seed
    print(f"  {students_seed.seed_demo(con)}")

    print("\n=== Layer 4g: 2024/2025 真题 PDF 导入 ===")
    # in-process 用现有写连接 (不再 subprocess 开第二写连接 → 避 DuckDB 单写者锁冲突,
    # 历来 Layer 4g subprocess 崩, local_pdf 行靠 out-of-band 手工补, 不可复现; 现入主链).
    from scripts.import_recent_exams import import_pdfs
    print(f"  {import_pdfs(con)}")

    print("\n=== Layer 4h: 设计宪法入库 (model_driven_design) ===")
    from backend.services import constitution
    cs = constitution.seed(con)
    print(f"  constitution: {cs['total']} 条 ({cs['principles']} 原则 + {cs['iron_laws']} 铁律 + {cs['violations']} 违宪)")

    print("\n=== Layer 4i: 考点 canonical 维度 (件2: genre/theme 双模型标注 → edges) ===")
    from backend.services.exam_point import load_exam_points, bridge_exam_point_themes
    print(f"  {load_exam_points(con)}")
    print(f"  桥接考点主题↔教材主题(4路追溯): {bridge_exam_point_themes(con)}")

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
