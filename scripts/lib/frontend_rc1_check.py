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
           "beike", "scaffold", "jichu_pages", "listening", "textbook", "dict", "k12"]
ECHARTS_JS = ["beike", "k12", "scaffold"]
NON_ECHARTS = [f for f in LIVE_JS if f not in ECHARTS_JS]
LIVE_CSS = ["style", "app", "beike", "design-system"]
OFF_EXEMPT = {"category-config"}   # 数据编码色单一来源 (design-system 自述与 UI accent 正交)

ALLOWED = set("→·—✕●↑↓↔←✓≈≠⊆⊇∈⭑★☆°")
EMOJI = re.compile(r"[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFFℹ️]")
OLD_CHROMA = re.compile(r"#(?:E3120B|e3120b|c1272d|C1272D|0a4d75|0A4D75|1c5d99|185FA5|1D6FB8|1d6fb8|993C1D|c50e09)\b")
# 冷灰族 (与暖中性 --ink/--line 冲突, 用户全局禁; #000 纯黑不在禁列=打印用)。仅扫 CSS: echarts canvas 在 JS 里合法用 hex。
COLD_GREY = re.compile(r"#(?:333|444|555|666|777|888|999|aaa|bbb|ccc|ddd|eee)\b|rgba\(\s*0\s*,\s*0\s*,\s*0", re.I)
SELECT_TAG = re.compile(r"<select\b[^>]*>")


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
    init_n = sum(len(re.findall(r"\.initChart\(", _rd(f))) for f in ECHARTS_JS)
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


def check_raw_echarts_init() -> list[str]:
    """raw echarts.init 仅允许 common.js (GZ.initChart 单一安全入口); 其余文件须经 GZ.initChart,
    根治"重访 tab 陈旧实例渲到已销毁 DOM 致空白" + load 竞态。防回归: 新图勿直接 echarts.init。"""
    bad = []
    for f in LIVE_JS:
        if f == "common":
            continue
        for ln, line in enumerate(_strip_js_comments(_rd(f)).splitlines(), 1):
            if "echarts.init(" in line:
                bad.append(f"raw echarts.init {f}.js:{ln} (应用 GZ.initChart 防陈旧实例/竞态空白)")
    return bad


def check_cold_grey() -> list[str]:
    """冷灰族禁入 CSS (锁住 RC1 ceiling 调色板令牌化, 防 #666/#888/#ddd 等回流冲突暖палитра)。"""
    bad = []
    for f in LIVE_CSS:
        css = "\n".join(l for l in _rd(f, "css").splitlines() if not l.lstrip().startswith("/*"))
        bad += _scan(css, COLD_GREY, f"cold-grey {f}.css", lambda h: True)
    return bad


def check_layout_restored() -> list[str]:
    """锁 commit 5cad53e 布局回归: design-system.css 的 .bk-card 必有 padding + .bk-h 必 flex
    (共享卡片布局, 删了致全 tab 卡片贴边/迁移行竖堆/delta 丢 pill = 用户'太乱'主因)。"""
    ds = _rd("design-system", "css")
    bad = []
    if not re.search(r"\.bk-card\s*\{[^}]*padding", ds):
        bad.append("design-system.css .bk-card 缺 padding (布局回归)")
    if not re.search(r"\.bk-h\s*\{[^}]*display:\s*flex", ds):
        bad.append("design-system.css .bk-h 缺 display:flex (布局回归)")
    return bad


def check_select_aria() -> list[str]:
    """交互 <select> 须有 accessible name (aria-label/aria-labelledby), 防读屏读成无名 combobox。"""
    bad = []
    for f in LIVE_JS:
        for ln, line in enumerate(_strip_js_comments(_rd(f)).splitlines(), 1):
            for tag in SELECT_TAG.findall(line):
                if "aria-label" not in tag:
                    bad.append(f"select 无 aria-label {f}.js:{ln}")
    return bad


def main() -> int:
    bad = (check_emoji() + check_chart_aria() + check_off_token() + check_raw_echarts_init()
           + check_cold_grey() + check_layout_restored() + check_select_aria())
    if bad:
        print("前端 RC1 回归:")
        for b in bad[:20]:
            print("  XX", b)
        return 1
    print("前端 RC1 质量门 OK (无emoji / 图表role=img / 无off-token / 无冷灰CSS / 布局未回归 / select有aria)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
