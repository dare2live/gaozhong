#!/usr/bin/env python3
"""前端 RC1 质量防回归检查 (moth 锁: 锁住 a11y/无emoji/单调色板成果不退化).

跑: python3 scripts/lib/frontend_rc1_check.py   (cwd=项目根)
exit 0 = 全过; 非0 = 有回归 (打印违规)。
检查 (live app.html 加载的前端文件):
  1. 无 emoji (live JS 渲染文本; 排版符号 →·—✕●↑↓↔←⭑★ 豁免)
  2. echarts 图表容器全有 role=img (读屏文字替代)
  3. 无 off-token 旧红/旧蓝 chromatic (非echarts UI; category-config 数据色单一来源豁免)
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

FE = Path(__file__).resolve().parents[2] / "frontend" / "static"
LIVE_JS = ["common", "graph_popup", "nav-config", "category-config", "app_router",
           "beike", "jiangke", "lesson", "textbook", "dict", "k12", "xisheng"]
ECHARTS_JS = ["beike", "k12", "xisheng", "jiangke"]
NON_ECHARTS = [f for f in LIVE_JS if f not in ECHARTS_JS]
LIVE_CSS = ["style", "app", "beike", "design-system"]
OFF_EXEMPT = {"category-config"}   # 数据编码色单一来源 (design-system 自述与 UI accent 正交)

ALLOWED = set("→·—✕●↑↓↔←✓≈≠⊆⊇∈⭑★☆°")
EMOJI = re.compile(r"[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFFℹ️]")
OLD_CHROMA = re.compile(r"#(?:E3120B|e3120b|c1272d|C1272D|0a4d75|0A4D75|1c5d99|185FA5|1D6FB8|1d6fb8|993C1D|c50e09)\b")


def _rd(name: str, ext: str = "js") -> str:
    p = FE / f"{name}.{ext}"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _strip_js_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", s, flags=re.MULTILINE)


def _scan(text: str, pat: re.Pattern, label: str, keep) -> list[str]:
    """通用: 逐行扫 pat, keep(ch) 真才算违规, 返回 'label:ln hit' 列表."""
    out = []
    for ln, line in enumerate(text.splitlines(), 1):
        for hit in pat.findall(line):
            if keep(hit):
                out.append(f"{label}:{ln} {hit!r}")
    return out


def check_emoji() -> list[str]:
    bad = []
    for f in LIVE_JS:
        bad += _scan(_strip_js_comments(_rd(f)), EMOJI, f"emoji {f}.js", lambda c: c not in ALLOWED)
    return bad


def check_chart_aria() -> list[str]:
    init_n = sum(len(re.findall(r"echarts\.init", _rd(f))) for f in ECHARTS_JS)
    aria_n = sum(len(re.findall(r'role="img"', _rd(f))) for f in ECHARTS_JS)
    return [] if (init_n and aria_n >= init_n) else [f"chart role=img 覆盖不足: {aria_n}/{init_n} init"]


def check_off_token() -> list[str]:
    bad = []
    for f in (x for x in NON_ECHARTS if x not in OFF_EXEMPT):
        bad += _scan(_strip_js_comments(_rd(f)), OLD_CHROMA, f"off-token {f}.js", lambda h: True)
    for f in LIVE_CSS:
        css = "\n".join(l for l in _rd(f, "css").splitlines() if not l.lstrip().startswith("/*"))
        bad += _scan(css, OLD_CHROMA, f"off-token {f}.css", lambda h: True)
    return bad


def main() -> int:
    bad = check_emoji() + check_chart_aria() + check_off_token()
    if bad:
        print("前端 RC1 回归:")
        for b in bad[:20]:
            print("  XX", b)
        return 1
    print("前端 RC1 质量门 OK (无emoji / 图表role=img全覆盖 / 无off-token旧调色板)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
