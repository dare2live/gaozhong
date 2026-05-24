"""Layer 2 extract pipeline: 教材 unit / vocab / section / phrase / 真题 / flags."""
from __future__ import annotations

from pathlib import Path

import duckdb

from backend.orchestrator.load import _read_jsonl
from backend.services.extraction import exam as exam_extract
from backend.services.extraction import exam_province
from backend.services.extraction import phrases as ph_extract
from backend.services.extraction import section as section_extract
from backend.services.extraction import section_flags
from backend.services.extraction import section_text as st_extract
from backend.services.extraction import textbook as textbook_extract
from backend.services.extraction import unit_title_fix
from backend.services.extraction import vocab as vocab_extract
from backend.services.extraction import vocab_renjiao as vocab_rj_extract

ROOT = Path(__file__).resolve().parent.parent.parent


def run_exam_extract(con: duckdb.DuckDBPyConnection) -> dict:
    s = exam_extract.mirror_to_jsonl(write_db_conn=con)
    return {"files": s["files"], "examples": s["examples"]}


def run_textbook_units(con: duckdb.DuckDBPyConnection) -> dict:
    ts = textbook_extract.run_all()
    units_jsonl = ROOT / "data/structured/textbook/units_all.jsonl"
    n = 0
    if units_jsonl.exists():
        u_rows = _read_jsonl(units_jsonl)
        con.executemany(
            "INSERT OR REPLACE INTO units VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [(r["version_key"], r["volume_key"], r["unit_number"], r["title_en"],
              None, r["page_start"], r["page_end"], r["extract_method"]) for r in u_rows],
        )
        n = len(u_rows)
    return {"summary": ts, "loaded": n}


def run_vocab(con: duckdb.DuckDBPyConnection) -> dict:
    vs = vocab_extract.run_all()
    vsr = vocab_rj_extract.run_all()
    total = 0
    for jl in [ROOT/"data/structured/textbook/vocab_intro_all.jsonl",
                ROOT/"data/structured/textbook/vocab_intro_renjiao.jsonl"]:
        if not jl.exists(): continue
        rows = _read_jsonl(jl)
        con.executemany(
            "INSERT OR REPLACE INTO unit_vocab_intro VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [(r["version_key"], r["volume_key"], r["unit_number"], r["word"],
              True, r.get("pos"), r.get("zh_def"), r.get("raw_marker")) for r in rows],
        )
        total += len(rows)
    return {"waiyan_rows": vs["rows"], "renjiao_rows": vsr["rows"], "loaded": total}


def run_fix_titles(con: duckdb.DuckDBPyConnection) -> dict:
    return unit_title_fix.fix_titles(con)


def run_sections(con: duckdb.DuckDBPyConnection) -> dict:
    ss = section_extract.run_all(con)
    sec_jsonl = ROOT/"data/structured/textbook/sections_all.jsonl"
    if sec_jsonl.exists():
        rows = _read_jsonl(sec_jsonl)
        con.executemany(
            "INSERT OR REPLACE INTO sections "
            "(version_key, volume_key, unit_number, seq, kind, title, page_start, page_end) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [(r["version_key"], r["volume_key"], r["unit_number"], r["seq"],
              r["kind"], r["title"], r["page_start"], r["page_end"]) for r in rows],
        )
    return ss


def run_section_text(con: duckdb.DuckDBPyConnection) -> dict:
    return st_extract.extract_section_text(con)


def run_phrases(con: duckdb.DuckDBPyConnection) -> dict:
    return ph_extract.extract_phrases(con)


def run_province_refine(con: duckdb.DuckDBPyConnection) -> dict:
    return exam_province.refine_province(con)


def run_section_flags(con: duckdb.DuckDBPyConnection) -> dict:
    return section_flags.flag_sections(con)


def run_derive_edges(con: duckdb.DuckDBPyConnection) -> int:
    """Build word ↔ word derive_from edges (M)."""
    from backend.services import derive
    return derive.build_derive_edges(con)


def run_question_bank(con: duckdb.DuckDBPyConnection) -> dict:
    """题库装载: 真题 + 合成题入 question_bank, 自动打标."""
    from backend.services.question_bank import loader
    real = loader.load_real_questions(con)
    synth = loader.load_synthesized_samples(con, samples_per_type=15)
    return {**real, **synth}


def run_ocr_fix_dict(con: duckdb.DuckDBPyConnection) -> dict:
    """构建 OCR 修复字典 (用户 2026-05-24 上下文修复)."""
    from backend.services import ocr_fix
    return ocr_fix.build_ocr_fix_dict(con)
