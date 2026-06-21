"""真值校验系统 — 模块化注册 + 门接入单一入口.

CHECKERS = 全域真值校验器 (数据驱动 dispatch, 同 _LIB_CHECKS); 加新域 = 追加一个 checker, 核心不动。
CLI (scripts/tools/truth_check) + D0 门 (run_truth_checks) 都遍历 CHECKERS = 同一计算点, 非两套一次性脚本。
"""
from __future__ import annotations

from .base import Deviation, TruthChecker, load_anchors
from .truth_exam import ExamTruthChecker
from .truth_gloss import GlossaryTruthChecker

CHECKERS: list[TruthChecker] = [ExamTruthChecker(), GlossaryTruthChecker()]

__all__ = ["CHECKERS", "Deviation", "TruthChecker", "load_anchors", "collect_deviations", "run_truth_checks"]


def collect_deviations(con) -> list[Deviation]:
    """跑全部真值校验器, 收所有偏差 (CLI/门/API 共用)."""
    out = []
    for chk in CHECKERS:
        out.extend(chk.check(con))
    return out


def run_truth_checks(con, check) -> None:
    """D0 门接入: 每偏差调既有 check(); BLOCK→失败入 FAILURES→exit1, UNKNOWN→pass但可见(诚实降级)."""
    print("\n=== 真值锚比对 (验内容匹配第一手源, 非计数自洽) ===")
    for d in collect_deviations(con):
        check(f"[真值:{d.domain}:{d.anchor_key}] {d.kind}", d.severity != "BLOCK", d.detail)
