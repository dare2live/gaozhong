"""word_sense 本体 (master A1: 义项才是带 stage 的最小单位; docs/kg_layer_design §2).

真相源 = data/structured/word_sense/word_sense_judged.jsonl (404 跨阶段候选, 双模型锚定释义
判断 + 对抗验证防过度检测, 坑16)。142 确认跨阶段真多义 → word_sense 节点 + has_sense + expands_sense。
word_sense 节点/边带 provenance=dual_model_adversarial (LLM 推断层, 诚实标)。
⚠ 2026-06-21: 不再回写 exam_vocabulary.gloss(原 cleaned_judged): LLM consolidate 零血缘不可复核
(违用户红线"义项来自真值源非LLM"); 交付级词典义项保留确定性清洗的 word_glosses 真值源 (OCR 由
_clean_zh_def 确定性清洗, GlossaryTruthChecker 已锁0PUA, LLM 覆盖冗余)。
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

_ROOT = Path(__file__).resolve().parents[2]
_JUDGED = _ROOT / "data" / "structured" / "word_sense" / "word_sense_judged.jsonl"


def _sense_node(con, word: str, stage: str, senses: list, new_senses: list) -> int:
    cid = f"word_sense:{word}:{stage}"
    if con.execute("SELECT 1 FROM nodes WHERE concept_id=?", [cid]).fetchone():
        return 0
    attrs = {"word": word, "stage": stage, "senses": senses}
    if new_senses:
        attrs["new_senses"] = new_senses
    con.execute("INSERT INTO nodes VALUES (?, 'word_sense', ?, ?)",
                [cid, f"{word}（{stage}）", json.dumps(attrs, ensure_ascii=False)])
    return 1


def _edge(con, src: str, dst: str, rel: str, ev: dict) -> int:
    if con.execute("SELECT 1 FROM edges WHERE src_id=? AND dst_id=? AND relation=?",
                   [src, dst, rel]).fetchone():
        return 0
    con.execute("INSERT INTO edges (src_id, dst_id, relation, weight, evidence_json) VALUES (?,?,?,?,?)",
                [src, dst, rel, 1.0, json.dumps(ev, ensure_ascii=False)])
    return 1


def build_word_senses(con: duckdb.DuckDBPyConnection) -> dict:
    """142 确认跨阶段多义 → word_sense 节点+has_sense+expands_sense; 清洗释义回写词典."""
    rows = [json.loads(l) for l in _JUDGED.read_text(encoding="utf-8").splitlines() if l.strip()]
    n_node = n_has = n_exp = 0
    for w in rows:
        word = w["word"]
        # 不回写 exam_vocabulary.gloss: 交付级词典义项保留 word_glosses 真值源(确定性清洗),
        # 不用 LLM consolidate 覆盖(零血缘不可复核, 违红线; OCR 已由 _clean_zh_def 确定性处理)。
        if not w.get("is_cross_stage_multi"):
            continue
        wnode = f"word:{word}"
        if not con.execute("SELECT 1 FROM nodes WHERE concept_id=? AND node_type='word'", [wnode]).fetchone():
            continue
        n_node += _sense_node(con, word, "初中", w["jr_senses"], [])
        n_node += _sense_node(con, word, "高中", w["hs_senses"], w["new_senses"])
        ev = {"provenance": "gloss_derived"}
        n_has += _edge(con, wnode, f"word_sense:{word}:初中", "has_sense", ev)
        n_has += _edge(con, wnode, f"word_sense:{word}:高中", "has_sense", ev)
        n_exp += _edge(con, f"word_sense:{word}:初中", f"word_sense:{word}:高中", "expands_sense",
                       {"provenance": "dual_model_adversarial", "new_senses": w["new_senses"],
                        "derived_by": "word_sense_judge@workflow",
                        "source_artifact": "word_sense_judged.jsonl"})
    return {"word_sense 节点": n_node, "has_sense 边": n_has, "expands_sense 边": n_exp}
