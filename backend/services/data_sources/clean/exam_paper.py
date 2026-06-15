"""通用卷型 provenance 清洗工具 — category-aware 诚实卷型分类.

抽取自 backend/services/extraction/exam.py 的 classify_paper / _juan_token /
_norm_cat / _JUAN_MAP / LN_II_* 常量, 与之**字节级等价**, 仅做模块化复用.

卷型 ↔ 辽宁 (provenance honest): GAOKAO-Bench/Updates 的 category 区分
新课标I/II/III/甲/乙. 辽宁卷型史: 2010-2014 自主命题(无国家卷) / 2015 起用新课标全国II卷.
故只有 "新课标II + year>=2015" = 辽宁卷; 其余诚实标非辽宁卷型, 不冒充辽宁 (L-N/L-P/L-R 防回归).

全半角统一: Ⅰ/Ⅱ/Ⅲ (大写) + ⅰ/ⅱ/ⅲ (小写) → I/II/III; 甲/乙 直读.

公开 API (与 exam.classify_paper 完全等价):
    classify_paper(year, category, question_text="") -> (province, paper_type)
"""
from __future__ import annotations

LN_II_2015_2020 = "辽宁 (新课标 II 卷, 2015-2020)"
LN_II_2021 = "辽宁 (新课标 II 卷, 2021+)"


def _norm_cat(category: str | None) -> str:
    c = category or ""
    for a, b in (("Ⅰ", "I"), ("Ⅱ", "II"), ("Ⅲ", "III"), ("ⅰ", "I"), ("ⅱ", "II"), ("ⅲ", "III")):
        c = c.replace(a, b)
    return c.upper()


def _juan_token(c: str) -> str:
    """normalized category → 卷型 token (甲/乙/III/II/I/'')."""
    if "甲" in c:
        return "甲"
    if "乙" in c:
        return "乙"
    if "III" in c or "三" in c:
        return "III"
    if "II" in c or "二" in c:
        return "II"
    if "I" in c or "一" in c:
        return "I"
    return ""


# 卷型 token → (province, paper_type); II 因 year 区分辽宁与否, 单独处理.
_JUAN_MAP = {
    "甲": ("全国甲卷 (非辽宁)", "全国甲卷"),
    "乙": ("全国乙卷 (非辽宁)", "全国乙卷"),
    "III": ("全国新课标 III 卷 (非辽宁)", "新课标 III 卷"),
    "I": ("全国新课标 I 卷 (非辽宁)", "新课标 I 卷"),
}


def classify_paper(year: int | None, category: str | None,
                   question_text: str = "") -> tuple[str, str]:
    """(province, paper_type) — category-aware 诚实卷型标注 (见上注释).

    只有 "新课标II + year>=2015" = 辽宁卷; 其余诚实标非辽宁卷型.
    """
    if year is None:
        return "未知", "未知"
    tok = _juan_token(_norm_cat(category))
    if tok in _JUAN_MAP:
        return _JUAN_MAP[tok]
    if tok == "II":
        if year >= 2015:
            return (LN_II_2021 if year >= 2021 else LN_II_2015_2020), "新课标 II 卷"
        return "全国新课标 II 卷 (2010-2014, 非辽宁; 辽宁当年自主命题)", "新课标 II 卷"
    if "解析版" in (category or ""):
        return "未知 (解析版, 待核验卷型)", "未知"
    return "未知 (GAOKAO-Bench 无明确卷型)", "未知"
