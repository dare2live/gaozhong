"""R5 R6 词汇分层 + 教材位置 — 4 层词集 + 反查 position.

层映射 (volume_key → layer):
  必修 1, 2          → G1   (高一 ~1200 词)
  必修 3, 选必 1, 2  → G2   (高二, G1 ∪)
  选必 3, 4          → G3   (高三, G2 ∪)
  cefr_vocab 其它    → G_FINAL  (高考前突击, G3 ∪ 课标补充)
"""
from __future__ import annotations

from functools import lru_cache

import duckdb

# volume_key → year_level (1/2/3)
VOLUME_TO_YEAR = {
    "bixiu_1": 1, "bixiu_2": 1,
    "bixiu_3": 2, "xuanze_1": 2, "xuanze_2": 2,
    "xuanze_3": 3, "xuanze_4": 3,
}

# year → layer (累计)
YEAR_TO_LAYERS = {
    1: ["G1", "G2", "G3", "G_FINAL"],         # G1 词在所有层都允许
    2: ["G2", "G3", "G_FINAL"],
    3: ["G3", "G_FINAL"],
    99: ["G_FINAL"],                            # 课标补充只在 G_FINAL
}

VOLUME_LABEL = {
    "bixiu_1": "必修1", "bixiu_2": "必修2", "bixiu_3": "必修3",
    "xuanze_1": "选必1", "xuanze_2": "选必2",
    "xuanze_3": "选必3", "xuanze_4": "选必4",
}

VERSION_LABEL = {"waiyan": "外研", "renjiao": "人教"}


@lru_cache(maxsize=4)
def allowed_words(layer: str) -> frozenset[str]:
    """返 layer 允许的所有词 (lowercase). R5 strict ⊆ 校验用."""
    raise RuntimeError("call allowed_words_for(con, layer) — needs DB con")


CEFR_LEVELS_PER_LAYER = {
    "G1":      ["义教"],
    "G2":      ["义教", "必修"],
    "G3":      ["义教", "必修", "选必"],
    "G_FINAL": ["义教", "必修", "选必"],   # cefr_vocab 实际无"选修", G_FINAL ≡ G3 词集 (差异在真题密集 + 模拟卷, 非新词)
}


def allowed_words_for(con: duckdb.DuckDBPyConnection, layer: str) -> set[str]:
    """R5 词集 = 初中基础词 ∪ unit_vocab_intro (按 volume → year) ∪ cefr_vocab (按 cefr_level)."""
    if layer not in ("G1", "G2", "G3", "G_FINAL"):
        raise ValueError(f"bad layer {layer}")
    words: set[str] = set()
    # (0) 初中+小学基础词 (所有层的基底, 从 junior_high/vocab 加载)
    words.update(_load_base_vocab())
    # (1) 教材展开词
    volumes: list[str] = [v for v, y in VOLUME_TO_YEAR.items() if layer in YEAR_TO_LAYERS[y]]
    if volumes:
        placeholders = ",".join("?" * len(volumes))
        rows = con.execute(
            f"SELECT DISTINCT LOWER(word) FROM unit_vocab_intro "
            f"WHERE volume_key IN ({placeholders})",
            volumes,
        ).fetchall()
        words.update(r[0] for r in rows)
    # (2) 课标 cefr_vocab (按 cefr_level 映射到 layer)
    cefr_levels = CEFR_LEVELS_PER_LAYER.get(layer, [])
    if cefr_levels:
        placeholders = ",".join("?" * len(cefr_levels))
        rows = con.execute(
            f"SELECT LOWER(word) FROM cefr_vocab WHERE cefr_level IN ({placeholders})",
            cefr_levels,
        ).fetchall()
        words.update(r[0] for r in rows)
    return words


@lru_cache(maxsize=1)
def _load_base_vocab() -> frozenset[str]:
    """加载初中+小学基础词汇 (所有层共享的基底). 从 data/junior_high/vocab/ 读取."""
    from pathlib import Path
    base_dir = Path(__file__).resolve().parents[3] / "data" / "junior_high" / "vocab"
    words: set[str] = set()
    for f in base_dir.glob("*.txt"):
        for line in f.read_text(encoding="utf-8").splitlines():
            w = line.strip().lower()
            if w and len(w) > 1:
                words.add(w)
    return frozenset(words)


