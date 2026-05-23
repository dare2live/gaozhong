"""建空 DuckDB + load 课标 truth source + 辽宁选用约束 + 已下载教材 manifest.

跑这个脚本会**删除并重建** data/db/gaozhong.duckdb (MVP 简化, 不做迁移).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import duckdb
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"
SCHEMA_PATH = ROOT / "backend" / "db" / "schema.sql"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_jsonl(path: Path) -> list[dict]:
    out: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    con = duckdb.connect(str(DB_PATH))
    con.execute(SCHEMA_PATH.read_text(encoding="utf-8"))

    # 1) cefr_vocab
    vocab = _read_jsonl(ROOT / "data/structured/curriculum/cefr_vocab.jsonl")
    con.executemany(
        "INSERT OR REPLACE INTO cefr_vocab VALUES (?, ?, ?, ?)",
        [(r["word"], r["cefr_level"], r["raw_suffix"], r["source"]) for r in vocab],
    )
    print(f"loaded cefr_vocab: {len(vocab)} rows")

    # 2) grammar_items
    gram = _read_jsonl(ROOT / "data/structured/curriculum/grammar_items.jsonl")
    con.executemany(
        "INSERT OR REPLACE INTO grammar_items VALUES (?, ?, ?, ?, ?)",
        [(r["grammar_item_id"], r.get("category"), r["label"], r["cefr_level"], r["source"]) for r in gram],
    )
    print(f"loaded grammar_items: {len(gram)} rows")

    # 3) theme_contexts
    themes = _read_jsonl(ROOT / "data/structured/curriculum/theme_contexts.jsonl")
    con.executemany(
        "INSERT OR REPLACE INTO theme_contexts VALUES (?, ?, ?, ?, ?)",
        [(r["theme_context_id"], r["level1"], r.get("level2"), r.get("level3"), r["source"]) for r in themes],
    )
    print(f"loaded theme_contexts: {len(themes)} rows")

    # 4) liaoning_allowed_publishers
    pubs = _read_jsonl(ROOT / "data/structured/curriculum/liaoning_allowed_english_publishers_2023.jsonl")
    con.executemany(
        "INSERT OR REPLACE INTO liaoning_allowed_publishers VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (r["rank"], r["subject"], r["chief_editor"], r["publisher"],
             r["book_title"], json.dumps(r["volumes"], ensure_ascii=False), r["source"])
            for r in pubs
        ],
    )
    print(f"loaded liaoning_allowed_publishers: {len(pubs)} rows")

    # 5) liaoning_city_textbook_choice
    cities = _read_jsonl(ROOT / "data/structured/curriculum/liaoning_city_textbook_choice_2026.jsonl")
    con.executemany(
        "INSERT OR REPLACE INTO liaoning_city_textbook_choice VALUES (?, ?, ?, ?)",
        [(r["city"], r["subject"], r["publisher_short"], r["source"]) for r in cities],
    )
    print(f"loaded liaoning_city_textbook_choice: {len(cities)} rows")

    # 6) textbooks (登记下载的 14 册 PDF, 拿 sha + page count)
    label_map = {
        "waiyan": "外研社版-外语教学与研究出版社 (2019 新版)",
        "renjiao": "人教版-人民教育出版社 (2019 新版)",
    }
    book_rows = []
    for ver_dir in sorted((ROOT / "data/textbooks").iterdir()):
        if not ver_dir.is_dir():
            continue
        for pdf in sorted(ver_dir.glob("*.pdf")):
            try:
                pages = len(PdfReader(pdf).pages)
            except Exception:
                pages = None
            book_rows.append((
                ver_dir.name, pdf.stem,
                label_map.get(ver_dir.name, ver_dir.name),
                str(pdf.relative_to(ROOT)),
                _sha256(pdf), pages,
            ))
    con.executemany(
        "INSERT OR REPLACE INTO textbooks VALUES (?, ?, ?, ?, ?, ?)",
        book_rows,
    )
    print(f"loaded textbooks: {len(book_rows)} rows")

    # 7) file_manifest (扫所有数据文件)
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    manifest_rows = []
    for base, file_type in [
        (ROOT / "data/textbooks", "textbook"),
        (ROOT / "data/curriculum", "curriculum"),
        (ROOT / "data/structured", "structured"),
    ]:
        for f in base.rglob("*"):
            if f.is_file():
                try:
                    manifest_rows.append((
                        str(f.relative_to(ROOT)), file_type,
                        _sha256(f), f.stat().st_size, None, now,
                    ))
                except Exception:
                    pass
    con.executemany(
        "INSERT OR REPLACE INTO file_manifest VALUES (?, ?, ?, ?, ?, ?)",
        manifest_rows,
    )
    print(f"loaded file_manifest: {len(manifest_rows)} rows")

    # summary
    print("\n=== verify ===")
    for tbl in ["cefr_vocab", "grammar_items", "theme_contexts",
                "liaoning_allowed_publishers", "liaoning_city_textbook_choice",
                "textbooks", "file_manifest"]:
        n = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl}: {n}")

    print(f"\n  DB ready at {DB_PATH.relative_to(ROOT)}")
    con.close()


if __name__ == "__main__":
    main()
