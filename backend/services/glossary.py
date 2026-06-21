"""统一逐阶段释义词典 (word_sense 地基; 单一计算点 build_glossary 入 word_glosses).

真相源 (课标只有词无释义, 故释义全来自教材/词表):
  - 高中: unit_vocab_intro.zh_def (外研 waiyan / 人教 renjiao 教材生词表; volume_key→必修/选修)
  - 初中: hujiao_vocab.jsonl (沪教初中教材生词表; 待OCR 项跳过) + 中考英语词汇表.txt (补基础词)
docs/kg_layer_design §2 词汇维. word_sense 从同词跨阶段 gloss 比对长出 (power 初中=能量 → 高中+电力/控制力)。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
_HUJIAO = ROOT / "data" / "junior_high" / "structured" / "hujiao_vocab.jsonl"
_ZHONGKAO = ROOT / "data" / "structured" / "english-wordlists" / "中考英语词汇表.txt"

# 中考词汇表行: "ability [əˈbɪlɪtɪ] n. 能力;才能"  → word / pos / 中文释义
_ZK_LINE = re.compile(r"^([a-zA-Z][a-zA-Z\s()/.'\-]*?)\s*\[[^\]]*\]\s*"
                      r"([a-z]+\.?(?:\s*&\s*[a-z]+\.?)?)?\s*(.+)$")


def _volume_stage(volume_key: str) -> str:
    """教材册 → 阶段 (bixiu_N=高中必修 / xuanze_N=高中选修)."""
    return "高中选修" if volume_key.startswith("xuanze") else "高中必修"


_POS_KEEP = {"vi", "vt", "v", "n", "adj", "adv", "prep", "conj", "pron",
             "num", "art", "vb", "aux", "a", "int", "modal"}


def _clean_zh_def(zh: str) -> str:
    """清教材生词表 zh_def 的 OCR 污染 (renjiao 5%: PUA音标/邻条bleed/英文例句/章节头).

    保守: 截在首个 PUA 或首个非 POS 英文词 (邻条 headword/例句起点); **清空则保留原文**
    (防过删合法条如 'consist of 由…组成'/'& modal v. 胆敢')。小验证: 保守应用后残留 PUA=0。
    """
    s = re.sub("[" + chr(0xE000) + "-" + chr(0xF8FF) + "]", "", zh)         # 移除 PUA 音标乱码(全私用区; 移除非截断, 保前置PUA后的真释义如 e-mail)
    out = []
    for m in re.finditer(r"[A-Za-z]+\.?|[^A-Za-z]+", s):
        tok = m.group()
        if re.fullmatch(r"[A-Za-z]+\.?", tok) and tok.strip(". ").lower() not in _POS_KEEP:
            break                                          # 非 POS 英文词 = 邻条/例句 → 停
        out.append(tok)
    cleaned = re.sub(r"[\s；;,，&/]+$", "", "".join(out)).strip()
    return cleaned if cleaned else zh.strip()              # 保守: 过删则保留原文


def _parse_zhongkao() -> list[tuple]:
    """中考词汇表 → (word, pos, gloss); 补初中基础词释义 (生词表只列生词缺基础词)."""
    out = []
    for ln in _ZHONGKAO.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if len(ln) < 3:
            continue
        m = _ZK_LINE.match(ln)
        if m:
            w = m.group(1).strip().split("(")[0].strip().lower()
            gloss = m.group(3).strip()
            if w and gloss:
                out.append((w, (m.group(2) or "").strip(), gloss))
    return out


def build_glossary(con: duckdb.DuckDBPyConnection) -> dict:
    """组装 word_glosses (单一计算点); INSERT OR IGNORE 幂等, 多源各一行."""
    con.execute("DELETE FROM word_glosses")
    rows: list[tuple] = []
    # 高中: 教材生词表 (源=version_key, 阶段由册定)
    for vk, vol, w, pos, zh in con.execute(
        "SELECT version_key, volume_key, word, pos, zh_def FROM unit_vocab_intro "
        "WHERE zh_def IS NOT NULL AND zh_def <> ''").fetchall():
        rows.append((w.lower(), _volume_stage(vol), pos, _clean_zh_def(zh), vk))   # 清OCR污染(保守)
    # 初中: 沪教生词表 (待OCR 跳过)
    for ln in _HUJIAO.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        r = json.loads(ln)
        if r.get("zh_def") and r["zh_def"] != "待OCR":
            rows.append((r["word"].lower(), "初中", r.get("pos"), r["zh_def"], "hujiao"))
    # 初中: 中考词汇表 (补基础词; 同清 OCR 污染)
    for w, pos, gloss in _parse_zhongkao():
        rows.append((w, "初中", pos, _clean_zh_def(gloss), "中考词汇表"))
    # dedup on PK (word,stage,source): 同源同阶段一词多 unit → 取最长 gloss (信息最全)
    best: dict[tuple, tuple] = {}
    for w, st, pos, gloss, src in rows:
        k = (w, st, src)
        if k not in best or len(gloss) > len(best[k][3]):
            best[k] = (w, st, pos, gloss, src)
    con.executemany(
        "INSERT OR IGNORE INTO word_glosses (word, stage, pos, gloss, source) VALUES (?, ?, ?, ?, ?)",
        list(best.values()))
    n = con.execute("SELECT COUNT(*) FROM word_glosses").fetchone()[0]
    by_stage = dict(con.execute("SELECT stage, COUNT(*) FROM word_glosses GROUP BY stage").fetchall())
    cross = con.execute(
        "SELECT COUNT(*) FROM (SELECT word FROM word_glosses GROUP BY word "
        "HAVING COUNT(DISTINCT CASE WHEN stage='初中' THEN 1 ELSE 2 END) > 1)").fetchone()[0]
    return {"word_glosses 行": n, "by_stage": by_stage, "跨阶段词(word_sense候选)": cross}


def cross_stage_words(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """初中+高中都有释义的词 (word_sense 直接候选): 返回逐阶段 gloss 供比对."""
    rows = con.execute(
        "SELECT word, stage, gloss, source FROM word_glosses "
        "WHERE word IN (SELECT word FROM word_glosses WHERE stage='初中') "
        "AND word IN (SELECT word FROM word_glosses WHERE stage LIKE '高中%') "
        "ORDER BY word, stage").fetchall()
    out: dict[str, dict] = {}
    for w, st, gloss, src in rows:
        out.setdefault(w, {"word": w, "初中": [], "高中": []})
        out[w]["初中" if st == "初中" else "高中"].append(f"{gloss}({src})")
    return list(out.values())
