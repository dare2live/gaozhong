"""词性分布统计 (Rule5 共享helper, 2026-07-09 覆盖率审计后新增).

由来: 全库覆盖率审计发现 grammar_occurrences 表的"一/词类"+"二/构词法"两个taxonomy分支
永久0覆盖(高中108项/初中71项taxonomy里合计约33项), 根因是教材本身不会用术语显式讲解
"这是名词/这是介词"(英语词类是隐性习得, 非陈述式教学), 提取器(grammar_occurrence.py)
的"扫Grammar专题段"逻辑对此从设计上就不适用。

调研过3条补救路径, 前两条均否决:
  (a) 从 unit_vocab_intro.pos 反推塞进 grammar_occurrences —— 否决: 会制造假分层
      (如"数词覆盖0%"看着像教材不重视数词, 实际是自动词性标注工具对数词/代词/冠词的
      标注覆盖率历史偏低, 是工具局限非教材特征, 硬填等于用一个谎掩盖另一个真相)。
  (b) 扫非Grammar段落找术语提及 —— 否决: 教材里"noun/verb"等词几乎全部出现在题目
      操作指令("Match the nouns")里, 不是真实讲解, 抓取会把操作指令当成语法讲解。
  (c) 【本模块采用】诚实维持 grammar_occurrences 词类分支永久0覆盖(不删除/不臆造),
      词性信息该走 unit_vocab_intro.pos 这个已有、已验证(高中100%/初中99.7%标注率)
      的字段, 通过独立的"词性分布"视图呈现, 不污染grammar_occurrences框架。

单一计算点: 只读聚合调用方已fetch的vocab列表(每条含pos字段), 不重新查库(Rule1)。
"""
from __future__ import annotations

from collections import Counter

_POS_LABELS = {
    "n": "名词", "v": "动词", "vt": "及物动词", "vi": "不及物动词", "adj": "形容词",
    "adv": "副词", "prep": "介词", "conj": "连词", "pron": "代词", "num": "数词",
    "det": "冠词", "interj": "感叹词", "art": "冠词",
}


def pos_distribution(vocab: list[dict]) -> dict:
    """词性分布(仅统计已标注pos的词; vocab 须是已含 'pos' 键的词条列表, 不接受裸词表).

    诚实caveat内嵌返回体: 词性来自自动标注工具, 标注完整度不等于教学深度差异
    (2026-07-09调研实证: 数词/代词/冠词标注覆盖率历史偏低于名词/动词/形容词/副词,
    是标注工具局限, 不能读成"教材更重视名词轻视数词")。
    """
    counts = Counter(w["pos"] for w in vocab if w.get("pos"))
    n_tagged = sum(counts.values())
    return {
        "by_pos": [{"pos": p, "label": _POS_LABELS.get(p, p), "n": n} for p, n in counts.most_common()],
        "n_tagged": n_tagged,
        "n_untagged": len(vocab) - n_tagged,
        "caveat": "词性来自自动标注工具, 标注完整度不代表教学深度(数词/代词/冠词等标注覆盖率历史偏低是工具局限非教材特征)",
    }
