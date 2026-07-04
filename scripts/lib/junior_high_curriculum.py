"""义务教育英语课程标准 (2022年版) 词汇表 + 语法项目表抽取 — 初中子系统 stage 真相源.

第一手源: data/junior_high/curriculum/义务教育英语课程标准_2022年版.pdf (201页, 官方 S 级).

布局实测: 词汇表是**两栏字母序** (extract_text 会把两栏交错合并, 如 "after ball" =
左栏 after + 右栏 ball). 必须按 x 坐标 crop 左/右栏分别抽 (同高中 renjiao page.crop 做法).
栏分界 x≈200 (左栏 x0≈70, 右栏 x0≈260).

页范围 (PDF index, 0-based):
  二级词汇表(小学 505 词): idx94-103 (header idx93).
  三级词汇表(初中, 1600 词含二级 505 用 * 标 + 1095 三级新增): a-z 主表 idx105-134
    (止于 'zoo*'); 其后数词/月份/星期/地理/节日/不规则动词表 = 说明 §5-7 "单独列出"
    的补充段, **不计入 1600** (实测 a-z 主表 distinct ≈ 官方 1600).
  语法项目表: idx144-148 (header idx144); "＋"(全角) 标 = 仅理解要求的三级项.

CC<10/函数 (Rule 8). 纯抽取, 不写 DB, 不 ATTACH.
"""
from __future__ import annotations

import re

import pdfplumber

PDF_PATH = "data/junior_high/curriculum/义务教育英语课程标准_2022年版.pdf"

# 栏分界 x 坐标 (实测左栏 x0≈70 / 右栏 x0≈260, 522 宽页, 200 居中安全分界).
COL_SPLIT = 200

# 词汇表页范围 (PDF index).
L2_PAGES = range(94, 104)        # 二级 a-z (小学 505).
L3_AZ_PAGES = range(105, 135)    # 三级 a-z 主表 (1600), 止于 idx134 'zoo*'.

# 主词 token: 英文起头, 允许内嵌 - ' / (actor/actress, AI), 可后跟 *.
_MAIN_RE = re.compile(r"^([A-Za-z][A-Za-z\-'/]*)")

# 非主词噪声 (栏头字母 / 词性标 / PDF OCR 残片).
_NOISE = {"n", "adj", "v", "pl", "sing", "eg", "etc", "ie", "adv"}

# 括号变体里要跳过的标签 token.
_ALT_SKIP = {"pl", "sing", "eg", "etc", "ie", "an", "to"}
_ALT_WORD_RE = re.compile(r"([A-Za-z][A-Za-z\-']{1,})")


def _crop_columns(page) -> list[str]:
    """按 x 坐标 crop 左右栏, 各自 extract_text → 两段文本 (保栏内字母序)."""
    out = []
    for x0, x1 in ((0, COL_SPLIT), (COL_SPLIT, page.width)):
        out.append(page.crop((x0, 0, x1, page.height)).extract_text() or "")
    return out


def _is_chinese_line(line: str) -> bool:
    return any("一" <= ch <= "鿿" for ch in line)


def _parse_vocab_line(line: str) -> tuple[str, bool, list[str]] | None:
    """一行 → (主词, 带星?, 括号变体词列表) 或 None.

    带星 = 行内含 * (三级表中标二级复列词). 括号变体如 child(pl. children) / (an).
    """
    starred = "*" in line or "＊" in line
    paren_groups = re.findall(r"\(([^)]*)\)", line)
    main_part = re.sub(r"\([^)]*\)", "", line).replace("*", "").replace("＊", "").strip()
    toks = main_part.split()
    if not toks:
        return None
    m = _MAIN_RE.match(toks[0])
    if not m:
        return None
    word = m.group(1).lower().strip("/-'.")
    if not word or word in _NOISE or len(word) < 2:
        return None
    return (word, starred, _extract_alts(paren_groups, word))


def _extract_alts(paren_groups: list[str], word: str) -> list[str]:
    """括号变体词 (child(pl. children)→children), 去标签 token + 主词自身."""
    alts = []
    for grp in paren_groups:
        for a in _ALT_WORD_RE.findall(grp):
            aw = a.lower()
            if aw not in _ALT_SKIP and aw != word:
                alts.append(aw)
    return alts


def _row(word, level, stage, source_tag, starred, is_alt=False) -> dict:
    r = {"word": word, "level": level, "stage": stage, "source": source_tag, "starred": starred}
    if is_alt:
        r["is_alt"] = True
    return r


