"""教材超纲词分层分类 — 词形归并 + 派生还原 + 高考核对 + 专名过滤 (自编教程地基).

产出 data/structured/vocab_classification.jsonl: 每个"教材词 NOT IN cefr_vocab(精确)"的词分到:
  - 课标屈折变形: 复数/时态/被动/-ing/比较级 还原后词根在课标 → 实为课标内 (非超纲)
  - 课标派生:    -ment/-tion/-ly/-ness... 还原词根在课标 → 课标派生 (词根已学)
  - 专名/碎片:   单字母 / 国名语言名 / 无元音缩写 → 非学习词汇
  - 真超纲·辽宁考过:  真超纲 ∧ (词或屈折形) 出现在辽宁真题 → 必教 (§7 最高优先)
  - 真超纲·仅外省考过: 真超纲 ∧ 仅外省真题 → 高值参考 (非辽宁确认)
  - 真超纲·未考:      真超纲 ∧ 无任何真题 → 教材装饰, 选学

真相源 = cefr_vocab(课标附录2) + unit_vocab_intro(教材) + exam_questions.raw_question(高考词汇)。
**nltk WordNet 仅生成期用** (词形归并); artifact 入库后 services/init_db 只读 jsonl, 运行时零依赖。
判断规则集中此处 (单一计算点); 教材/课标变更后重跑本脚本刷新 artifact。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.services.exam_vocab import word_exam_hits_from_edges, word_inflections  # noqa: E402

DB = ROOT / "data" / "db" / "gaozhong.duckdb"
OUT = ROOT / "data" / "structured" / "vocab_classification.jsonl"

# 国名/语言名 (专名, 非学习词汇; 数据化可扩)
NATION = {
    "arabic", "danish", "korean", "dutch", "spanish", "polish", "greek", "french",
    "german", "japanese", "italian", "russian", "chinese", "english", "american",
    "british", "african", "european", "asian", "latin", "swedish", "norwegian",
    "finnish", "turkish", "indian", "mexican", "canadian", "australian", "egyptian",
    "roman", "irish", "scottish", "welsh", "vietnamese", "thai", "brazilian",
}
KEEP = {"app", "dna", "nasa"}   # 像缩写但是常用词/已入题, 不当专名
_DERIV = [("ically", "ic"), ("ally", "al"), ("ment", ""), ("ness", ""), ("tion", "te"),
          ("tion", "t"), ("ation", "ate"), ("sion", "de"), ("ly", ""), ("ical", "ic"),
          ("ity", ""), ("ous", ""), ("ive", ""), ("ize", ""), ("er", ""), ("or", ""),
          ("ist", ""), ("ism", ""), ("able", ""), ("ible", ""), ("ful", ""), ("less", ""),
          ("ship", ""), ("hood", ""), ("al", "")]


def _deriv_roots(w: str) -> set[str]:
    s = set()
    for suf, rep in _DERIV:
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            s.add(w[:-len(suf)] + rep)
    return s


def _is_propnoise(w: str) -> bool:
    if len(w) < 2 or w in NATION:
        return True
    if w in KEEP:
        return False
    return len(w) <= 4 and not re.search("[aeiou]", w)   # 无元音缩写


def _classify_word(w: str, cefr: set, ln_edged: set, all_edged: set, lemm) -> str:
    forms = word_inflections(w, lemm)   # {w} ∪ lemmatize(v,n,a,r) — 仅判课标屈折变形
    if any(l in cefr for l in forms):
        return "课标屈折变形"
    if any(r in cefr for r in _deriv_roots(w)):
        return "课标派生"
    if _is_propnoise(w):
        return "专名/碎片"
    # 考过判定走 tests_word 边 (唯一真相, 与 node exam_status 同源 → 3源一致 by construction)
    if w in ln_edged:
        return "真超纲·辽宁考过"
    return "真超纲·仅外省考过" if w in all_edged else "真超纲·未考"


def classify(con, lemm) -> dict[str, str]:
    cefr = {r[0].lower() for r in con.execute("SELECT word FROM cefr_vocab").fetchall()}
    tb = {r[0].lower() for r in con.execute("SELECT DISTINCT word FROM unit_vocab_intro").fetchall()}
    hits = word_exam_hits_from_edges(con)   # 唯一真相=tests_word 边 (§7 辽宁/外省)
    # 后端审计 根因A: "辽宁考过"用 ln_tested(辽宁∧离散考点题型 考查), 非 ln(出现, 含阅读篇章内容词);
    # 与 exam_coverage core/HV_extra 同源同口径 → 3源一致 by construction (d0_exam_status 锁)。
    ln_edged = {w for w, h in hits.items() if h.get("ln_tested", 0) > 0}
    all_edged = {w for w, h in hits.items() if h["all"] > 0}
    return {w: _classify_word(w, cefr, ln_edged, all_edged, lemm) for w in sorted(tb - cefr)}


def build(con) -> dict:
    """生成 vocab_classification.jsonl (复用调用方 con — 不自开第二连接, 避 DuckDB 单写者冲突, 坑11)。

    P0-3 (2026-06-26 架构): 接进 init_db Layer 3w(tests_word 边建完后), 使新卷→超纲分层全自动,
    消除"重建→手跑 build_vocab→jsonl sha 变→file_manifest 失配→再重建"的级联(本文件 OUT 由
    load_file_manifest 排除 sha 锁, 因它是派生生成物非真相源)。输出确定序(classify 已 sorted)。
    """
    from nltk.stem import WordNetLemmatizer  # 仅生成期依赖
    rec = classify(con, WordNetLemmatizer())
    OUT.write_text("\n".join(json.dumps({"word": w, "category": c}, ensure_ascii=False)
                             for w, c in rec.items()) + "\n", encoding="utf-8")
    from collections import Counter
    return Counter(rec.values())


def main() -> int:
    con = duckdb.connect(str(DB), read_only=True)
    try:
        dist = build(con)
    finally:
        con.close()
    print(f"vocab_classification.jsonl: {sum(dist.values())} 词")
    for k, v in dist.most_common():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
