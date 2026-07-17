#!/usr/bin/env python3
"""Shared parsers for XGKII listening stem harvest."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def docx_text(path: Path) -> str:
    root = ET.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
    lines = []
    for p in root.iter(NS + "p"):
        line = "".join(t.text or "" for t in p.iter(NS + "t")).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def normalize_option_layout(text: str) -> str:
    text = text.replace("\u3000", " ")
    text = text.replace("【此处可播放相关音频，请去附件查看】", "")
    text = text.replace("\f", "\n")
    text = re.sub(r"第\d+页/共\d+页", "", text)
    text = re.sub(r"(?<=\S)([ABC])[\.、．]", r" \1. ", text)
    text = re.sub(r"([ABC])[\.、．](?=\S)", r"\1. ", text)
    return text


def parse_qs(text: str, max_q: int = 20) -> dict[int, dict]:
    text = normalize_option_layout(text)
    items: dict[int, dict] = {}
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
        qm = re.search(r"([A-Za-z][^?]{5,200}\?)", body)
        if not qm:
            continue
        stem = re.sub(r"\s+", " ", qm.group(1)).strip()
        after = body[qm.end() :]
        after = re.split(r"(?:三个选项|选出最佳|听每段|听完后)", after, maxsplit=1)[-1]
        opts: dict[str, str] = {}
        for om in re.finditer(
            r"([ABC])[\.、．]\s*(.+?)(?=\s+[ABC][\.、．]|\s*$)",
            after,
            re.S,
        ):
            val = re.sub(r"\s+", " ", om.group(2)).strip(" .")
            if not re.search(r"[A-Za-z]", val):
                continue
            opts[om.group(1)] = val
        if len(stem) < 8:
            continue
        items[n] = {"n": n, "stem": stem, "options": opts}
    return items


def require_full_abc(year: int, rows: list[dict]) -> None:
    bad = [
        r["n"]
        for r in rows
        if set((r.get("options") or {}).keys()) != {"A", "B", "C"}
        or any(not (r["options"][k] or "").strip() for k in "ABC")
    ]
    if bad:
        raise RuntimeError(f"{year} missing full ABC options on Q{bad}")


def expand_key(blocks: list[str]) -> dict[int, str]:
    s = "".join(blocks)
    if len(s) != 20 or any(ch not in "ABC" for ch in s):
        raise ValueError(f"bad key blocks {blocks!r} -> {s!r}")
    return {i + 1: s[i] for i in range(20)}


def fmt_raw(n: int, stem: str, options: dict[str, str]) -> str:
    parts = [f"{n}. {stem}"]
    for k in "ABC":
        if k in options:
            parts.append(f"{k}. {options[k]}")
    return " ".join(parts)
