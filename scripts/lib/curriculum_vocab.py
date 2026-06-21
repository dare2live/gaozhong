"""课标词汇表 (附录 2, p129-182) 抽取 — 从 extract_curriculum.py 拆出 (4.5).

减 extract_cefr_vocab CC 20 → ≤ 10.
"""
from __future__ import annotations

import re

from pypdf import PdfReader

MAIN_RE = re.compile(r"^([A-Za-z][A-Za-z\-'.]*)(\*{1,2})?$")
ALT_WORD_RE = re.compile(r"([A-Za-z][A-Za-z\-']{1,})")
ALT_SKIP_TOKENS = {"pl", "sing", "eg", "etc", "ie"}


def _level_of(suffix: str) -> str:
    if suffix.startswith("***"): return "选修"
    if suffix.startswith("**"): return "选必"
    if suffix.startswith("*"): return "必修"
    return "义教"


def _skip_line(line: str) -> bool:
    if not line: return True
    if line.startswith("│") or line.isdigit(): return True
    if len(line) == 1 and line.isalpha(): return True
    # 跳过中文说明
    if any("一" <= ch <= "鿿" for ch in line): return True
    return False


def _parse_main_token(tok: str) -> tuple[str, str] | None:
    m = MAIN_RE.match(tok)
    if not m: return None
    w = m.group(1).lower().rstrip(".")
    suffix = m.group(2) or ""
    return (w, suffix)


def _extract_alt_words(paren_groups: list[str]) -> list[str]:
    """Extract alt forms from '(an)' / '(pl. mice)' etc."""
    out = []
    for p in paren_groups:
        for a in ALT_WORD_RE.findall(p):
            aw = a.lower()
            if aw not in ALT_SKIP_TOKENS:
                out.append(aw)
    return out


def _process_line(line: str, seen: set[str], source_tag: str) -> list[dict]:
    rows = []
    # 全行捕星(item级 */**/*** 在词尾, 但带括注的行如 'analyse (analyze)**' 去括号后 ** 会脱成独立
    # token 被 MAIN_RE 丢 → 父词+alt 都误标义教, 44行错)。先从全行抓星, 再去括号去星, 全行星优先。
    star_m = re.search(r"\*{1,3}", line)
    line_suffix = star_m.group(0) if star_m else ""
    paren = re.findall(r"\(([^)]*)\)", line)
    main_part = re.sub(r"\*{1,3}", "", re.sub(r"\([^)]*\)", "", line)).strip()
    for tok in main_part.split():
        parsed = _parse_main_token(tok)
        if not parsed: continue
        word, tok_suffix = parsed
        suffix = line_suffix or tok_suffix              # 全行星(真item级) 优先, 兜底 token 星
        if word and word not in seen:
            seen.add(word)
            rows.append({
                "word": word, "cefr_level": _level_of(suffix),
                "raw_suffix": suffix, "source": source_tag,
            })
        for alt_word in _extract_alt_words(paren):
            if alt_word not in seen:
                seen.add(alt_word)
                rows.append({
                    "word": alt_word, "cefr_level": _level_of(suffix),
                    "raw_suffix": suffix + " (alt)", "source": source_tag,
                })
        paren = []   # 只用第一个 token 的括号
    return rows


# 国家表段起锚 (附录标题行 '主要国家名称及相关信息（供教学参考）'): 真词表到此为止。
# index 183(p184) 顶部是 yes..zoo 真词, 底部转国家表; 表内纯 ASCII 行(ADJECTIVES/Korea/
# Korean) 不含中文 → _skip_line 漏过 → 误纳。内容锚定截断 (PIT 安全, 不 hardcode 页/行)。
# 必须锚"行首即标题": 词表首页脚注 '7. 主要国家名称…供教学参考。' 也含该词, 仅以 '7.' 起
# (非行首标题), 不可误截 → 用 ^ 锚区分标题行 vs 句中引用。
_COUNTRY_TABLE_RE = re.compile(r"^主要国家名称及相关信息")


def extract_cefr_vocab(reader: PdfReader, source_tag: str,
                         start_page: int = 129, end_page: int = 184) -> list[dict]:
    # end_page 182→184 (2026-06-17 修): 原 range 停在 index 181, 切掉 index 182('w': why/word/work)
    # + 183('y': yes/yourself) 两页词汇 → 漏 ~55 词(wisdom/with/will...)误判超纲。
    # 184 含到 'y' 页止; index 183 国家表段经 _COUNTRY_TABLE_RE 内容截断 (不靠页号)。
    rows: list[dict] = []
    seen: set[str] = set()
    for pi in range(start_page - 1, end_page):
        if pi >= len(reader.pages): break
        text = reader.pages[pi].extract_text() or ""
        for raw in text.split("\n"):
            line = raw.strip()
            if _COUNTRY_TABLE_RE.search(line):
                return rows   # 国家表起始 → 词表终点 (其后纯 ASCII 国名/形容词会误纳)
            if _skip_line(line): continue
            rows.extend(_process_line(line, seen, source_tag))
    return rows
