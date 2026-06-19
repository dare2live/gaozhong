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
    alts = []
    for grp in paren_groups:
        for a in _ALT_WORD_RE.findall(grp):
            aw = a.lower()
            if aw not in _ALT_SKIP and aw != word:
                alts.append(aw)
    return (word, starred, alts)


def extract_vocab(level: str, stage: str, pages, source_tag: str,
                  include_alts: bool = False) -> list[dict]:
    """抽一个词汇表段 (二级或三级 a-z 主表) → [{word, level, stage, source, starred?}].

    level/stage 由调用方传 (二级=小学; 三级表里逐词的 level/stage 在 emit 层按 starred 分裂).
    返回行带 raw `starred` 供三级表分裂二级复列词. include_alts: 括号变体是否单独入 (去重).
    """
    rows: list[dict] = []
    seen: set[str] = set()
    with pdfplumber.open(PDF_PATH) as pdf:
        for idx in pages:
            if idx >= len(pdf.pages):
                break
            for col in _crop_columns(pdf.pages[idx]):
                for raw in col.split("\n"):
                    line = raw.strip()
                    if not line or _is_chinese_line(line):
                        continue
                    parsed = _parse_vocab_line(line)
                    if not parsed:
                        continue
                    word, starred, alts = parsed
                    if word not in seen:
                        seen.add(word)
                        rows.append({"word": word, "level": level, "stage": stage,
                                     "source": source_tag, "starred": starred})
                    if include_alts:
                        for aw in alts:
                            if aw not in seen:
                                seen.add(aw)
                                rows.append({"word": aw, "level": level, "stage": stage,
                                             "source": source_tag, "starred": starred,
                                             "is_alt": True})
    return rows


# ---------------- 语法项目表 (idx144-148) ----------------

# 层级行型 (复用高中 curriculum_grammar 思路, 但 level marker 是全角"＋"= 仅理解, 非 *).
_G_L1 = re.compile(r"^([一二三四五六七八九十]+)、(.+)$")           # 一、词类
_G_L2 = re.compile(r"^[（(]([一二三四五六七八九十]+)[)）]\s*(.+)$")  # （一）名词
_G_L3 = re.compile(r"^(\d+)[.．]\s*(.+)$")                          # 1.可数名词…

_G_SKIP_PREFIX = ("附录", "说明", "义务教育", "■", "│")
_PLUS_CHARS = ("＋", "+")


def _strip_plus(label: str) -> tuple[str, bool]:
    understand = any(p in label for p in _PLUS_CHARS)
    clean = label
    for p in _PLUS_CHARS:
        clean = clean.replace(p, "")
    return clean.strip().rstrip("：:"), understand


def _grammar_skip(line: str) -> bool:
    if not line or line.isdigit():
        return True
    if any(line.startswith(p) for p in _G_SKIP_PREFIX):
        return True
    if "语法项目表" in line or line == "附 录":
        return True
    return False


def _match_grammar(line: str, state: dict) -> dict | None:
    """4 层 dispatch → grammar node, 维护 parent 路径. CC≤6."""
    for depth, regex in ((1, _G_L1), (2, _G_L2), (3, _G_L3)):
        m = regex.match(line)
        if not m:
            continue
        num, raw_label = m.group(1), m.group(2)
        label, understand = _strip_plus(raw_label)
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
            for raw in text.split("\n"):
                line = raw.strip()
                if _grammar_skip(line):
                    continue
                node = _match_grammar(line, state)
                if node:
                    node["source"] = source_tag
                    rows.append(node)
    return rows