def _rows_from_line(line, level, stage, source_tag, include_alts, seen) -> list[dict]:
    """一行 → 0/1 主词行 (+可选变体行); 维护 seen 去重. (抽出降 extract_vocab CC)."""
    if not line or _is_chinese_line(line):
        return []
    parsed = _parse_vocab_line(line)
    if not parsed:
        return []
    word, starred, alts = parsed
    out: list[dict] = []
    if word not in seen:
        seen.add(word)
        out.append(_row(word, level, stage, source_tag, starred))
    if include_alts:
        for aw in alts:
            if aw not in seen:
                seen.add(aw)
                out.append(_row(aw, level, stage, source_tag, starred, is_alt=True))
    return out


# 单词变体/展开: '(AmE color)' / '(=application)' / '(BrE X)' — 词头才是词条, 这些是注释。
# **只匹配单词** (跳过 '(=physical education)' 多词展开 — 其分量 physical/education 可能本身是词头, 不删)。
_PAREN_VARIANT_RE = re.compile(r"^(?:AmE|BrE|=)\s*([A-Za-z][A-Za-z\-']+)\s*$")


def extract_paren_words(pages=L3_AZ_PAGES) -> set[str]:
    """括号内**单词**变体/展开词集 (官方口径: '(=application)'/'(AmE color)' 是注释非独立词条).

    全页 extract_text (括号行内, 两栏合并不破配对)。供 _cross_validate 从 OCR 恢复项减掉
    (这些词只经 OCR 混入, 不在文本层词头)。多词展开不收(防误删 physical/education 等真词头)。
    """
    words: set[str] = set()
    with pdfplumber.open(PDF_PATH) as pdf:
        for idx in pages:
            if idx >= len(pdf.pages):
                break
            text = pdf.pages[idx].extract_text() or ""
            for grp in re.findall(r"\(([^)]*)\)", text):
                m = _PAREN_VARIANT_RE.match(grp.strip())
                if m:
                    words.add(m.group(1).lower().strip("-'"))
    return words


def _merge_unclosed_parens(lines: list[str]) -> list[str]:
    """跨列/跨页边界拼接括号未配平的行 (右栏宽度有限, 长括号变体列表被截断到下一列/页开头).

    坑(2026-07-04 全数据审计): 原版逐行独立解析, 'kilometre(AmE kilometer' 这类右栏末行
    因括号未配平, 续写内容(若存在)在下一列/页首行, 旧版从不看下一行, 静默丢失整个变体词。
    只在"拼接后确实配平"才采用(而非见开括号就无脑吸下一行) — 防止真无续行时误把下一个
    真词条(如 'geography'/'kind*') 吞并导致该词条自身丢失; 经验证多数场景无真续行故不并,
    仅在真有续行(如 kilogramme/kilogram 跨行案例)时生效, 是保守/零回归的合并策略。"""
    out: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if i + 1 < n and line.count("(") > line.count(")"):
            merged = line.rstrip() + " " + lines[i + 1].strip()
            if merged.count("(") == merged.count(")"):
                out.append(merged)
                i += 2
                continue
        out.append(line)
        i += 1
    return out


def extract_vocab(level: str, stage: str, pages, source_tag: str,
                  include_alts: bool = False) -> list[dict]:
    """抽一个词汇表段 (二级或三级 a-z 主表) → [{word, level, stage, source, starred?}].

    level/stage 由调用方传 (二级=小学; 三级表逐词 level/stage 在 emit 层按集合交分裂).
    先跨列/跨页拉平成一条行流, 补括号截断续行, 再逐行解析(_merge_unclosed_parens 只在
    确认能配平时合并, 不会误吸不相关的下一词条)。
    """
    rows: list[dict] = []
    seen: set[str] = set()
    flat: list[str] = []
    with pdfplumber.open(PDF_PATH) as pdf:
        for idx in pages:
            if idx >= len(pdf.pages):
                break
            for col in _crop_columns(pdf.pages[idx]):
                flat.extend(raw.strip() for raw in col.split("\n"))
    for line in _merge_unclosed_parens(flat):
        rows.extend(_rows_from_line(line, level, stage, source_tag, include_alts, seen))
    return rows


# ---------------- 语法项目表 (idx144-148) ----------------

# 层级行型 (复用高中 curriculum_grammar 思路, 但 level marker 是全角"＋"= 仅理解, 非 *).
_G_L1 = re.compile(r"^([一二三四五六七八九十]+)、(.+)$")           # 一、词类
_G_L2 = re.compile(r"^[（(]([一二三四五六七八九十]+)[)）]\s*(.+)$")  # （一）名词
_G_L3 = re.compile(r"^(\d+)[.．]\s*(.+)$")                          # 1.可数名词…

