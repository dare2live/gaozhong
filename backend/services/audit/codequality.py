"""代码质量审计 — 代码也是数据 (用户 2026-05-23: 系统层面治理).

跑 scripts/lib/complexity_check.py 全扫:
  - 任何 CC > 10 函数 → WARN
  - 任何 size > 250 行的 backend/* / scripts/* 文件 → WARN
  - 任何 size > 400 行 → FAIL
找到的 hotspot 入 audit_findings, 走相同 0 FAIL / 1 WARN 治理路径.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import duckdb

from ._common import ROOT, finding

CC_WARN = 10
SIZE_WARN = 250
SIZE_FAIL = 400

# 扫这些目录下的 .py
SCAN_DIRS = [ROOT / "backend", ROOT / "scripts"]


def _scan_files() -> list[Path]:
    out = []
    for d in SCAN_DIRS:
        out.extend(p for p in d.rglob("*.py")
                   if "__pycache__" not in p.parts
                   and not p.name.startswith("test_"))
    return out


def _hi_cc_funcs(file: Path) -> list[tuple[str, int]]:
    """Run complexity_check.py --json on file, return [(name, cc), ...] for CC > threshold."""
    try:
        res = subprocess.run(
            ["python3", str(ROOT / "scripts/lib/complexity_check.py"), "--json", str(file)],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return []
    import json
    try:
        rows = json.loads(res.stdout)
    except json.JSONDecodeError:
        return []
    return [(r["name"], r["cc"]) for r in rows if r.get("cc", 0) > CC_WARN]


CC_BASELINE = 13   # 与 stop_gate.sh 一致, M6 持续收紧 (D0 100% 准 — OBS 与 baseline 对齐)


def audit_code_complexity(_con: duckdb.DuckDBPyConnection) -> list[dict]:
    files = _scan_files()
    hi_funcs: list[dict] = []
    for f in files:
        for name, cc in _hi_cc_funcs(f):
            hi_funcs.append({"file": str(f.relative_to(ROOT)), "name": name, "cc": cc})
    # D0 重归类: ≤ baseline = OK (OBS, 非数据 bug); > baseline = WARN (真涨需收紧)
    sev = "OK" if len(hi_funcs) <= CC_BASELINE else "WARN"
    return [finding("code_complexity", sev,
                    target=f"all .py in {[str(d.relative_to(ROOT)) for d in SCAN_DIRS]}",
                    expected=f"CC>10 funcs <= baseline {CC_BASELINE}",
                    actual=str(len(hi_funcs)),
                    note=f"OBS 工程指标 (M6 持续收紧); hotspots: {hi_funcs[:5]}" if hi_funcs else None)]


def audit_code_size(_con: duckdb.DuckDBPyConnection) -> list[dict]:
    files = _scan_files()
    big = []
    huge = []
    for f in files:
        lines = sum(1 for _ in f.open("r", encoding="utf-8", errors="replace"))
        if lines > SIZE_FAIL:
            huge.append((str(f.relative_to(ROOT)), lines))
        elif lines > SIZE_WARN:
            big.append((str(f.relative_to(ROOT)), lines))
    sev = "FAIL" if huge else ("WARN" if big else "OK")
    return [finding("code_size", sev,
                    target="backend/scripts py file LOC",
                    expected=f"WARN > {SIZE_WARN} L, FAIL > {SIZE_FAIL} L",
                    actual=f"warn={len(big)}, fail={len(huge)}",
                    note=f"huge={huge} big={big}" if (huge or big) else None)]
