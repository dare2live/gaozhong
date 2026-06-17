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

from backend.services.exam_vocab import province_exam_token_bags, word_inflections  # noqa: E402

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


def _classify_word(w: str, cefr: set, ln_v: set, ws_v: set, lemm) -> str:
    forms = word_inflections(w, lemm)   # 单一计算点: {w} ∪ lemmatize(v,n,a,r)
    if any(l in cefr for l in forms):
        return "课标屈折变形"
    if any(r in cefr for r in _deriv_roots(w)):
        return "课标派生"
    if _is_propnoise(w):
        return "专名/碎片"
    if forms & ln_v:
        return "真超纲·辽宁考过"
    return "真超纲·仅外省考过" if forms & ws_v else "真超纲·未考"


def classify(con, lemm) -> dict[str, str]:
    cefr = {r[0].lower() for r in con.execute("SELECT word FROM cefr_vocab").fetchall()}
    tb = {r[0].lower() for r in con.execute("SELECT DISTINCT word FROM unit_vocab_intro").fetchall()}
    ln_v, ws_v = province_exam_token_bags(con, lemm)   # 单一 tokenizer (§7 辽宁/外省)
    return {w: _classify_word(w, cefr, ln_v, ws_v, lemm) for w in sorted(tb - cefr)}


def main() -> int:
    from nltk.stem import WordNetLemmatizer  # 仅生成期依赖
    con = duckdb.connect(str(DB), read_only=True)
    try:
        rec = classify(con, WordNetLemmatizer())
    finally:
        con.close()
    OUT.write_text("\n".join(json.dumps({"word": w, "category": c}, ensure_ascii=False)
                             for w, c in rec.items()) + "\n", encoding="utf-8")
    from collections import Counter
    dist = Counter(rec.values())
    print(f"vocab_classification.jsonl: {len(rec)} 词")
    for k, v in dist.most_common():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
