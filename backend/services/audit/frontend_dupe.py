"""前端复用 audit (Rule 5 + L-G).

扫 frontend/*.html:
  - inline <script> 块 > 80 L (超出 = 应抽 common.js)
  - inline <style> 块 > 30 L (超出 = 应抽 css)
  - fetch( 出现 ≥ 2 个 html 未走 common.js → 重复
  - duplicate fn name (eg const $ = ...) 出现多 html
"""
from __future__ import annotations

import re
from pathlib import Path

import duckdb

from ._common import ROOT, finding

FRONTEND_DIR = ROOT / "frontend"
INLINE_SCRIPT_BLOCK_LIMIT = 80
INLINE_STYLE_BLOCK_LIMIT = 30

_SCRIPT_RE = re.compile(r"<script(?![^>]*src=)[^>]*>(.*?)</script>", re.DOTALL | re.IGNORECASE)
_STYLE_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.DOTALL | re.IGNORECASE)


def _scan_inline_blocks(text: str, pat: re.Pattern) -> list[int]:
    return [block.count("\n") + 1 for block in pat.findall(text)]


def audit_frontend_inline_blocks(_con: duckdb.DuckDBPyConnection) -> list[dict]:
    out = []
    big_script = []; big_style = []
    for html in sorted(FRONTEND_DIR.glob("*.html")):
        text = html.read_text(encoding="utf-8")
        for n in _scan_inline_blocks(text, _SCRIPT_RE):
            if n > INLINE_SCRIPT_BLOCK_LIMIT:
                big_script.append((html.name, n))
        for n in _scan_inline_blocks(text, _STYLE_RE):
            if n > INLINE_STYLE_BLOCK_LIMIT:
                big_style.append((html.name, n))
    sev_s = "WARN" if big_script else "OK"
    sev_c = "WARN" if big_style else "OK"
    out.append(finding("frontend_inline_script", sev_s,
                       target=f"frontend/*.html inline <script> ≤ {INLINE_SCRIPT_BLOCK_LIMIT} L",
                       expected="抽到 common.js", actual=str(big_script),
                       note="违反 Rule 5 可复用 + L-G; 应抽到 frontend/static/common.js"))
    out.append(finding("frontend_inline_style", sev_c,
                       target=f"frontend/*.html inline <style> ≤ {INLINE_STYLE_BLOCK_LIMIT} L",
                       expected="抽到 style.css", actual=str(big_style)))
    return out


def audit_frontend_duplicate_fetch(_con: duckdb.DuckDBPyConnection) -> list[dict]:
    """Detect duplicated 'fetch(' usage across html files not delegated to common."""
    fetch_by_file: dict[str, int] = {}
    for html in sorted(FRONTEND_DIR.glob("*.html")):
        text = html.read_text(encoding="utf-8")
        fetch_count = len(re.findall(r"\bfetch\(", text))
        if fetch_count > 0:
            fetch_by_file[html.name] = fetch_count
    sev = "WARN" if len(fetch_by_file) >= 2 else "OK"
    return [finding("frontend_duplicate_fetch", sev,
                    target="≥ 2 html 用 fetch( 应走 common.js",
                    expected="集中到 frontend/static/common.js",
                    actual=str(fetch_by_file),
                    note="违反 Rule 5; L-G 反模式")]
