#!/usr/bin/env python3
"""Harvest 2022–2025 XGKII listening stems + import into exam_questions_all / question_bank.

Sources (local-first; answers ≥1 published key, stems from paper/export):
  2022: 133ku/zxxk-style parsed stems + jczhijia key CBBCA…ABABC
  2023: gzenxx.docx stems + scribd analysis keys
  2024: local PDF text + gaokao_export answers
  2025: newdu stem txt (stems+key CBABC…)

Does NOT wipe question_bank. Idempotent on origin_ref / question_id.
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import duckdb

from backend.services.question_bank.loader import autotag, insert_question
from backend.services.trend import scope

OUT = ROOT / "data/external/exam_sources/listening_stems"
NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
PROVINCE = scope.LIAONING_XGKII_2021
PAPER = scope.PAPER_XGKII
REPO = "listening_stems_xgkii"


def _docx_text(path: Path) -> str:
    root = ET.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
    lines = []
    for p in root.iter(NS + "p"):
        line = "".join(t.text or "" for t in p.iter(NS + "t")).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def _normalize_option_layout(text: str) -> str:
    """Fix packed options like ``A. Foo.B. Bar`` / ``A.Foo``."""
    text = text.replace("\u3000", " ")
    text = text.replace("【此处可播放相关音频，请去附件查看】", "")
    text = text.replace("\f", "\n")
    text = re.sub(r"第\d+页/共\d+页", "", text)
    # space before letter-dot when glued after prior option period
    text = re.sub(r"(?<=\S)([ABC])[\.、．]", r" \1. ", text)
    # space after A./B./C. when missing
    text = re.sub(r"([ABC])[\.、．](?=\S)", r"\1. ", text)
    return text


def _parse_qs(text: str, max_q: int = 20) -> dict[int, dict]:
    text = _normalize_option_layout(text)
    items: dict[int, dict] = {}
    # Line-anchored numbers only — avoid splitting on times like "5:30."
    for m in re.finditer(
        r"^[ \t]*(\d{1,2})[\.．]\s*(.+?)(?=^[ \t]*(?:\d{1,2})[\.．]\s*|\Z)",
        text,
        re.M | re.S,
    ):
        n = int(m.group(1))
        if not 1 <= n <= max_q:
            continue
        body = re.split(
            r"听下面|第二节|第一部分|重难点|【答案】|【解析】|文本解密|参考答案|解析：",
            m.group(2),
        )[0]
        # Stem = English question up to first '?'; options only after that
        qm = re.search(r"([A-Za-z][^?]{5,200}\?)", body)
        if not qm:
            continue
        stem = re.sub(r"\s+", " ", qm.group(1)).strip()
        after = body[qm.end() :]
        # Drop Chinese instruction residue before real options
        after = re.split(r"(?:三个选项|选出最佳|听每段|听完后)", after, maxsplit=1)[-1]
        opts: dict[str, str] = {}
        for om in re.finditer(
            r"([ABC])[\.、．]\s*(.+?)(?=\s+[ABC][\.、．]|\s*$)",
            after,
            re.S,
        ):
            val = re.sub(r"\s+", " ", om.group(2)).strip(" .")
            # reject Chinese-only garbage options
            if not re.search(r"[A-Za-z]", val):
                continue
            opts[om.group(1)] = val
        if len(stem) < 8:
            continue
        items[n] = {"n": n, "stem": stem, "options": opts}
    return items


def _require_full_abc(year: int, rows: list[dict]) -> None:
    bad = [
        r["n"]
        for r in rows
        if set((r.get("options") or {}).keys()) != {"A", "B", "C"}
        or any(not (r["options"][k] or "").strip() for k in "ABC")
    ]
    if bad:
        raise RuntimeError(f"{year} missing full ABC options on Q{bad}")


def _fmt_raw(n: int, stem: str, options: dict[str, str]) -> str:
    parts = [f"{n}. {stem}"]
    for k in "ABC":
        if k in options:
            parts.append(f"{k}. {options[k]}")
    return " ".join(parts)


def _expand_key(blocks: list[str]) -> dict[int, str]:
    """['CBABC','BCBAB',...] → {1:'C',...}."""
    s = "".join(blocks)
    if len(s) != 20 or any(ch not in "ABC" for ch in s):
        raise ValueError(f"bad key blocks {blocks!r} -> {s!r}")
    return {i + 1: s[i] for i in range(20)}


def harvest_2022() -> list[dict]:
    # Stems+options from zxxk published paper (I&II shared listening).
    # Key cross-checked: jczhijia CBBCA/ABBCC/BAACC/ABABC == zxxk 【答案】 blocks.
    stems = {
        1: (
            "What will the speakers do next?",
            {"A": "Check the map.", "B": "Leave the restaurant.", "C": "Park the car."},
        ),
        2: (
            "Where are the speakers?",
            {"A": "At a bus stop.", "B": "At home.", "C": "At the airport."},
        ),
        3: (
            "What did the speakers do last week?",
            {
                "A": "They had a celebration dinner.",
                "B": "They went to see a newborn baby.",
                "C": "They sent a mail to their neighbors.",
            },
        ),
        4: (
            "Why does the man make the phone call?",
            {
                "A": "To cancel a weekend trip.",
                "B": "To make an appointment.",
                "C": "To get some information.",
            },
        ),
        5: (
            "What does the man probably want to do?",
            {
                "A": "Do some exercise.",
                "B": "Get an extra key.",
                "C": "Order room service.",
            },
        ),
        6: (
            "Why does the woman come to the man?",
            {
                "A": "To ask for permission.",
                "B": "To extend an invitation.",
                "C": "To express thanks.",
            },
        ),
        7: (
            "When are the students going to the museum?",
            {"A": "On Friday.", "B": "On Saturday.", "C": "On Sunday."},
        ),
        8: (
            "What are the speakers talking about?",
            {
                "A": "Buying groceries.",
                "B": "Choosing gifts.",
                "C": "Seeing friends.",
            },
        ),
        9: (
            "Who is Clara?",
            {
                "A": "The man's wife.",
                "B": "The man's sister.",
                "C": "The man's daughter.",
            },
        ),
        10: (
            "How much did the man spend on the city passes?",
            {"A": "$36.", "B": "$50.", "C": "$150."},
        ),
        11: (
            "Why did Tracy bring dogs to the children?",
            {
                "A": "To teach them to love animals.",
                "B": "To help them gain confidence.",
                "C": "To protect them from dangers.",
            },
        ),
        12: (
            "What is Kevin's concern about the dog?",
            {
                "A": "They may misbehave.",
                "B": "They may get hurt.",
                "C": "They may carry diseases.",
            },
        ),
        13: (
            "What will Helen do tomorrow morning?",
            {
                "A": "Give a talk.",
                "B": "Meet the children.",
                "C": "Take some photos.",
            },
        ),
        14: (
            "What is the man doing?",
            {
                "A": "Attending a lecture.",
                "B": "Hosting a workshop.",
                "C": "Conducting an interview.",
            },
        ),
        15: (
            "Why is Emily doing unpaid work in the new season of the show?",
            {
                "A": "To follow the latest trend.",
                "B": "To help raise the crew's pay.",
                "C": "To support the post-production.",
            },
        ),
        16: (
            "What enables Emily to try different things in her field?",
            {
                "A": "Her college education.",
                "B": "Her teaching experience.",
                "C": "Her family tradition.",
            },
        ),
        17: (
            "What does Emily think of her work at the Film Centre?",
            {"A": "Boring.", "B": "Rewarding.", "C": "Demanding."},
        ),
        18: (
            "Who is the speaker talking to?",
            {
                "A": "Sports club members.",
                "B": "International tourists.",
                "C": "University students.",
            },
        ),
        19: (
            "Where did Emma work for a rugby team?",
            {
                "A": "In Manchester.",
                "B": "In Dublin.",
                "C": "In Vancouver.",
            },
        ),
        20: (
            "What can be a challenge to Emma's work?",
            {
                "A": "Competition in the health care industry.",
                "B": "Discrimination against female scientists.",
                "C": "Influence of misinformation on the public.",
            },
        ),
    }
    # jczhijia + zxxk 【答案】 (shared I&II)
    key = _expand_key(["CBBCA", "ABBCC", "BAACC", "ABABC"])
    assert key == {
        1: "C", 2: "B", 3: "B", 4: "C", 5: "A",
        6: "A", 7: "B", 8: "B", 9: "C", 10: "C",
        11: "B", 12: "A", 13: "A", 14: "C", 15: "C",
        16: "A", 17: "B", 18: "A", 19: "B", 20: "C",
    }
    rows = []
    for n, (stem, opts) in stems.items():
        rows.append(
            {
                "year": 2022,
                "n": n,
                "stem": stem,
                "options": opts,
                "answer": key[n],
                "source": "zxxk_stems;jczhijia+zxxk_key",
            }
        )
    _require_full_abc(2022, rows)
    return rows


def harvest_2023() -> list[dict]:
    docx = ROOT / "data/external/exam_sources/third_party_pdfs/2023_xgkii_english_gzenxx.docx"
    t = _docx_text(docx)
    i = t.find("What will Jack probably do this weekend?")
    i = t.rfind("1.", 0, i)
    j = t.find("第二部分", i)
    qs = _parse_qs(t[i:j])
    # scribd analysis keys for XGK I/II shared listening
    key = {
        1: "C", 2: "A", 3: "B", 4: "B", 5: "C",
        6: "C", 7: "B", 8: "A", 9: "B",
        10: "C", 11: "A", 12: "C", 13: "A",
        14: "B", 15: "A", 16: "C", 17: "C",
        18: "A", 19: "B", 20: "A",
    }
    if len(qs) != 20:
        raise RuntimeError(f"2023 expected 20 stems, got {sorted(qs)}")
    rows = [
        {
            "year": 2023,
            "n": n,
            "stem": qs[n]["stem"],
            "options": qs[n]["options"],
            "answer": key[n],
            "source": "gzenxx_docx;scribd_analysis_key",
        }
        for n in range(1, 21)
    ]
    _require_full_abc(2023, rows)
    return rows


def harvest_2024() -> list[dict]:
    pdf_txt = Path("/tmp/2024_xgkii.txt")
    if not pdf_txt.exists():
        import subprocess

        subprocess.run(
            [
                "pdftotext",
                "-layout",
                str(ROOT / "data/external/exam_sources/local_pdfs/2024_xgkii_english.pdf"),
                str(pdf_txt),
            ],
            check=True,
        )
    t = pdf_txt.read_text(encoding="utf-8", errors="replace")
    i = t.find("1. What did the woman do yesterday evening?")
    if i < 0:
        raise RuntimeError("2024 listening Q1 not found in PDF text")
    j = t.find("参考答案", i)
    if j < 0:
        j = t.find("第二部分", i)
    qs = _parse_qs(t[i:j])
    export: dict[int, dict] = {}
    for line in (ROOT / "data/gaokao_export_2021_2025.jsonl").open(encoding="utf-8"):
        o = json.loads(line)
        if o.get("year") == 2024 and "听" in str(o.get("question_type")):
            export[int(o["question_number"])] = o
    rows = []
    for n in range(1, 21):
        if n not in qs or set(qs[n]["options"]) != {"A", "B", "C"}:
            raise RuntimeError(f"2024 Q{n} incomplete parse: {qs.get(n)}")
        ans = (export[n].get("answer") or "").strip()
        if ans not in "ABC":
            raise RuntimeError(f"2024 Q{n} bad answer {ans!r}")
        rows.append(
            {
                "year": 2024,
                "n": n,
                "stem": qs[n]["stem"],
                "options": qs[n]["options"],
                "answer": ans,
                "source": "local_pdf+gaokao_export",
            }
        )
    _require_full_abc(2024, rows)
    return rows


def harvest_2025() -> list[dict]:
    # Stem txt has Q1–20 + key; Q4 option B is blank in stem → patch from analysis.
    analysis = (
        ROOT
        / "data/external/exam_sources/listening_transcripts/2025_xgkii_newdu_listening_analysis.txt"
    )
    stem_path = (
        ROOT
        / "data/external/exam_sources/listening_transcripts/2025_xgkii_newdu_listening_stem.txt"
    )
    t = stem_path.read_text(encoding="utf-8")
    m = re.search(r"1\.How will the woman.*?(?=1—5\s+[A-C]{5})", t, re.S)
    if not m:
        raise RuntimeError("2025 stem block not found")
    block = re.sub(r"(?m)^(\d{1,2})\.(?=\S)", r"\1. ", m.group(0))
    qs = _parse_qs(block)
    if 4 in qs and "B" not in qs[4]["options"] and analysis.exists():
        am = re.search(
            r"4\.What is the man's major\?\s*"
            r"A\.Psychology\.\s*B\.Biology\.\s*C\.English\.",
            analysis.read_text(encoding="utf-8"),
            re.S,
        )
        if not am:
            raise RuntimeError("2025 Q4 ABC not found in analysis for B-patch")
        qs[4]["options"] = {
            "A": "Psychology.",
            "B": "Biology.",
            "C": "English.",
        }
    key_m = re.search(
        r"1—5\s+([A-C]{5})\s+6—10\s+([A-C]{5})\s+11—15\s+([A-C]{5})\s+16—20\s+([A-C]{5})",
        t,
    )
    if not key_m:
        raise RuntimeError("2025 answer key line not found")
    key = _expand_key(list(key_m.groups()))
    if len(qs) != 20:
        raise RuntimeError(f"2025 expected 20, got {sorted(qs)}")
    rows = [
        {
            "year": 2025,
            "n": n,
            "stem": qs[n]["stem"],
            "options": qs[n]["options"],
            "answer": key[n],
            "source": "newdu_listening_stem+analysis_Q4B",
        }
        for n in range(1, 21)
    ]
    _require_full_abc(2025, rows)
    return rows


def write_jsonl(year: int, rows: list[dict]) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{year}_xgkii_listening_stems.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return path


def import_rows(rows: list[dict]) -> dict:
    con = duckdb.connect(str(ROOT / "data/db/gaozhong.duckdb"))
    cefr = {r[0] for r in con.execute("SELECT word FROM cefr_vocab").fetchall()}
    inserted_eq = 0
    inserted_qb = 0
    try:
        for r in rows:
            year, n = r["year"], r["n"]
            qid = f"listening/{year}/xgkii/{n}"
            raw = _fmt_raw(n, r["stem"], r.get("options") or {})
            src = f"listening_stems/{year}"
            con.execute(
                "DELETE FROM exam_questions_all WHERE question_id = ?", [qid]
            )
            con.execute(
                "INSERT INTO exam_questions_all "
                "(question_id, year, province, paper_type, question_type, "
                " raw_question, answer, analysis, source_file, source_index, "
                " source_repo, exam_type) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                [
                    qid,
                    year,
                    PROVINCE,
                    PAPER,
                    "听力",
                    raw,
                    r["answer"],
                    f"listening stem import; source={r.get('source')}",
                    src,
                    n,
                    REPO,
                    "高考",
                ],
            )
            inserted_eq += 1
            # question_bank: delete existing same origin_ref then insert
            old = con.execute(
                "SELECT qb_id FROM question_bank WHERE origin_ref = ?", [qid]
            ).fetchall()
            for (qb_id,) in old:
                con.execute("DELETE FROM question_tags WHERE qb_id = ?", [qb_id])
                con.execute("DELETE FROM question_bank WHERE qb_id = ?", [qb_id])
            qb_id = insert_question(
                con,
                "real",
                qid,
                "听力",
                raw,
                json.dumps(r.get("options") or {}, ensure_ascii=False),
                r["answer"],
                f"source={r.get('source')}",
            )
            autotag(con, qb_id, raw, year, "听力", cefr, origin_ref=qid)
            inserted_qb += 1
    finally:
        con.close()
    return {"exam_questions": inserted_eq, "question_bank": inserted_qb}


def main() -> int:
    all_rows: list[dict] = []
    for harvester in (harvest_2022, harvest_2023, harvest_2024, harvest_2025):
        rows = harvester()
        assert len(rows) == 20, harvester.__name__
        write_jsonl(rows[0]["year"], rows)
        all_rows.extend(rows)
        print(f"OK harvest {rows[0]['year']}: 20 stems -> {OUT}/{rows[0]['year']}_xgkii_listening_stems.jsonl")
    stats = import_rows(all_rows)
    print("import", stats)
    # recount
    con = duckdb.connect(str(ROOT / "data/db/gaozhong.duckdb"), read_only=True)
    print(
        "listening by year",
        con.execute(
            "SELECT year, count(*) FROM exam_questions WHERE question_type='听力' GROUP BY 1 ORDER BY 1"
        ).fetchall(),
    )
    print(
        "qb listening",
        con.execute(
            "SELECT count(*) FROM question_bank WHERE question_type='听力'"
        ).fetchone()[0],
    )
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
