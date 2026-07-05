"""教材单元语法点出现位置提取 (§1.2 不偏离学校: 每单元语法进度可执行).

真相源 = 教材 Grammar-kind section 标题/正文首行陈述的语法主题 (人教"Grammar 语法"附录双语标签 /
外研"Using language"英文主题); 经 backend/config/grammar_topic_map.yaml curated 映射到课标官方
grammar_items (标准术语等价非估算)。不命中 (歧义交际指令如"Talk about your future plans") →
**诚实跳过** (D0 返空>假推, 不强配)。单一计算点 (Rule 1): 从 sections+section_text 派生一次入表。
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import yaml

ROOT = Path(__file__).resolve().parents[3]
MAP_PATH = ROOT / "backend" / "config" / "grammar_topic_map.yaml"


def _load_rules() -> list[dict]:
    raw = yaml.safe_load(MAP_PATH.read_text(encoding="utf-8")) or {}
    return raw.get("rules") or []


def _match_topic(text: str, rules: list[dict]) -> str | None:
    """按 rules 顺序首匹配 (specific 在前) → grammar_item_id; 不命中 None."""
    low = text.lower()
    for rule in rules:
        for pat in rule.get("patterns", []):
            if pat.lower() in low:
                return rule["grammar_item_id"]
    return None


def extract_grammar_occurrences(con: duckdb.DuckDBPyConnection) -> dict:
    """Grammar section 语法主题 → 课标项 → grammar_occurrences (诚实跳过不命中)."""
    rules = _load_rules()
    valid_ids = {r[0] for r in con.execute("SELECT grammar_item_id FROM grammar_items").fetchall()}
    rows = con.execute("""
        SELECT s.version_key, s.volume_key, s.unit_number, t.raw_text
        FROM sections s JOIN section_text t
          ON t.version_key = s.version_key AND t.volume_key = s.volume_key
         AND t.unit_number = s.unit_number AND t.seq = s.seq
        WHERE s.kind = 'Grammar'
        ORDER BY 1, 2, 3
    """).fetchall()
    con.execute("DELETE FROM grammar_occurrences")
    out: list[tuple] = []
    seen: set = set()
    for ver, vol, un, txt in rows:
        # 坑29 (2026-07-04): 匹配窗口 160→300 字 — 部分教材(如外研"Using language")的
        # 语法主题名(如 "Attributive clauses")排在页首指令语之后, 160 字会截断掉主题名本身。
        # 坑(2026-07-05 教师视角审计): example_sentence 原只存前 120 字, 但多数单元的指令语
        # ("Look at the sentences..."/"Match the..."/"Decide which...")本身就占 100+ 字,
        # 120 字常常截在指令语中间、真正的例句(a.../b...字母标记句)还没出现就被切掉。改存整个
        # 已抓的 300 字窗口(复用同一次 fetch, 零额外成本), 让真例句有机会露出来; 仍全是指令语、
        # 300 字内也没有例句的单元, 由 backend/services/textbook_content.py._is_practice_instruction
        # 诊断降级(不展示), 不臆造边界。
        head = " ".join((txt or "").split())[:300]
        gid = _match_topic(head, rules)
        if not gid or gid not in valid_ids:
            continue  # 诚实跳过: 歧义交际指令 / 无清晰术语 / 映射目标无效
        key = (ver, vol, un, gid)
        if key in seen:
            continue
        seen.add(key)
        out.append((ver, vol, un, gid, head))
    con.executemany(
        "INSERT INTO grammar_occurrences VALUES (?, ?, ?, ?, ?, ?)",
        [(i + 1, *r) for i, r in enumerate(out)],
    )
    return {"grammar_sections": len(rows), "occurrences": len(out),
            "skipped": len(rows) - len(out)}