_G_SKIP_PREFIX = ("附录", "说明", "义务教育", "■", "│")
_PLUS_CHARS = ("＋", "+")


_HEAD_PLUS_RE = re.compile(r"^[+＋]\s*")


def _strip_plus(label: str) -> str:
    """清行首残留 +/＋ (head '仅理解'标记已在 _match_grammar 剥); **保留 inline +** (主语+动词 是内容,
    强验证G1: 原全剥致 '主语+动词'→'主语动词' 截断). 不据 inline 判 understand (F6 防假阳性, 由 head 正则管)."""
    return _HEAD_PLUS_RE.sub("", label).strip().rstrip("：:")


def _grammar_skip(line: str) -> bool:
    if not line or line.isdigit():
        return True
    if any(line.startswith(p) for p in _G_SKIP_PREFIX):
        return True
    if "语法项目表" in line or line == "附 录":
        return True
    return False


def _is_grammar_marker(line: str) -> bool:
    s = _HEAD_PLUS_RE.sub("", line.strip())
    return any(r.match(s) for r in (_G_L1, _G_L2, _G_L3))


def _is_grammar_continuation(prev: str, nxt: str) -> bool:
    """nxt 是 prev(marker行)的折行续写? 同 scripts/lib/curriculum_grammar.py._is_continuation
    判据(该姊妹模块已修过此坑, 本文件此前未同步移植): 非marker + 含中文 + ASCII占比不过高(非例句)
    + prev 不完整(括号未配平 或 无终止符)。"""
    if not nxt or _is_grammar_marker(nxt):
        return False
    if not any("一" <= c <= "鿿" for c in nxt):
        return False
    if sum(c.isascii() and c.isalpha() for c in nxt) / max(1, len(nxt.replace(" ", ""))) > 0.6:
        return False
    op = prev.count("（") + prev.count("(")
    cp = prev.count("）") + prev.count(")")
    return op > cp or not re.search(r"[）)。\*]\s*$", prev)


def _merge_grammar_continuations(lines: list[str]) -> list[str]:
    """合并 marker 行的折行续写(语法项 label 跨页换行被截, 如'关系从句'条目 seq 丢失后半句).
    字符级拼接(PDF 换行无空格); 必须在 _grammar_skip 过滤前做(续行含关系代词清单可能被误杀)。"""
    out: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if _is_grammar_marker(line):
            j = i + 1
            while j < n and _is_grammar_continuation(line, lines[j]):
                line += lines[j]
                j += 1
            out.append(line)
            i = j
        else:
            out.append(line)
            i += 1
    return out


def _match_grammar(line: str, state: dict) -> dict | None:
    """4 层 dispatch → grammar node. F6 修: **仅行首** +/＋ = '仅理解'标记(剥后再匹配),
    inline + (主语+动词) 不算 (防假阳性)。"""
    s = line.strip()
    understand = bool(_HEAD_PLUS_RE.match(s))   # 行首 + = 理解项
    if understand:
        s = _HEAD_PLUS_RE.sub("", s)
    for depth, regex in ((1, _G_L1), (2, _G_L2), (3, _G_L3)):
        m = regex.match(s)
        if not m:
            continue
        num, raw_label = m.group(1), m.group(2)
        label = _strip_plus(raw_label)
        parent = None
        for d in range(depth - 1, 0, -1):
            if state["path"].get(d):
                parent = state["path"][d]
                break
        item_id = (parent + "/" if parent else "") + num
        state["path"][depth] = item_id
        for k in range(depth + 1, 4):
            state["path"][k] = None
        state["seq"] += 1
        return {"item_id": item_id, "depth": depth, "label": label,
                "parent": parent, "level": "三级+" if understand else "三级",
                "understand_only": understand, "seq": state["seq"]}
    return None


def extract_grammar(pages=range(144, 149), source_tag: str = "yiwu_2022_grammar") -> list[dict]:
    rows: list[dict] = []
    state = {"path": {1: None, 2: None, 3: None}, "seq": 0}
    with pdfplumber.open(PDF_PATH) as pdf:
        for idx in pages:
            if idx >= len(pdf.pages):
                break
            text = pdf.pages[idx].extract_text() or ""
            merged = _merge_grammar_continuations([raw.strip() for raw in text.split("\n")])
            for line in merged:
                if _grammar_skip(line):
                    continue
                node = _match_grammar(line, state)
                if node:
                    node["source"] = source_tag
                    rows.append(node)
    return rows
