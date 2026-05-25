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

    print("\n=== Layer 4c: 写作练习入库 (Phase 7.3: 续写+应用文) ===")
    from backend.services.course.writing import load_writing_exercises
    writing_rows = load_writing_exercises()
    now_str = datetime.now(timezone.utc).isoformat()
    for wr in writing_rows:
        con.execute(
            "INSERT INTO question_bank (qb_id, question_type, stem, options_json, answer, "
            "difficulty, origin, origin_ref, created_at, analysis) "
            "VALUES (nextval('qb_id_seq'), ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [wr["question_type"], wr["stem"], wr["options_json"], wr["answer"],
             wr["difficulty"], wr["origin"], wr["origin_ref"], now_str,
             wr.get("analysis", "")],
        )
    print(f"  writing exercises: {len(writing_rows)} (续写+应用文)")

    print("\n=== Layer 4d: 听力练习入库 (Phase 7.2: 短对话/长对话/独白) ===")
    from backend.services.course.listening import load_listening_exercises
    listening_rows = load_listening_exercises()
    for lr in listening_rows:
        con.execute(
            "INSERT INTO question_bank (qb_id, question_type, stem, options_json, answer, "
            "difficulty, origin, origin_ref, created_at, analysis, "
            "has_audio, audio_id, transcript, audio_speakers, audio_duration) "
            "VALUES (nextval('qb_id_seq'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [lr["question_type"], lr["stem"], lr["options_json"], lr["answer"],
             lr["difficulty"], lr["origin"], lr["origin_ref"], now_str,
             lr.get("analysis", ""),
             lr["has_audio"], lr["audio_id"], lr["transcript"],
             lr["audio_speakers"], lr["audio_duration"]],
        )
    print(f"  listening exercises: {len(listening_rows)} (短对话+长对话+独白)")

    print("\n=== Layer 4f: 阅读理解练习入库 (Phase 7.4: 趋势驱动) ===")
    from backend.services.course.reading import load_reading_exercises
    reading_rows = load_reading_exercises()
    for rr in reading_rows:
        con.execute(
            "INSERT INTO question_bank (qb_id, question_type, stem, options_json, answer, "
            "difficulty, origin, origin_ref, created_at, analysis) "
            "VALUES (nextval('qb_id_seq'), ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [rr["question_type"], rr["stem"], rr["options_json"], rr["answer"],
             rr["difficulty"], rr["origin"], rr["origin_ref"], now_str,
             rr.get("analysis", "")],
        )
    print(f"  reading exercises: {len(reading_rows)} (趋势驱动: 词义猜测/标题/推理/七选五)")

    print(f"  qb total: {con.execute('SELECT COUNT(*) FROM question_bank').fetchone()[0]}")
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
    import subprocess
    r = subprocess.run(["python3", "scripts/import_recent_exams.py"],
                       capture_output=True, text=True, timeout=60)
    for line in (r.stdout or "").strip().split("\n"):
        if line.strip(): print(f"  {line.strip()}")
    if r.returncode != 0:
        print(f"  PDF import warning: {(r.stderr or '')[:200]}")

    print("\n=== Layer 4h: 设计宪法入库 (model_driven_design) ===")
    from backend.services import constitution
    cs = constitution.seed(con)
    print(f"  constitution: {cs['total']} 条 ({cs['principles']} 原则 + {cs['iron_laws']} 铁律 + {cs['violations']} 违宪)")

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
