#!/usr/bin/env python3
"""解析 2024/2025 高考英语 PDF → 入 exam_questions 表.

从 gaokao 项目的 PDF 提取阅读/完形/语法填空/写作题, 结构化入库.
不处理听力 (PDF 无音频).

2026-06-15 模块化 (M6): PDF→文本 + 题型分段下沉到 extract 层
  backend/services/data_sources/extract/pdf.py
  (extract_text / parse_exam_sections / PdfUnreadableError, 与本文件原逻辑字节等价).
本脚本只保留"入库 + 入库后交叉核对"编排.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import duckdb

from backend.services.contracts import load_import_policy
from backend.services.data_sources.extract.pdf import (
    PdfUnreadableError,
    extract_text,
    has_post_exam_contamination,
    parse_exam_sections,
)
from backend.services.data_sources.registry import load_registry

# 真题导入数据化 (架构契约 direct_exam_questions_writer: exam imports 必须 registry/import-policy 驱动):
#   - backend/config/sources.yaml         PDF 路径/sha256 真相源 (经 registry.load_registry 读, 不硬编码路径 §3.5)
#   - backend/config/import_policies.yaml  污染/缺题干 block_if 安全门 (经 load_import_policy 读, 入库前施加)
DB_PATH = ROOT / "data" / "db" / "gaozhong.duckdb"
# 答案真相源 (gaokao 收口 sub-question, 含 2024/2025 答案键); PDF 给全文, jsonl 给答案
GAOKAO_SUBQ = ROOT / "data" / "structured" / "exam_subquestions" / "xgkii_2021_2025_subquestions.jsonl"
LOCAL_PDF_FAMILY = "exam_truth_source_local_pdf"   # sources.yaml 里本地 PDF 真题源家族
IMPORT_POLICY = "exam_truth_source_import"          # import_policies.yaml 里适用的策略名


def _local_pdf_sources() -> list[tuple]:
    """从 sources.yaml registry 派生本地 PDF 真题源 (year, paper_type, pdf_path); 不硬编码路径 (§3.5).

    legacy passage-level 源 (status=legacy_imported, 非 import_ready): 不主张完整 item-level D0 契约,
    但路径/sha256 真相源走 registry, 与 fetcher/acquire 同一 sources.yaml 单点.
    """
    out = []
    for s in load_registry().list_sources():
        if s.family != LOCAL_PDF_FAMILY or s.year is None:
            continue
        pdf = next((a.local_path for a in s.attachments if a.kind == "pdf"), None)
        if pdf is not None:
            out.append((s.year, s.paper_type or "新课标 II 卷", pdf))
    return sorted(out, key=lambda t: t[0])


def _policy_block_if() -> list[str]:
    """读 import_policies.yaml 适用策略的 block_if (污染/缺题干等硬阻断项), 入库前施加普适安全门."""
    return load_import_policy(IMPORT_POLICY).get("block_if") or []


def _policy_check(sections: list[dict], year: int, block_if: list[str]) -> bool:
    """入库前按 import_policies block_if 施加普适安全门 (污染/缺题干); 命中示警返 False (§1.5 不静默)."""
    ok = True
    if "answer_section_contamination" in block_if:
        bad = [s["question_id"] for s in sections if has_post_exam_contamination(s["raw_question"])]
        if bad:
            print(f"    ⚠ policy[{year}] answer_section_contamination: {bad}")
            ok = False
    if "missing_stem_preview" in block_if:
        empty = [s["question_id"] for s in sections if len((s["raw_question"] or "").strip()) < 50]
        if empty:
            print(f"    ⚠ policy[{year}] missing_stem_preview: {empty}")
            ok = False
    return ok

# jsonl question_type → (pdf qtype, pdf source_index/qnum); 阅读按 passage 映 1-4
_QT_MAP = {
    "seven_choose_five": ("完形填空(七选五/语篇)", 36),
    "cloze_fill_in_blanks": ("完形填空", 41),
    "grammar_fill": ("语法填空", 56),
}
_PASSAGE_QNUM = {"A": 1, "B": 2, "C": 3, "D": 4}


def _row_key(jqt, r) -> tuple | None:
    """jsonl question_type → (pdf_qtype, qnum) 聚合键; 阅读按 passage_label 映 1-4, 不匹配 None."""
    if jqt == "reading_comprehension":
        qn = _PASSAGE_QNUM.get(r.get("passage_label"))
        return ("阅读理解", qn) if qn else None
    return _QT_MAP.get(jqt)


def _row_contrib(r) -> tuple:
    """单行 → (排序号, 答案串). 源数据异构: list 型(2024整段)保序拼并用 -1 标识整段串."""
    ans = r["answer"]
    if isinstance(ans, list):
        return (-1, " ".join(str(x) for x in ans))
    try:
        num = int(r.get("question_number") or 0)
    except (TypeError, ValueError):
        num = 0
    return (num, str(ans))


def _fmt_group(v: list) -> str:
    """组贡献 → 答案串: 逐题行按题号排 '1.C 2.B'; 整段 list 串(num=-1)直接用."""
    if len(v) == 1 and v[0][0] == -1:
        return v[0][1]
    return " ".join(f"{n}.{a}" for n, a in sorted(v))


def _jsonl_answer_map(year: int) -> dict:
    """从 gaokao jsonl 聚合该年答案: (pdf_qtype, qnum) → 答案串 (2025逐题/2024整段两形态统一)."""
    import json
    from collections import defaultdict
    if not GAOKAO_SUBQ.exists():
        return {}
    groups: dict = defaultdict(list)
    for line in GAOKAO_SUBQ.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if str(r.get("year")) != str(year) or not r.get("answer"):
            continue
        key = _row_key(r.get("question_type"), r)
        if key:
            groups[key].append(_row_contrib(r))
    return {k: _fmt_group(v) for k, v in groups.items()}


def _enrich_answers(sections: list[dict], year: int) -> list[dict]:
    """用 gaokao jsonl 答案真相源填 PDF section 的 answer (原为空; D0 缺陷修复)."""
    amap = _jsonl_answer_map(year)
    for s in sections:
        a = amap.get((s["question_type"], s["source_index"]))
        if a:
            s["answer"] = a
    return sections


def import_to_db(questions: list[dict], con) -> int:
    """用**传入的写连接**入库 + 挂 question/exam_year 节点边.

    单一写连接纪律 (DuckDB 单写者): 不自开第二个写连接, 由调用方 (init_db / main) 统一持有,
    否则与 init_db 的写连接锁冲突 (Layer 4g subprocess 崩 → local_pdf 行历来靠 out-of-band 手工补).
    """
    existing = {r[0] for r in con.execute("SELECT question_id FROM exam_questions").fetchall()}
    n = 0
    for q in questions:
        if q["question_id"] in existing:
            continue
        con.execute(
            "INSERT INTO exam_questions_all (question_id, year, province, paper_type, question_type, "
            "raw_question, answer, analysis, source_file, source_index, source_repo) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",   # exam_type 默认'高考'
            [q["question_id"], q["year"], q["province"], q["paper_type"],
             q["question_type"], q["raw_question"], q["answer"], q["analysis"],
             q["source_file"], q["source_index"], q["source_repo"]],
        )
        cid = f"question:{q['question_id']}"
        if not con.execute("SELECT 1 FROM nodes WHERE concept_id=?", [cid]).fetchone():
            con.execute("INSERT INTO nodes VALUES (?,?,?,NULL)", [cid, "question", q["question_id"]])
        year_node = f"exam_year:{q['year']}"
        if not con.execute("SELECT 1 FROM nodes WHERE concept_id=?", [year_node]).fetchone():
            con.execute("INSERT INTO nodes VALUES (?,?,?,NULL)", [year_node, "exam_year", str(q["year"])])
        if not con.execute("SELECT 1 FROM edges WHERE src_id=? AND dst_id=?", [cid, year_node]).fetchone():
            con.execute("INSERT INTO edges (src_id, dst_id, relation, weight, evidence_json) VALUES (?,?,?,?,?)",
                        [cid, year_node, "in_year", 1.0, '{"source":"pdf_import"}'])
        n += 1
    return n


def _post_import_verify(year: int, con=None) -> bool:
    """入库后立即 cross-verify — FAIL 则示警 (宪法 §8.3 程序化执行).

    con 传入时 verify_year 复用该连接 (无第二连接, 适配 init_db in-process 调用).
    """
    try:
        from scripts.tools.audit.cross_verify_pdf import verify_year
        result = verify_year(year, con=con)
        status = result.get("overall", result.get("status", "skip"))
        n_fail = result.get("summary", {}).get("fail", 0)
        print(f"    cross-verify {year}: {status} (fail={n_fail})")
        return status != "FAIL"
    except Exception as e:
        print(f"    cross-verify skip: {e}")
        return True


def import_pdfs(con) -> dict:
    """编排 PDF→入库 (用传入写连接), 返回 {total, by_year, verify}. init_db Layer 4g 调用.

    PDF→文本→分段 走 extract 层 (pdf.extract_text / parse_exam_sections); 本函数只编排 + 入库 + 核对.
    """
    total = 0
    by_year: dict[int, int] = {}
    verify_ok = True
    block_if = _policy_block_if()
    for year, _paper, pdf_path in _local_pdf_sources():
        if not pdf_path.exists():
            print(f"  SKIP {year}: {pdf_path} not found")
            continue
        try:
            text = extract_text(pdf_path)
        except PdfUnreadableError as e:
            # 非有效 PDF (HTML 伪装/损坏) → 诚实跳过, 不静默吞 (§1.5), 不崩流程
            print(f"  SKIP {year}: {e}")
            continue
        qs = _enrich_answers(parse_exam_sections(text, year), year)
        if not _policy_check(qs, year, block_if):
            verify_ok = False
        n = import_to_db(qs, con)
        total += n
        by_year[year] = n
        print(f"  {year}: extracted {len(qs)}, imported {n} new (skipped {len(qs) - n} existing)")
        if not _post_import_verify(year, con=con):
            verify_ok = False
            print(f"    ❌ cross-verify FAIL for {year} — 数据可能不一致, 请检查")
    return {"total": total, "by_year": by_year, "verify_ok": verify_ok}


def main():
    con = duckdb.connect(str(DB_PATH))
    try:
        result = import_pdfs(con)
        print(f"\nTotal imported: {result['total']}")
        for r in con.execute("SELECT year, COUNT(*) FROM exam_questions WHERE year >= 2024 GROUP BY 1 ORDER BY 1").fetchall():
            print(f"  DB year {r[0]}: {r[1]} questions")
    finally:
        con.close()


if __name__ == "__main__":
    main()
