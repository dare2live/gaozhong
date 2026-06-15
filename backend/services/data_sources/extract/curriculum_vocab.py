"""通用课标词汇表提取工具 — 英语课标 PDF 附录 2 词汇表 → 单词 + 层级.

复现并模块化 official_curriculum_vocab.jsonl 的生成逻辑 (commit 27cb04b 后落地):
从《普通高中英语课程标准 (2017 年版 2020 年修订)》附录 2 词汇表抽词 + 星标层级.

层级铁律 (星标在行尾, 紧跟主词或括号变体之后):
  - 无星  → 必修   (level 0)
  - `*`   → 选修I  (level 1)
  - `**`  → 选修II (level 2)

词汇表区定位 (不 hardcode 页码, 按内容找, PIT 安全):
  - 起始页: 同一页含 'abandon' 且 'ability' (词汇表 A 段起点)
  - 结束页: 起始页之后首个含 '语法项目一览' 的页 (附录 3 起点, exclusive)

主词规则: 一行先剥星标, 再按 括号 `(` / 斜杠 `/` / 空格切分取第一个 token,
小写, 仅保留纯字母 2-20 长度 (滤掉 'a' 1 字母 / 中文说明 / 页码 / 噪音).

公开 API:
  extract_curriculum_vocab(pdf_path=None) -> list[dict]
    [{word, level('必修'/'选修I'/'选修II'), source}]

只读真相源 (课标 PDF), 不写表; 落库由上层 services / 脚本负责 (Rule 1 单一计算点).
"""
from __future__ import annotations

import glob
import re
from pathlib import Path

from pypdf import PdfReader

# 默认 glob: 辽宁主用全国课标, 单一英语课标 PDF
DEFAULT_PDF_GLOB = "data/curriculum/national/*/*英语*.pdf"
SOURCE_TAG = "课标2017rev2020 附录2 词汇表"

# 星标数 → 层级 (0=必修, 1=选修I, 2=选修II)
LEVEL_BY_STARS = {0: "必修", 1: "选修I", 2: "选修II"}

# 行尾星标 (主词/括号变体之后的 1~2 个 *)
_TRAILING_STARS_RE = re.compile(r"(\*{1,2})\s*$")
# 主词: 纯字母 2-20 (剥星 + 切分后校验)
_MAIN_WORD_RE = re.compile(r"[a-z]{2,20}$")
# 主词切分点: 第一个 括号 / 斜杠 / 空格
_SPLIT_RE = re.compile(r"[(/ ]")


def _project_root() -> Path:
    # .../backend/services/data_sources/extract/curriculum_vocab.py → 上 5 级
    return Path(__file__).resolve().parents[4]


def _resolve_pdf(pdf_path: str | Path | None) -> Path:
    """显式解析 PDF 路径; 默认走 glob. 找不到/多于一个 → 显式报错 (不静默)."""
    if pdf_path is not None:
        p = Path(pdf_path)
        if not p.exists():
            raise FileNotFoundError(f"课标 PDF 不存在: {p}")
        return p
    root = _project_root()
    matches = sorted(glob.glob(str(root / DEFAULT_PDF_GLOB)))
    if not matches:
        raise FileNotFoundError(
            f"默认 glob 未命中课标 PDF: {root / DEFAULT_PDF_GLOB}"
        )
    if len(matches) > 1:
        raise ValueError(
            f"默认 glob 命中多个 PDF, 请显式传 pdf_path: {matches}"
        )
    return Path(matches[0])


def _page_text(reader: PdfReader, page_index: int) -> str:
    return reader.pages[page_index].extract_text() or ""


def _find_vocab_span(reader: PdfReader) -> tuple[int, int]:
    """定位词汇表页区间 [start, end) — start 含 abandon+ability, end 含 语法项目一览.

    end 必须在 start 之后搜 (目录页也含 '语法项目一览', 会误命中).
    """
    start = None
    for i in range(len(reader.pages)):
        text = _page_text(reader, i)
        if "abandon" in text and "ability" in text:
            start = i
            break
    if start is None:
        raise ValueError("未定位到词汇表起始页 (含 abandon+ability)")
    for i in range(start + 1, len(reader.pages)):
        if "语法项目一览" in _page_text(reader, i):
            return (start, i)
    # 找不到结束标记 → 退到文档末尾 (显式, 不静默吃)
    return (start, len(reader.pages))


def _parse_line(line: str) -> tuple[str, str] | None:
    """单行 → (主词, 层级) 或 None (非词条行)."""
    line = line.strip()
    if not line:
        return None
    star_match = _TRAILING_STARS_RE.search(line)
    stars = len(star_match.group(1)) if star_match else 0
    # 剥星标后切分取第一个 token
    head = _SPLIT_RE.split(line.replace("*", "").strip())[0].strip().lower()
    if not _MAIN_WORD_RE.fullmatch(head):
        return None
    return (head, LEVEL_BY_STARS[stars])


def extract_curriculum_vocab(pdf_path: str | Path | None = None) -> list[dict]:
    """英语课标 PDF 附录 2 词汇表 → [{word, level, source}].

    Args:
        pdf_path: 课标 PDF 路径; None 走默认 glob 'data/curriculum/national/*/*英语*.pdf'.

    Returns:
        list[dict], 每项 {word, level('必修'/'选修I'/'选修II'), source}, 首次出现去重.
    """
    pdf = _resolve_pdf(pdf_path)
    reader = PdfReader(pdf)
    start, end = _find_vocab_span(reader)

    seen: set[str] = set()
    rows: list[dict] = []
    for pi in range(start, end):
        for raw in _page_text(reader, pi).split("\n"):
            parsed = _parse_line(raw)
            if parsed is None:
                continue
            word, level = parsed
            if word in seen:
                continue
            seen.add(word)
            rows.append({"word": word, "level": level, "source": SOURCE_TAG})
    return rows


if __name__ == "__main__":
    from collections import Counter

    vocab = extract_curriculum_vocab()
    dist = Counter(r["level"] for r in vocab)
    print(f"total={len(vocab)}  分布={dict(dist)}")
    by = {r["word"]: r["level"] for r in vocab}
    for w in ("abandon", "ability", "above"):
        print(f"  {w} -> {by.get(w)}")