def word_position(con: duckdb.DuckDBPyConnection, word: str) -> tuple[int, str] | None:
    """R6: 反查词的 (year_level, textbook_position).

    优先教材位置 (year 1/2/3 + 'XXX·必修Y·U?·Vocabulary'),
    否则课标补充 (year 99 + '课标·3500词表'),
    否则 None.
    """
    w = word.lower()
    row = con.execute(
        "SELECT version_key, volume_key, unit_number "
        "FROM unit_vocab_intro WHERE LOWER(word) = ? "
        "ORDER BY volume_key, unit_number LIMIT 1",
        [w],
    ).fetchone()
    if row:
        ver, vol, uno = row
        year = VOLUME_TO_YEAR.get(vol, 0)
        pos = f"{VERSION_LABEL.get(ver, ver)}·{VOLUME_LABEL.get(vol, vol)}·U{uno}·Vocabulary"
        return year, pos
    row = con.execute("SELECT 1 FROM cefr_vocab WHERE LOWER(word) = ? LIMIT 1", [w]).fetchone()
    if row:
        return 99, "课标·3500词表"
    return None


def grammar_position(con: duckdb.DuckDBPyConnection, grammar_id: str) -> tuple[int, str] | None:
    """R6 for grammar — 走 grammar_items 的 cefr_level 推 year."""
    row = con.execute(
        "SELECT cefr_level, label FROM grammar_items WHERE grammar_item_id = ? LIMIT 1",
        [grammar_id],
    ).fetchone()
    if not row:
        return None
    cefr, label = row
    year = {"义教": 1, "必修": 2, "选必": 3, "选修": 99}.get(cefr, 99)
    pos = f"课标·语法·{cefr}·{label}"
    return year, pos


def check_words_in_layer(con: duckdb.DuckDBPyConnection, words: list[str], layer: str) -> list[str]:
    """R5 strict: 返回不在 layer 词集的词 (陌生词列表). 空 = 通过."""
    allowed = allowed_words_for(con, layer)
    return [w for w in words if w.lower() not in allowed]


# ========== 词形变形展开 (超纲检测用) ==========

IRREGULAR_FORMS: dict[str, list[str]] = {
    "make": ["made","makes","making"], "take": ["took","taken","takes","taking"],
    "go": ["went","gone","goes","going"], "see": ["saw","seen","sees","seeing"],
    "say": ["said","says","saying"], "get": ["got","gotten","gets","getting"],
    "give": ["gave","given","gives","giving"], "know": ["knew","known","knows","knowing"],
    "think": ["thought","thinks","thinking"], "find": ["found","finds","finding"],
    "tell": ["told","tells","telling"], "become": ["became","becomes","becoming"],
    "leave": ["left","leaves","leaving"], "feel": ["felt","feels","feeling"],
    "hold": ["held","holds","holding"], "write": ["wrote","written","writes","writing"],
    "stand": ["stood","stands","standing"], "hear": ["heard","hears","hearing"],
    "run": ["ran","runs","running"], "pay": ["paid","pays","paying"],
    "sit": ["sat","sits","sitting"], "lead": ["led","leads","leading"],
    "grow": ["grew","grown","grows","growing"], "lose": ["lost","loses","losing"],
    "fall": ["fell","fallen","falls","falling"], "send": ["sent","sends","sending"],
    "build": ["built","builds","building"], "spend": ["spent","spends","spending"],
    "cut": ["cuts","cutting"], "rise": ["rose","risen","rises","rising"],
    "drive": ["drove","driven","drives","driving"], "buy": ["bought","buys","buying"],
    "wear": ["wore","worn","wears","wearing"], "choose": ["chose","chosen","chooses","choosing"],
    "break": ["broke","broken","breaks","breaking"], "speak": ["spoke","spoken","speaks","speaking"],
    "draw": ["drew","drawn","draws","drawing"], "begin": ["began","begun","begins","beginning"],
    "bring": ["brought","brings","bringing"], "catch": ["caught","catches","catching"],
    "meet": ["met","meets","meeting"], "keep": ["kept","keeps","keeping"],
    "mean": ["meant","means","meaning"], "show": ["showed","shown","shows","showing"],
    "throw": ["threw","thrown","throws","throwing"], "fly": ["flew","flown","flies","flying"],
    "sell": ["sold","sells","selling"], "eat": ["ate","eaten","eats","eating"],
    "drink": ["drank","drunk","drinks","drinking"], "sing": ["sang","sung","sings","singing"],
    "swim": ["swam","swum","swims","swimming"], "teach": ["taught","teaches","teaching"],
    "win": ["won","wins","winning"], "hit": ["hits","hitting"],
    "put": ["puts","putting"], "set": ["sets","setting"],
    "let": ["lets","letting"], "read": ["reads","reading"],
    "lie": ["lay","lain","lied","lies","lying"], "die": ["died","dies","dying"],
    "have": ["has","had","having"], "be": ["is","am","are","was","were","been","being"],
    "do": ["does","did","done","doing"],
    "child": ["children"], "man": ["men"], "woman": ["women"],
    "person": ["people"], "foot": ["feet"], "tooth": ["teeth"],
    "mouse": ["mice"], "life": ["lives"], "wife": ["wives"],
    "knife": ["knives"], "leaf": ["leaves"], "shelf": ["shelves"],
}


