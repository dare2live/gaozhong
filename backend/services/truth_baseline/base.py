"""真值校验系统 — 基座 (TruthChecker ABC + Deviation + 注册表加载).

根治"自洽门≠真值校验": checker 验"库内容匹配第一手真值锚", 非"计数==快照"。
模块化: 每域一个 TruthChecker 子类, 注册进 CHECKERS (数据驱动 dispatch, 同 _LIB_CHECKS)。
工具化: CLI (scripts/tools/truth_check) + D0 门 (run_truth_checks) 复用同一 CHECKERS, 非一次性脚本。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[3]
_ANCHORS = _ROOT / "backend" / "config" / "truth_anchors.yaml"


@dataclass
class Deviation:
    domain: str
    anchor_key: str
    kind: str       # content_mismatch | missing | pollution | no_anchor
    severity: str   # BLOCK | UNKNOWN
    detail: str


def load_anchors() -> dict:
    return yaml.safe_load(_ANCHORS.read_text(encoding="utf-8")) or {}


class TruthChecker:
    """每域真值校验器基类. domain + check(con)->偏差 + self_test()(证明非装饰门)."""
    domain = "?"

    def check(self, con) -> list[Deviation]:
        raise NotImplementedError

    def self_test(self) -> bool:
        """对抗自测: 注入污染必抓到 + 干净不误报. 返回 True=校验器真有效(非装饰门, 坑21).

        子类 override; 默认无自测 = 不许 active (lifecycle 前置门)。
        """
        return False
