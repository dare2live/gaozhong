"""考试词典 (Canonical First; 词本体地基; docs/kg_layer_design §2).

"一本最小也最准的考试词典" = 课标∪教材真超纲 出现过的词本身, 每词溯回真相源。
单一计算点 build_exam_dictionary → exam_vocabulary 表。复用既有单算点不重造:
  课标=cefr_vocab / 教材=unit_vocab_intro+hujiao / 真超纲判定=vocab_classify.is_real_over /
  辽宁命中=exam_vocab.word_exam_hits_from_edges / 阶段=refined_stage / 释义=word_glosses。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import duckdb
import yaml

from backend.services.exam_vocab import word_exam_hits_from_edges
from backend.services.stage_labels import CEFR_LEVEL_STAGE
from backend.services.vocab_classify import is_real_over

_ROOT = Path(__file__).resolve().parents[2]
_REFINED = _ROOT / "data" / "junior_high" / "structured" / "stage_refined.jsonl"
_COCA = _ROOT / "data" / "structured" / "english-wordlists" / "COCA_with_translation.txt"
_VARIANTS = _ROOT / "backend" / "config" / "word_variants.yaml"
_LEVEL_STAGE = CEFR_LEVEL_STAGE   # cefr_level→stage 标签单点 (stage_labels.py)
_COCA_POS = re.compile(r"^(n|v|vt|vi|adj|adv|art|prep|conj|pron|num|aux|int|abbr|a)\.")


def _is_coca_gloss_line(ln: str) -> bool:
    """COCA 释义行 = pos 前缀 或 含中文 (区别于词行)."""
    return bool(_COCA_POS.match(ln)) or any("一" <= c <= "鿿" for c in ln)


_COCA_POS_SEG = r"(?=(?:^|\s)(?:n|adj|adv|vt|vi|v|abbr|art|prep|pron|num|conj|int|aux)\.\s)"


def _strip_coca_pn(gloss: str) -> str:
    """剥 COCA 释义尾部专名段(人名/地名音译, 如'n. (Bad)人名；(罗)巴德'/'n. （英）多（人名）')。
    按 POS 段切, 丢含'人名'/'地名'的段(专名总在真义项之后); 全删则保留原文(防过删)。
    """
    parts = re.split(_COCA_POS_SEG, gloss)
    kept = [p for p in parts if not re.search(r"[人地]名", p)]
    out = re.sub(r"[\s；;,，]+$", "", "".join(kept)).strip()
    return out if out and any("一" <= c <= "鿿" for c in out) else gloss


def _flush_coca(out: dict, cur: str | None, buf: list) -> None:
    if cur and buf:
        out.setdefault(cur, _strip_coca_pn(" ".join(buf)))


def _coca_glosses() -> dict[str, str]:
    """COCA 全量带译词表 → {word: gloss} (兜底常见词; 教材/中考表跳过的基础词在此).

    格式: 词行(纯字母) + 紧跟释义行(pos. 中文译). 比 OALD8 abridged 全(不跳常见词)。
    """
    if not _COCA.exists():
        return {}
    out: dict[str, str] = {}
    cur, buf = None, []
    for ln in (x.strip() for x in _COCA.read_text(encoding="utf-8", errors="replace").splitlines()):
        if re.fullmatch(r"[a-zA-Z][a-zA-Z-]*", ln):           # 词行 → 收上一词
            _flush_coca(out, cur, buf)
            cur, buf = ln.lower(), []
        elif cur and ln and _is_coca_gloss_line(ln):
            buf.append(ln)
    _flush_coca(out, cur, buf)
    return out


def _word_variants() -> dict[str, str]:
    """词形变体 → 规范形 (释义继承用; 判断数据化 §3.5, backend/config/word_variants.yaml)."""
    if not _VARIANTS.exists():
        return {}
    cfg = yaml.safe_load(_VARIANTS.read_text(encoding="utf-8")) or {}
    return {v: d["canonical"] for v, d in (cfg.get("variants") or {}).items()}


def _refined_stages() -> dict[str, str]:
    if not _REFINED.exists():
        return {}
    return {json.loads(l)["word"].lower(): json.loads(l)["refined_stage"]
            for l in _REFINED.read_text(encoding="utf-8").splitlines() if l.strip()}


def _textbook_words(con) -> set[str]:
    hs = {r[0].lower() for r in con.execute("SELECT DISTINCT word FROM unit_vocab_intro").fetchall()}
    jr = {r[0].lower() for r in con.execute(
        "SELECT DISTINCT word FROM word_glosses WHERE stage='初中'").fetchall()}
    return hs | jr


def _direct_gloss(con, word: str, coca: dict[str, str]) -> tuple[str | None, str | None]:
    """直接释义: 教材生词表→中考表 优先(真相源准), 缺则 COCA 兜底(全量基础词)."""
    r = con.execute(
        "SELECT gloss, source FROM word_glosses WHERE word=? "
        "ORDER BY CASE WHEN stage LIKE '高中%' THEN 0 ELSE 1 END, LENGTH(gloss) DESC LIMIT 1",
        [word]).fetchone()
    if r:
        return r[0], r[1]
    if word in coca:                                          # 兜底: 教材/中考表跳过的基础常见词
        return coca[word], "COCA"
    return None, None


def _best_gloss(con, word: str, coca: dict[str, str],
                variants: dict[str, str]) -> tuple[str | None, str | None]:
    """释义交叉引用 (用户思路): 直接源→变体规范形继承. 优先高中(义项更全)→初中, 多源取最长.

    末环 variant 继承: 课标用英式/屈折形(colour/children)做词条, 教材/COCA 只 gloss 规范形
    → 经确定性变体规则继承规范形释义 (gloss 仍来自真值源, 非 LLM 生成义项, 守红线)。
    """
    gloss, src = _direct_gloss(con, word, coca)
    if gloss:
        return gloss, src
    canon = variants.get(word)                                # 末环: 变体 → 规范形释义
    if canon:
        g2, _ = _direct_gloss(con, canon, coca)
        if g2:
            return g2, f"variant:{canon}"
    return None, None


def build_exam_dictionary(con: duckdb.DuckDBPyConnection) -> dict:
    """组装 exam_vocabulary (课标∪教材真超纲, 真题作旗); 单一计算点, 幂等重建."""
    con.execute("DELETE FROM exam_vocabulary")
    cefr = {r[0].lower(): r[1] for r in con.execute("SELECT word, cefr_level FROM cefr_vocab").fetchall()}
    textbook = _textbook_words(con)
    hits = word_exam_hits_from_edges(con)         # {word: {ln, all}}
    stages = _refined_stages()
    coca = _coca_glosses()                         # 释义兜底 (全量基础词)
    variants = _word_variants()                    # 末环: 变体词条继承规范形释义
    # 最小最准: 课标 ∪ 真实教材超纲 (proper-noun/屈折噪声经 is_real_over 滤除)
    universe = set(cefr) | {w for w in (textbook - set(cefr)) if is_real_over(w)}
    rows = []
    for w in sorted(universe):
        in_cur, in_tb = w in cefr, w in textbook
        ln = int(hits.get(w, {}).get("ln", 0))
        flags = [k for k, v in (("curriculum", in_cur), ("textbook", in_tb), ("exam", ln > 0)) if v]
        stage = stages.get(w) or _LEVEL_STAGE.get(cefr.get(w), None)
        gloss, gsrc = _best_gloss(con, w, coca, variants)
        rows.append((w, in_cur, cefr.get(w), in_tb, ln > 0, ln, stage, gloss, gsrc, ",".join(flags)))
    con.executemany(
        "INSERT OR REPLACE INTO exam_vocabulary "
        "(word, in_curriculum, curriculum_level, in_textbook, in_exam, gaokao_hit_ln, "
        " stage, gloss, gloss_source, source_flags) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    n = len(rows)
    cov = con.execute("SELECT COUNT(*) FROM exam_vocabulary WHERE gloss IS NOT NULL").fetchone()[0]
    by_gsrc = dict(con.execute(
        "SELECT COALESCE(gloss_source,'(无)'), COUNT(*) FROM exam_vocabulary GROUP BY 1 ORDER BY 2 DESC").fetchall())
    return {"考试词典 词数": n, "有释义": cov, "释义覆盖率": f"{100 * cov // max(n, 1)}%",
            "释义来源分布": by_gsrc}
