#!/usr/bin/env python3
"""Import 2023 XGKII 应用文+续写 from mirrored gzenxx docx.

Local zizzs '.pdf' in this repo is an HTML landing page (no stem). Real question
stems come from gzenxx Word mirror under data/external/exam_sources/third_party_pdfs/.
"""
from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import duckdb

ROOT = Path(__file__).resolve().parents[3]
DOCX = ROOT / "data/external/exam_sources/third_party_pdfs/2023_xgkii_english_gzenxx.docx"
SIDECAR = ROOT / "data/structured/exam_point/writing_2023_xgkii.jsonl"


def _docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
    root = ET.fromstring(xml)
    paras: list[str] = []
    for p in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
        texts = [
            t.text or ""
            for t in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
        ]
        line = "".join(texts).strip()
        if line:
            paras.append(line)
    return "\n".join(paras)


def extract_rows() -> list[dict]:
    if not DOCX.exists():
        raise FileNotFoundError(DOCX)
    text = _docx_text(DOCX)
    m = re.search(
        r"(假定你是李华，外教Ryan[\s\S]*?Yours sincerely\nLi Hua)",
        text,
    )
    if not m:
        raise ValueError("2023 applied writing stem not found in docx")
    applied = re.sub(r"_{10,}", "", m.group(1))
    applied = re.sub(r"\n{3,}", "\n\n", applied).strip()
    applied = "（满分 15 分）\n66. " + applied

    m3 = re.search(
        r"(67\.\s*阅读下面材料[\s\S]*?I went to my teacher.?s office after the award presentation\.)",
        text,
    )
    if not m3:
        raise ValueError("2023 continuation stem not found in docx")
    cont = re.split(r"【答案】", m3.group(1))[0]
    cont = re.sub(r"_{10,}", "", cont)
    cont = re.sub(r"\n{3,}", "\n\n", cont).strip()
    cont = "（满分 25 分）\n" + cont

    return [
        {
            "question_id": "docx/2023/xgkii/应用文写作/66",
            "year": 2023,
            "province": "辽宁 (新课标 II 卷, 2021+)",
            "paper_type": "新课标 II 卷",
            "question_type": "应用文写作",
            "raw_question": applied,
            "answer": "",
            "analysis": "",
            "source_file": DOCX.name,
            "source_index": 66,
            "source_repo": "third_party_docx_gzenxx",
            "provenance": "gzenxx_docx_extract",
        },
        {
            "question_id": "docx/2023/xgkii/续写/67",
            "year": 2023,
            "province": "辽宁 (新课标 II 卷, 2021+)",
            "paper_type": "新课标 II 卷",
            "question_type": "续写",
            "raw_question": cont,
            "answer": "",
            "analysis": "",
            "source_file": DOCX.name,
            "source_index": 67,
            "source_repo": "third_party_docx_gzenxx",
            "provenance": "gzenxx_docx_extract",
        },
    ]


def write_sidecar(rows: list[dict] | None = None) -> Path:
    rows = rows or extract_rows()
    SIDECAR.parent.mkdir(parents=True, exist_ok=True)
    SIDECAR.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    return SIDECAR


def import_writing_2023(con: duckdb.DuckDBPyConnection | None = None) -> dict:
    """Upsert 2023 应用文+续写 into exam_questions_all + question nodes."""
    rows = extract_rows()
    write_sidecar(rows)
    own = con is None
    if own:
        con = duckdb.connect(str(ROOT / "data/db/gaozhong.duckdb"))
    assert con is not None
    n = 0
    for r in rows:
        con.execute("DELETE FROM exam_questions_all WHERE question_id=?", [r["question_id"]])
        con.execute(
            "INSERT INTO exam_questions_all ("
            "question_id, year, province, paper_type, question_type, "
            "raw_question, answer, analysis, source_file, source_index, source_repo"
            ") VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [
                r["question_id"],
                r["year"],
                r["province"],
                r["paper_type"],
                r["question_type"],
                r["raw_question"],
                r["answer"],
                r["analysis"],
                r["source_file"],
                r["source_index"],
                r["source_repo"],
            ],
        )
        cid = f"question:{r['question_id']}"
        if not con.execute("SELECT 1 FROM nodes WHERE concept_id=?", [cid]).fetchone():
            con.execute(
                "INSERT INTO nodes VALUES (?,?,?,?)",
                [
                    cid,
                    "question",
                    f"{r['year']} {r['question_type']}",
                    json.dumps(
                        {"year": r["year"], "province": "辽宁", "type": r["question_type"]},
                        ensure_ascii=False,
                    ),
                ],
            )
        n += 1
    if own:
        con.close()
    return {"n_upserted": n, "sidecar": str(SIDECAR.relative_to(ROOT)), "source": DOCX.name}


if __name__ == "__main__":
    print(import_writing_2023())
