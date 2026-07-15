"""人工核验 tests_phrase 边 — phrase_id ↔ 真题空.

与教材 introduces_phrase(出现) 物理隔离: 仅 curated jsonl 可建考查边;
禁止用文本共现或解析「考查搭配」类别桶 bulk 建边。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]
_CURATED = ROOT / "data/structured/exam_point/phrase_human_verified.jsonl"
PROV = "human_verified"
REL = "tests_phrase"


def _phrase_cid(canonical: str, phrase_type: str) -> str:
    """与 links_extra.build_introduces_phrase 同口径, 命中教材短语时复用节点."""
    sha = hashlib.sha1(f"{canonical}/{phrase_type}".encode("utf-8")).hexdigest()[:8]
    return f"phrase:{sha}"


def _norm(s: str) -> str:
    return " ".join((s or "").split()).strip().lower()


def _load_curated() -> list[dict]:
    if not _CURATED.exists():
        return []
    out = []
    for ln in _CURATED.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            out.append(json.loads(ln))
    return out


def _resolve_phrase_node(con: duckdb.DuckDBPyConnection, canonical: str, phrase_type: str) -> str:
    """优先复用教材 phrase 节点(label 精确/大小写不敏感); 否则建 exam 核验节点."""
    want = _norm(canonical)
    row = con.execute(
        "SELECT concept_id FROM nodes WHERE node_type='phrase' "
        "AND lower(trim(label)) = ? LIMIT 1",
        [want],
    ).fetchone()
    if not row and want:
        # 教材标签偶带中文后缀 e.g. so...that 结果状语
        row = con.execute(
            "SELECT concept_id FROM nodes WHERE node_type='phrase' "
            "AND lower(label) LIKE ? LIMIT 1",
            [want + "%"],
        ).fetchone()
    if row:
        return row[0]
    # 教材节点 type 可能与 curated 不同, 再试 sha(canonical/教材type) 无意义 —
    # label 未命中则新建, type 用 curated 的 exam_* 以免撞 introduces_phrase 的 sha.
    ptype = phrase_type if phrase_type.startswith("exam_") else f"exam_{phrase_type}"
    cid = _phrase_cid(canonical, ptype)
    if not con.execute("SELECT 1 FROM nodes WHERE concept_id=?", [cid]).fetchone():
        con.execute(
            "INSERT INTO nodes VALUES (?, ?, ?, ?)",
            [
                cid,
                "phrase",
                canonical,
                json.dumps(
                    {
                        "canonical": canonical,
                        "type": ptype,
                        "source": "human_verified_exam",
                    },
                    ensure_ascii=False,
                ),
            ],
        )
    return cid


def load_tests_phrase(con: duckdb.DuckDBPyConnection) -> dict:
    """读 curated → 确保 phrase 节点 → 替换全部 tests_phrase 边."""
    curated = _load_curated()
    con.execute(f"DELETE FROM edges WHERE relation='{REL}'")
    n_ok = n_skip = 0
    for row in curated:
        qid = row.get("question_id")
        canon = (row.get("canonical") or "").strip()
        if not qid or not canon:
            n_skip += 1
            continue
        src = f"question:{qid}"
        if not con.execute(
            "SELECT 1 FROM nodes WHERE concept_id=? AND node_type='question'", [src]
        ).fetchone():
            n_skip += 1
            continue
        dst = _resolve_phrase_node(con, canon, row.get("phrase_type") or "collocation")
        ev = {
            "provenance": PROV,
            "truth_source": "human_blank_vs_phrase_id",
            "blank_no": row.get("blank_no"),
            "year": row.get("year"),
            "answer_surface": row.get("answer_surface"),
            "canonical": canon,
            "note": row.get("note"),
        }
        con.execute(
            "INSERT INTO edges (src_id, dst_id, relation, weight, evidence_json) "
            "VALUES (?,?,?,?,?)",
            [src, dst, REL, 1.0, json.dumps(ev, ensure_ascii=False)],
        )
        n_ok += 1
    return {
        "relation": REL,
        "n_curated": len(curated),
        "n_edges": n_ok,
        "n_skipped": n_skip,
        "provenance": PROV,
    }


def tests_phrase_summary(con: duckdb.DuckDBPyConnection) -> dict:
    n = con.execute(f"SELECT COUNT(*) FROM edges WHERE relation='{REL}'").fetchone()[0]
    n_human = con.execute(
        f"SELECT COUNT(*) FROM edges WHERE relation='{REL}' "
        f"AND json_extract_string(evidence_json,'$.provenance')='{PROV}'"
    ).fetchone()[0]
    return {
        "n_tests_phrase_edges": n,
        "n_human_verified": n_human,
        "min_expected": 15,
        "pass": n >= 15 and n == n_human,
        "note": "仅 human_verified curated; 共现/类别桶仍不得 bulk 建边",
    }
