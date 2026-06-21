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
        return out

    def self_test(self) -> bool:
        import duckdb
        c = duckdb.connect(":memory:")
        c.execute("CREATE TABLE word_glosses(gloss VARCHAR)")
        c.execute("CREATE TABLE exam_vocabulary(gloss VARCHAR)")
        c.execute("INSERT INTO word_glosses VALUES (?)", ["值得" + chr(0xF022) + "污染"])   # 注入PUA
        polluted = [d for d in self.check(c) if d.kind == "pollution"]
        c.execute("DELETE FROM word_glosses")
        c.execute("INSERT INTO word_glosses VALUES ('值得尊敬的')")
        clean = [d for d in self.check(c) if d.kind == "pollution"]
        c.close()
        return bool(polluted) and not clean
