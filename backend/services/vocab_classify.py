"""超纲词分层分类 — 运行时只读 artifact (零 nltk 依赖, 单一计算点).

artifact = data/structured/vocab_classification.jsonl (由 scripts/build_vocab_classification.py
生成, 词形归并+派生+高考核对+专名过滤)。词不在 artifact = 在 cefr_vocab 课标内。
"""
from __future__ import annotations

import json
from pathlib import Path

_ART = Path(__file__).resolve().parent.parent.parent / "data" / "structured" / "vocab_classification.jsonl"

_REAL_OVER = ("真超纲·辽宁考过", "真超纲·仅外省考过", "真超纲·未考")
_IN_SYLLABUS = ("课标屈折变形", "课标派生")  # 实为课标词的变形/派生 → 不算超纲


def _load() -> dict[str, str]:
    if not _ART.exists():
        return {}
    out = {}
    for line in _ART.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["word"].lower()] = r["category"]
    return out


_CLASSIFY = _load()


def category(word: str) -> str:
    """词的分层类别; 不在 artifact = 课标内(精确命中 cefr)."""
    return _CLASSIFY.get(word.lower(), "课标内")


def is_real_over(word: str) -> bool:
    """是否真超纲 (排除变形/派生/专名)."""
    return category(word) in _REAL_OVER


def unit_over_profile(words: list[str]) -> dict:
    """单元词的越纲分层画像 (真超纲分辽宁考过/外省/未考; 越纲率只算真超纲)."""
    from collections import Counter
    c = Counter(category(w) for w in words)
    real_over = sum(c[k] for k in _REAL_OVER)
    in_syl = len(words) - real_over - c["专名/碎片"]   # 课标内 + 变形 + 派生
    total = len(words)
    return {
        "total": total,
        "in_syllabus": in_syl,                          # 课标内(含屈折/派生变形)
        "over_ln_tested": c["真超纲·辽宁考过"],          # 真超纲 ∧ 辽宁考过 — 必教
        "over_other_tested": c["真超纲·仅外省考过"],     # 真超纲 ∧ 仅外省 — 高值参考
        "over_untested": c["真超纲·未考"],               # 真超纲 ∧ 未考 — 选学
        "proper_noise": c["专名/碎片"],                  # 专名/碎片 — 不计
        "over_rate_pct": round(100 * real_over / total, 1) if total else 0.0,
    }
