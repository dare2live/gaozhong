"""抽 section page 范围内的 raw_text 入 section_text 表 (K).

为后续:
  - phrase 抽 (E): grep section_text 找短语 / 句型
  - LLM 抽 (S4): 送 section_text 给 LLM 抽 narrative / 功能表达
"""
from __future__ import annotations

from pathlib import Path

import duckdb
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent.parent.parent
TEXTBOOK_DIR = ROOT / "data" / "textbooks"


# 坑(2026-07-04 教研组验收发现): section 边界只记到"页"粒度, 当两个真实 section (如
# "Presenting ideas"/"Reflection") 印在同一物理页时, 二者会拿到完全相同的整页 raw_text ——
# 教师点开"Reflection"看到的其实是"Presenting ideas"的内容。外研版必修 1-3 册(辽宁 10 市
# 在用的核心/必修卷, 全 18 个单元)该页固定含 "After completing this unit, I can rate my
# performance" 这句自评量表的引导语, 经 18/18 单元逐一核验 100% 命中, 可作可靠切分点。
# 选修册(xuanze)的 Reflection 内容按单元话题变化, 无固定引导语, 找不到锚点时保留原整页
# (不臆造切分点, 见 mio "safe merge" 原则: 只在能验证的地方切, 不确定就不切)。
_REFLECTION_CONTENT_MARKER = "After completing this unit, I can rate my"


def _page_text(reader: PdfReader, pi: int) -> str:
    try:
        return reader.pages[pi].extract_text() or ""
    except Exception:
        return ""


def _before_reflection_marker(page_text: str) -> str:
    """本 section 的末页与下一节 Reflection 共享; 找到锚点(bixiu 18/18 验证恒在)才切,
    否则保留整页(不确定就不切, 允许与下一节重叠优于错误截断)。"""
    idx = page_text.find(_REFLECTION_CONTENT_MARKER)
    return page_text[:idx] if idx >= 0 else page_text


def _from_reflection_marker(page_text: str) -> str:
    """本 section 就是 Reflection, 起始页与上一节共享; 从锚点起才是真内容。"""
    idx = page_text.find(_REFLECTION_CONTENT_MARKER)
    return page_text[idx:] if idx >= 0 else page_text


def _same_unit(row, ver: str, vol: str, un: int) -> bool:
    return row is not None and row[0] == ver and row[1] == vol and row[2] == un


def _row_text(reader: PdfReader, row: tuple, prev_row: tuple | None, next_row: tuple | None) -> str:
    ver, vol, un, _seq, ps, pe, title = row
    shares_start_with_prev = _same_unit(prev_row, ver, vol, un) and prev_row[5] == ps
    shares_end_with_reflection = (
        _same_unit(next_row, ver, vol, un) and next_row[4] == pe and next_row[6] == "Reflection")
    chunks: list[str] = []
    for pi in range(max(0, ps - 1), min(pe, len(reader.pages))):
        page_no = pi + 1
        page_text = _page_text(reader, pi)
        if page_no == pe and shares_end_with_reflection:
            page_text = _before_reflection_marker(page_text)
        elif page_no == ps and shares_start_with_prev and title == "Reflection":
            page_text = _from_reflection_marker(page_text)
        chunks.append(page_text)
    return "\n".join(chunks).strip()


def extract_section_text(con: duckdb.DuckDBPyConnection) -> dict:
    rows = con.execute("""
        SELECT version_key, volume_key, unit_number, seq, page_start, page_end, title
        FROM sections WHERE page_start IS NOT NULL AND page_end IS NOT NULL
        ORDER BY version_key, volume_key, unit_number, seq
    """).fetchall()
    pdf_cache: dict[str, PdfReader] = {}
    inserted = 0
    con.execute("DELETE FROM section_text")
    n = len(rows)
    for i, (ver, vol, un, seq, ps, pe, title) in enumerate(rows):
        key = f"{ver}/{vol}"
        if key not in pdf_cache:
            p = TEXTBOOK_DIR / ver / f"{vol}.pdf"
            if not p.exists():
                continue
            try:
                pdf_cache[key] = PdfReader(p)
            except Exception:
                continue
        prev_row = rows[i - 1] if i > 0 else None
        next_row = rows[i + 1] if i + 1 < n else None
        text = _row_text(pdf_cache[key], (ver, vol, un, seq, ps, pe, title), prev_row, next_row)
        if not text:
            continue
        # 不截断 (issue #7): DuckDB VARCHAR 无长度上限, n_chars 已存 len(text) 真值;
        # 旧 text[:20000] 致 raw_text 被截 ≠ n_chars (D0 违反). 单元边界已收口 (issue #9) → 无 back-matter 污染需靠截断挡。
        con.execute(
            "INSERT INTO section_text VALUES (?, ?, ?, ?, ?, ?)",
            [ver, vol, un, seq, text, len(text)],
        )
        inserted += 1
    return {"sections_scanned": len(rows), "rows_inserted": inserted}
