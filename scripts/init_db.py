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
