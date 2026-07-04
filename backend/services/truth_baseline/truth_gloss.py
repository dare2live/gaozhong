"""释义污染真值校验器 (glossary 域; 模块化扩展示范 — 新域=加一个 checker, 核心不动).

教材生词表 zh_def 提取曾混入 PUA 音标/邻条 headword bleed (renjiao 5%);
glossary._clean_zh_def 保守清洗后应 0 PUA。本 checker 守门 + 防回归(污染重现→BLOCK)。
"""
from __future__ import annotations

from .base import Deviation, TruthChecker

_PUA = "[" + chr(0xE000) + "-" + chr(0xF8FF) + "]"   # Unicode 私用区 = OCR 音标乱码


def _pua_count(con, table: str) -> int:
    return con.execute(
        f"SELECT COUNT(*) FROM {table} WHERE gloss IS NOT NULL AND regexp_matches(gloss, ?)",
        [_PUA]).fetchone()[0]


def _no_cjk_count(con, table: str) -> int:
    """义项无中文字符 = 垃圾(OCR碎片如'（'/纯POS'modal'); 过'非空'门但无信息量."""
    return con.execute(
        f"SELECT COUNT(*) FROM {table} WHERE gloss IS NOT NULL AND TRIM(gloss)<>'' "
        "AND NOT regexp_matches(gloss, '[一-鿿]')").fetchone()[0]


def _truncated_sentinel_count(con, table: str) -> int:
    """义项含'真中文+垃圾截断哨兵后缀'复合污染 (2026-07-04坑: _no_cjk_count漏了这类——
    前缀是真中文过了'有无中文'门, 但整串仍是 scripts/extract_hujiao_vocab.py 未过滤掉的
    截断标记, glossary.build_glossary 应已剥离, 若此计数非0说明该剥离逻辑回归失效."""
    return con.execute(
        f"SELECT COUNT(*) FROM {table} WHERE gloss LIKE '%文本层截断待补全%'").fetchone()[0]


class GlossaryTruthChecker(TruthChecker):
    domain = "glossary"

    def check(self, con) -> list[Deviation]:
        out = []
        for tbl in ("word_glosses", "exam_vocabulary"):
            n = _pua_count(con, tbl)
            if n:
                out.append(Deviation("glossary", tbl, "pollution", "BLOCK",
                                     f"{tbl} 有 {n} 条 gloss 含 PUA 音标污染(教材OCR邻条bleed); "
                                     "应经 glossary._clean_zh_def 清洗"))
            g = _no_cjk_count(con, tbl)
            if g:
                out.append(Deviation("glossary", tbl, "pollution", "BLOCK",
                                     f"{tbl} 有 {g} 条 gloss 无中文字符(OCR碎片'（'/纯POS); "
                                     "_clean_zh_def 应去前导语法括号恢复中文, 无中文则跳过不入"))
            t = _truncated_sentinel_count(con, tbl)
            if t:
                out.append(Deviation("glossary", tbl, "pollution", "BLOCK",
                                     f"{tbl} 有 {t} 条 gloss 含'文本层截断待补全'哨兵后缀未被剥离; "
                                     "glossary.build_glossary 应已 strip 该后缀, 检查是否回归"))
        return out

    def self_test(self) -> bool:
        import duckdb
        c = duckdb.connect(":memory:")
        c.execute("CREATE TABLE word_glosses(gloss VARCHAR)")
        c.execute("CREATE TABLE exam_vocabulary(gloss VARCHAR)")
        c.execute("INSERT INTO word_glosses VALUES (?), ('（'), ('人人；…(文本层截断待补全)')",
                  ["值得" + chr(0xF022) + "污染"])  # 注入PUA + 无中文碎片 + 真中文但带截断哨兵后缀
        polluted = [d for d in self.check(c) if d.kind == "pollution"]
        c.execute("DELETE FROM word_glosses")
        c.execute("INSERT INTO word_glosses VALUES ('值得尊敬的')")
        clean = [d for d in self.check(c) if d.kind == "pollution"]
        c.close()
        return len(polluted) >= 3 and not clean
