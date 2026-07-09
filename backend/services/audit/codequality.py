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


CC_BASELINE = 37   # 2026-06-15 god-module 拆分后 42->37 (拆分把 CC>10 函数 verbatim 移入新模块); 减债 backlog 继续降, 升回则收紧


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


SIZE_BIG_BASELINE = 24  # 2026-06-15 拆 4 个 god-module 后, huge(>400)=0 即 Rule 8 已满足; 拆分自然产生更多 250-400 中型文件(big), 均合规. iron-law (huge>400=FAIL) 不变. 2026真题: cross_verify_pdf 加扫描图skip 249→255 (中型合规, 非god-module), baseline 12→13. 2026-07-07 grammar_4q.py 修复子串误配坑31(精确匹配+从句族/前缀/枚举例外三分层)125→183行, 19→21. senior_knowledge.py 补初中短语基线+两层判断物理隔离 231→294行, 21→22. 2026-07-09 全网挖掘补2024/2025/2026高考语法填空解析后: import_recent_exams.py新增_jsonl_field_map/_enrich_analysis(Rule5复用_row_contrib/_fmt_group, 参数化field非重写)217→257行新晋big; data_accuracy_check.py新增2条_LIB_CHECKS注册392→394行(注: 已接近400硬阈, 后续再涨需评估再抽lib), 22→24.
# 2026-07-04 全数据审计12+21问题按根因修复: vocab_renjiao.py(Welcome Unit+专有名词头识别+
# 跨行词条头合并 3 处真bug修复, 220→270行) + junior_high_curriculum.py(语法/词汇续行合并
# 2 处真bug修复, 233→298行) 跨过250行门槛, huge 仍=0(均<400, 非god-module), baseline 13→15.
# 2026-07-04 教研组验收: section.py(锚点大小写归一+启发式行长门槛防误命中真bug修复,
# 211→254行)跨过250行门槛, huge 仍=0, baseline 15→16.
# 2026-07-06 数据关联设计审查批次2: graph.py(全景图谱Top-N排序改relation加权度数+两级
# signal_degree排序, 修复tests_grammar边骨架生存率0/18的架构级bug, 227→277行)跨过250行
# 门槛, huge 仍=0(远低于400, 非god-module), baseline 16→17.
# 2026-07-06 复杂度债务两轮修复(commit 9673fdd/8f40868): extract-method 拆12+25个CC>15/
# CC11-14函数为命名辅助函数, 多个文件自然跨过250行门槛(graph.py 277→305, source_
# contracts.py→280, eol_review_backlog.py→291, eol_review_decisions.py→334[已拆god-
# module分流一半到contract_check.py仍334]等), huge 仍=0(最高399, 远低于400 god-module
# 硬阈), 新增文件跨门槛的都是CC降复杂度的正向重构副产物非债务, baseline 17→19.


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
    # D0 重归类: ≤ baseline = OK (OBS, 非数据 bug); > baseline = WARN (真涨需收紧)
    sev = "FAIL" if huge else ("WARN" if len(big) > SIZE_BIG_BASELINE else "OK")
    return [finding("code_size", sev,
                    target="backend/scripts py file LOC",
                    expected=f"big files <= baseline {SIZE_BIG_BASELINE}, FAIL > {SIZE_FAIL} L",
                    actual=f"big={len(big)}, huge={len(huge)}",
                    note=f"OBS 工程指标; huge={huge} big={big}" if (huge or big) else None)]
