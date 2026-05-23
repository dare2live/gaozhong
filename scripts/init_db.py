"""建空 DuckDB + 顺序: schema → load truth source → mirror exam → canonical → links → audit.

按 docs/architecture.md 三铁律: 单一计算点; canonical first; edges 走表.
日后改业务: 改对应 service, 重跑本脚本即可一键同步.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.services import canonical, links, audit  # noqa: E402
from backend.services.extraction import exam as exam_extract  # noqa: E402

DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"
SCHEMA_PATH = ROOT / "backend" / "db" / "schema.sql"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _load_main_tables(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    counts: dict[str, int] = {}

    vocab = _read_jsonl(ROOT / "data/structured/curriculum/cefr_vocab.jsonl")
    con.executemany(
        "INSERT OR REPLACE INTO cefr_vocab VALUES (?, ?, ?, ?)",
        [(r["word"], r["cefr_level"], r["raw_suffix"], r["source"]) for r in vocab],
    )
    counts["cefr_vocab"] = len(vocab)

    gram = _read_jsonl(ROOT / "data/structured/curriculum/grammar_items.jsonl")
    con.executemany(
        "INSERT OR REPLACE INTO grammar_items VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [(r["grammar_item_id"], r["depth"], r.get("parent_id"), r.get("category"),
          r["label"], r["cefr_level"], r.get("seq"), r["source"]) for r in gram],
    )
    counts["grammar_items"] = len(gram)

    themes = _read_jsonl(ROOT / "data/structured/curriculum/theme_contexts.jsonl")
    con.executemany(
        "INSERT OR REPLACE INTO theme_contexts VALUES (?, ?, ?, ?, ?)",
        [(r["theme_context_id"], r["level1"], r.get("level2"), r.get("level3"), r["source"]) for r in themes],
    )
    counts["theme_contexts"] = len(themes)

    pubs = _read_jsonl(ROOT / "data/structured/curriculum/liaoning_allowed_english_publishers_2023.jsonl")
    con.executemany(
        "INSERT OR REPLACE INTO liaoning_allowed_publishers VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(r["rank"], r["subject"], r["chief_editor"], r["publisher"], r["book_title"],
          json.dumps(r["volumes"], ensure_ascii=False), r["source"]) for r in pubs],
    )
    counts["liaoning_allowed_publishers"] = len(pubs)

    cities = _read_jsonl(ROOT / "data/structured/curriculum/liaoning_city_textbook_choice_2026.jsonl")
    con.executemany(
        "INSERT OR REPLACE INTO liaoning_city_textbook_choice VALUES (?, ?, ?, ?)",
        [(r["city"], r["subject"], r["publisher_short"], r["source"]) for r in cities],
    )
    counts["liaoning_city_textbook_choice"] = len(cities)
    return counts


def _load_textbooks(con: duckdb.DuckDBPyConnection) -> int:
    label_map = {
        "waiyan": "外研社版-外语教学与研究出版社 (2019 新版)",
        "renjiao": "人教版-人民教育出版社 (2019 新版)",
    }
    rows = []
    for ver_dir in sorted((ROOT / "data/textbooks").iterdir()):
        if not ver_dir.is_dir(): continue
        for pdf in sorted(ver_dir.glob("*.pdf")):
            try:
                pages = len(PdfReader(pdf).pages)
            except Exception:
                pages = None
            rows.append((
                ver_dir.name, pdf.stem,
                label_map.get(ver_dir.name, ver_dir.name),
                str(pdf.relative_to(ROOT)),
                _sha256(pdf), pages,
            ))
    con.executemany("INSERT OR REPLACE INTO textbooks VALUES (?, ?, ?, ?, ?, ?)", rows)
    return len(rows)


def _load_file_manifest(con: duckdb.DuckDBPyConnection) -> int:
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for base, kind in [
        (ROOT / "data/textbooks", "textbook"),
        (ROOT / "data/curriculum", "curriculum"),
        (ROOT / "data/structured", "structured"),
        (ROOT / "data/external", "external"),
    ]:
        if not base.exists(): continue
        for f in base.rglob("*"):
            if f.is_file():
                try:
                    rows.append((
                        str(f.relative_to(ROOT)), kind,
                        _sha256(f), f.stat().st_size, None, now,
                    ))
                except Exception:
                    pass
    con.executemany("INSERT OR REPLACE INTO file_manifest VALUES (?, ?, ?, ?, ?, ?)", rows)
    return len(rows)


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    con = duckdb.connect(str(DB_PATH))
    con.execute(SCHEMA_PATH.read_text(encoding="utf-8"))

    print("=== Layer 2: load main tables ===")
    for k, v in _load_main_tables(con).items():
        print(f"  {k}: {v}")
    print(f"  textbooks: {_load_textbooks(con)}")

    print("\n=== Layer 2: mirror gaokao exam questions (with Liaoning hint) ===")
    s = exam_extract.mirror_to_jsonl(write_db_conn=con)
    print(f"  files: {s['files']}, examples: {s['examples']}")
    print(f"  by_province: {s['by_province']}")
    print(f"  by_type: {s['by_type']}")

    print(f"\n  file_manifest: {_load_file_manifest(con)}")

    print("\n=== Layer 3: canonical/concept (build nodes) ===")
    nc = canonical.build_all(con)
    for k, v in nc.items():
        print(f"  nodes.{k}: {v}")
    total_nodes = con.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    print(f"  TOTAL nodes: {total_nodes}")

    print("\n=== Layer 3: links/build (build edges) ===")
    lk = links.build_all(con)
    for k, v in lk.items():
        print(f"  edges.{k}: {v}")
    total_edges = con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    print(f"  TOTAL edges: {total_edges}")

    print("\n=== Layer 3: audit/cross_check ===")
    s = audit.run_all(con)
    for k, v in s.items():
        print(f"  {k}: {v}")
    n_fail = con.execute("SELECT COUNT(*) FROM audit_findings WHERE severity='FAIL'").fetchone()[0]
    n_warn = con.execute("SELECT COUNT(*) FROM audit_findings WHERE severity='WARN'").fetchone()[0]
    print(f"  审计总览: {n_fail} FAIL, {n_warn} WARN")

    print(f"\nDB ready at {DB_PATH.relative_to(ROOT)}")
    con.close()


if __name__ == "__main__":
    main()
