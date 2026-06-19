"""S4 stage reconcile — 用初中真相源细分高中 word 的 stage (K12 双向贯通).

输入 (初中子系统抽取产物):
  小学 = 义务课标二级; 初中 = 义务课标三级(初中) ∪ 沪教6册词表; 高中 = cefr 必修/选必。
输出:
  data/junior_high/structured/stage_refined.jsonl  word → refined_stage (最早源=最权威)
  报告: 高中cefr义教级被细分 小学/初中 的量 + **语义扩展候选**(初中引入但高中必修/选修=词义跨阶段扩展, 如 power)。

stage 偏序 (最早引入=该词 stage): 小学 < 初中 < 高中必修 < 高中选修。
诚实(§1.3): 初中源有抽取缺口(课标CMap/沪教释义), 故 refined 是"≥2源可确证"的细分, 余留高中cefr原值。
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "junior_high" / "structured"
DB = ROOT / "data" / "db" / "gaozhong.duckdb"


def _load_sources() -> tuple[set, set]:
    yiwu = [json.loads(l) for l in (OUT / "curriculum_vocab.jsonl").open(encoding="utf-8")]
    xiao = {r["word"] for r in yiwu if r["stage"] == "小学"}
    chu = {r["word"] for r in yiwu if r["stage"] == "初中"}
    hj = {json.loads(l)["word"] for l in (OUT / "hujiao_vocab.jsonl").open(encoding="utf-8")}
    return xiao, (chu | hj)        # 初中 = 课标三级初中 ∪ 沪教


def _refined_stage(word: str, hs_stage: str, xiao: set, chu: set) -> str:
    """最早源 = 该词真实引入 stage。"""
    if word in xiao:
        return "小学"
    if word in chu:
        return "初中"
    return hs_stage or "未标"      # 初中源未见 → 留高中原值(义务教育/高中必修/选修/校本超纲)


def reconcile() -> dict:
    xiao, chu = _load_sources()
    c = duckdb.connect(str(DB), read_only=True)
    nodes = c.execute("SELECT concept_id, json_extract_string(attrs_json,'stage') "
                      "FROM nodes WHERE node_type='word' AND json_extract_string(attrs_json,'stage') IS NOT NULL").fetchall()
    c.close()
    rows, refined_cnt, expand_cand = [], 0, []
    for cid, hs_stage in nodes:
        w = cid.split(":", 1)[1]
        rs = _refined_stage(w, hs_stage, xiao, chu)
        rows.append({"word": w, "hs_stage": hs_stage, "refined_stage": rs})
        if rs != hs_stage:
            refined_cnt += 1
        # 语义扩展候选: 初中引入(小学/初中) 但高中标 必修/选修 → 词义跨阶段扩展(power)
        if rs in ("小学", "初中") and hs_stage in ("高中必修", "高中选修"):
            expand_cand.append(w)
    (OUT / "stage_refined.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return {"total": len(rows), "refined": refined_cnt,
            "by_refined": _dist(rows), "expand_candidates": len(expand_cand),
            "expand_sample": sorted(expand_cand)[:20]}


def _dist(rows: list[dict]) -> dict:
    from collections import Counter
    return dict(Counter(r["refined_stage"] for r in rows))


if __name__ == "__main__":
    r = reconcile()
    print(json.dumps(r, ensure_ascii=False, indent=2))
    print(f"\n语义扩展候选(初中引入·高中必修/选修, =power 类跨阶段词义扩展种子): {r['expand_candidates']} 个")
    print("→ 这些是 design §10 `expands_sense`/`collocates_into` 边的挖掘起点。")