def expand_morphology(base_words: set[str]) -> frozenset[str]:
    """展开词集的所有合法变形 (规则+不规则). 用于超纲检测."""
    expanded = set(base_words)
    for w in base_words:
        # 不规则
        for form in IRREGULAR_FORMS.get(w, []):
            expanded.add(form)
        # 规则后缀
        expanded.add(w + "s")
        expanded.add(w + "es")
        expanded.add(w + "ed")
        expanded.add(w + "d")
        expanded.add(w + "ing")
        expanded.add(w + "er")
        expanded.add(w + "est")
        expanded.add(w + "ly")
        expanded.add(w + "ness")
        expanded.add(w + "ful")
        expanded.add(w + "less")
        expanded.add(w + "ment")
        expanded.add(w + "tion")
        expanded.add(w + "able")
        if w.endswith("e"):
            expanded.add(w[:-1] + "ing")
            expanded.add(w[:-1] + "ed")
            expanded.add(w + "r")
            expanded.add(w + "st")
        if w.endswith("y") and len(w) > 2 and w[-2] not in "aeiou":
            expanded.add(w[:-1] + "ies")
            expanded.add(w[:-1] + "ied")
            expanded.add(w[:-1] + "ier")
            expanded.add(w[:-1] + "iest")
            expanded.add(w[:-1] + "ily")
        if len(w) > 2 and w[-1] not in "aeiouxy" and w[-2] in "aeiou" and w[-3] not in "aeiou":
            expanded.add(w + w[-1] + "ed")
            expanded.add(w + w[-1] + "ing")
            expanded.add(w + w[-1] + "er")
            expanded.add(w + w[-1] + "est")
    return frozenset(expanded)


# 停用词 (不参与超纲检测)
_STOP_WORDS = frozenset({
    "a","an","the","is","am","are","was","were","be","been","being",
    "have","has","had","do","does","did","will","would","shall","should",
    "can","could","may","might","must","need","dare",
    "i","me","my","mine","we","us","our","ours","you","your","yours",
    "he","him","his","she","her","hers","it","its","they","them","their","theirs",
    "this","that","these","those","what","which","who","whom","whose",
    "where","when","how","why","not","no","and","or","but","if","as","for",
    "to","of","in","on","at","by","with","from","about","between",
    "through","during","before","after","above","below","up","down","out",
    "off","over","under","again","then","once","also","just","only",
    "own","same","still","well","back","even","now","so","very","too",
    "quite","rather","much","more","most","than","such","each","every",
    "all","both","few","many","some","any","other","another","nor","yet",
    "here","there","into","onto","upon",
})

import re as _re


def validate_content_vocab(con: duckdb.DuckDBPyConnection,
                           text: str, layer: str) -> list[str]:
    """R5 程序级超纲检测: 扫描文本中所有英语词, 返回超纲词列表 (含变形).

    空列表 = 全部合规. 非空 = 有超纲词, 必须修改内容.
    """
    allowed_base = allowed_words_for(con, layer)
    allowed_expanded = expand_morphology(allowed_base)
    all_expanded = allowed_expanded | _STOP_WORDS

    words_in_text = set(_re.findall(r"\b[a-z]{3,}\b", text.lower()))
    beyond = words_in_text - all_expanded
    # 排除非词汇项 (语法术语/格式标记/专有名词/考试用语/缩写)
    non_vocab = {"adj","adv","noun","verb","pronoun","preposition",
        "conjunction","subjunctive","inversion","clause","tense",
        "participle","gerund","infinitive","superlative","comparative",
        "countable","uncountable","singular","plural","passive","active",
        "determiners","demonstrative","antonym","synonym","collocation",
        "prefix","suffix","etymology","morphology","phonetic",
        # 考试专用
        "gaokao","sth","sb","eg","etc","vs","min","max","avg",
        # 教学内容中的中文拼音/人名
        "hua","chen","tanaka","smith","tom","mary","peter","john","alice","bob",
        # 地名
        "nasa","beijing","china","chinese","english","mars","africa","african",
        "asia","europe","american","british","french","german","spanish","japanese",
        "suez","panama","jezero","ohio","washington","perseverance","antarctica",
        "shackleton","titanic","alzheimer",
        # 缩写/符号词
        "don","doesn","didn","isn","aren","wasn","weren","hasn","hadn",
        "wouldn","couldn","shouldn","won","cannot","can",
        # 单位/数学
        "km","mph","pct","pdf","url","html","css"}
    beyond -= non_vocab
    return sorted(beyond)
