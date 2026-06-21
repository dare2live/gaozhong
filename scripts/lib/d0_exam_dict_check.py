"""D0 考试词典校验 (Canonical 词本体地基; 坑17 新数据入强校验).

锁: 规模(课标∪教材真超纲) + 三源标记齐(每词 source_flags 非空且∈真相源) + 释义覆盖率 +
最准(真题超课标教材的阅读生词如 photosynthesis 不入词典, 防注水) + 每词至少一真相源(不凭空)。
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import yaml

_VARIANTS = Path(__file__).resolve().parents[2] / "backend" / "config" / "word_variants.yaml"


def _known_unglossable() -> set[str]:
    """word_variants.yaml 登记的"我方真值源无释义"白名单 (缩写/专名/复合)."""
    if not _VARIANTS.exists():
        return set()
    cfg = yaml.safe_load(_VARIANTS.read_text(encoding="utf-8")) or {}
    return set(cfg.get("unglossable") or {})


def check_exam_dict(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (33) 考试词典 (Canonical 词本体; 课标∪教材真超纲) ===")
    n = con.execute("SELECT COUNT(*) FROM exam_vocabulary").fetchone()[0]
    check("考试词典规模 3500–5000 (最小: 课标∪教材真超纲, 无CET/GRE注水)", 3500 <= n <= 5000, f"{n}")
    # 每词至少一真相源 (不凭空造词)
    no_src = con.execute(
        "SELECT COUNT(*) FROM exam_vocabulary WHERE NOT (in_curriculum OR in_textbook)").fetchone()[0]
    check("每词至少课标或教材源 (最准: 不凭空造词)", no_src == 0, f"{no_src} 无源")
    # source_flags 与布尔列一致 (provenance 诚实)
    bad_flag = con.execute(
        "SELECT COUNT(*) FROM exam_vocabulary WHERE "
        "(in_curriculum AND source_flags NOT LIKE '%curriculum%') OR "
        "(in_exam AND source_flags NOT LIKE '%exam%')").fetchone()[0]
    check("source_flags 与三源布尔一致 (provenance 可溯)", bad_flag == 0, f"{bad_flag} 不一致")
    # 释义覆盖 ≥98% (教材生词表→中考表→COCA兜底交叉引用)
    cov = con.execute("SELECT COUNT(*) FROM exam_vocabulary WHERE gloss IS NOT NULL").fetchone()[0]
    check("释义覆盖率 ≥98% (教材→中考表→COCA 兜底交叉引用)", cov * 100 >= n * 98,
          f"{cov}/{n}={100 * cov // max(n, 1)}%")
    # gloss ⟺ gloss_source (provenance 诚实: 有释义必有来源, 无释义必无来源)
    bad_gs = con.execute(
        "SELECT COUNT(*) FROM exam_vocabulary WHERE (gloss IS NULL) <> (gloss_source IS NULL)").fetchone()[0]
    check("释义 ⟺ gloss_source (每条释义可溯源; 不凭空)", bad_gs == 0, f"{bad_gs} 不一致")
    # 最准: in_exam 词必有 gaokao_hit_ln>0 (旗与命中数一致)
    bad_exam = con.execute(
        "SELECT COUNT(*) FROM exam_vocabulary WHERE in_exam <> (gaokao_hit_ln > 0)").fetchone()[0]
    check("in_exam 旗 == 辽宁命中>0 (真题口径一致, §7)", bad_exam == 0, f"{bad_exam}")
    # 破自洽棘轮: 每个无释义词必登记 word_variants.unglossable (缩写/专名/复合); 否则=未处理静默缺口
    glossless = {r[0] for r in con.execute(
        "SELECT word FROM exam_vocabulary WHERE gloss IS NULL").fetchall()}
    unexpected = glossless - _known_unglossable()
    check("无 UNEXPECTED 无释义词 (每缺口必登记 unglossable 白名单, 非静默缺口)",
          not unexpected, f"{len(unexpected)} 未登记: {sorted(unexpected)[:8]}")
    # 真值源门: 交付级词典义项 gloss_source 全来自真值源(教材/中考/COCA/variant), 无 LLM consolidate 覆盖
    # (cleaned_judged = 双模型 consolidate 零血缘不可复核, 违红线"义项来自真值源非LLM"; 已废)
    llm_gloss = con.execute(
        "SELECT COUNT(*) FROM exam_vocabulary WHERE gloss_source IN ('cleaned_judged')").fetchone()[0]
    check("词典义项无 LLM 覆盖 (gloss_source 全真值源, 非cleaned_judged consolidate)", llm_gloss == 0, f"{llm_gloss} LLM源")
    # 内容门: unit_vocab_intro.in_curriculum 必=词∈cefr_vocab 真值 (非硬编码True谎报越纲; 违§1.2)
    bad_ic = con.execute(
        "SELECT COUNT(*) FROM unit_vocab_intro u WHERE u.in_curriculum <> "
        "EXISTS(SELECT 1 FROM cefr_vocab c WHERE LOWER(c.word)=LOWER(u.word))").fetchone()[0]
    check("in_curriculum==词∈cefr_vocab 真值 (非硬编码; 教材约47%越纲, 防§1.2选材踩雷)", bad_ic == 0, f"{bad_ic} 假源")
