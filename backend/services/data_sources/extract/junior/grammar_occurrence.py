"""沪教牛津 教材单元语法主题 → grammar_occurrences (Phase E4, K12衔接lineage补全).

真相源: 46个Grammar-kind section标题里的"A/B/C <主题>"板块标注(教材自身标注, 非估算),
按 backend/config/hujiao_grammar_topic_map.yaml 人工核验的映射规则(逐条读原文核实, 见该
文件头注)匹配到71个初中课标语法项(grammar:jr:<id>)。不命中→诚实跳过(D0 返空>假推)。

单一计算点(Rule1): 复用 grammar_occurrences 表(与高中 extraction/grammar_occurrence.py
共用同一张表, version_key='hujiao' 区分), 复用 backend/config/*.yaml 判断数据化模式
(§3.5, 与高中 grammar_topic_map.yaml 同一套设计, 只是取材料不同教材版本)。

坑(2026-07-08 提取时发现, 记录防重踩): 正则粗筛"标题行首字母必须大写"的规则会把
"can and cannot"/"may and may not"这类合法(但小写开头)的语法主题标题, 和真实的误检
(练习题句子片段"dog will love you faithfully and bring")一起过滤/一起保留, 两者无法
用单一正则规则区分——最终对全部46个Grammar section原文逐条人工核对(非自动化判定"是不是
标题"), 手工YAML里排除了那1条误检。
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import yaml

ROOT = Path(__file__).resolve().parents[5]
MAP_PATH = ROOT / "backend" / "config" / "hujiao_grammar_topic_map.yaml"
_VERSION = "hujiao"

# "A/B/C <主题>" 板块标题行(教材自身格式); 排除已知的1条误检(练习题句子片段, 见YAML头注)。
_KNOWN_FALSE_POSITIVE = "dog will love you faithfully and bring"


def _load_rules() -> list[dict]:
    raw = yaml.safe_load(MAP_PATH.read_text(encoding="utf-8")) or {}
    return raw.get("rules") or []


def _match_topic(text: str, rules: list[dict]) -> list[str] | None:
    """按 rules 顺序首匹配(具体在前) → grammar_item_id 列表(通常1个, 部分主题合并2个概念)."""
    low = text.lower()
    for rule in rules:
        for pat in rule.get("patterns", []):
            if pat.lower() in low:
                gid = rule["grammar_item_id"]
                return gid if isinstance(gid, list) else [gid]
    return None


def _extract_topic_labels(raw_text: str) -> list[str]:
    """从 Grammar section 原文逐行提取 'A/B/C <主题>' 标题(人工核验规则, 见模块docstring)."""
    import re

    labels = []
    for ln in (raw_text or "").split("\n"):
        ln = ln.strip()
        m = re.match(r"^[A-E]\s+([A-Za-z][A-Za-z0-9 ,:;'-]{3,55})$", ln)
        if m:
            label = m.group(1)
            if label == _KNOWN_FALSE_POSITIVE:
                continue
            labels.append(label)
    return labels


def extract_junior_grammar_occurrences(con: duckdb.DuckDBPyConnection) -> dict:
    """沪教Grammar section主题 → grammar_occurrences(version_key='hujiao', 诚实跳过不命中)."""
    rules = _load_rules()
    valid_ids = {
        cid.split(":", 2)[-1]
        for (cid,) in con.execute(
            "SELECT concept_id FROM nodes WHERE concept_id LIKE 'grammar:jr:%'"
        ).fetchall()
    }
    rows = con.execute(
        "SELECT s.volume_key, s.unit_number, t.raw_text FROM sections s JOIN section_text t "
        "ON t.version_key=s.version_key AND t.volume_key=s.volume_key "
        "AND t.unit_number=s.unit_number AND t.seq=s.seq "
        "WHERE s.version_key=? AND s.kind='Grammar' ORDER BY 1, 2", [_VERSION],
    ).fetchall()
    con.execute("DELETE FROM grammar_occurrences WHERE version_key = ?", [_VERSION])
    max_occ = con.execute("SELECT COALESCE(MAX(occ_id), 0) FROM grammar_occurrences").fetchone()[0]
    out: list[tuple] = []
    seen: set = set()
    n_labels = n_skipped = 0
    for vol, un, txt in rows:
        for label in _extract_topic_labels(txt):
            n_labels += 1
            gids = _match_topic(label, rules)
            if not gids:
                n_skipped += 1
                continue
            for gid in gids:
                if gid not in valid_ids:
                    n_skipped += 1
                    continue
                key = (vol, un, gid)
                if key in seen:
                    continue
                seen.add(key)
                out.append((_VERSION, vol, un, gid, label))
    con.executemany(
        "INSERT INTO grammar_occurrences VALUES (?, ?, ?, ?, ?, ?)",
        [(max_occ + i + 1, *r) for i, r in enumerate(out)],
    )
    return {"Grammar section数": len(rows), "提取到的主题标题数": n_labels,
            "落库occurrences": len(out), "诚实跳过(无对应71项)": n_skipped}
