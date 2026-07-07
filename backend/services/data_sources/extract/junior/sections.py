"""沪教初中 textbooks/units/sections/section_text → 对应表 (Phase E1, 2026-07-07 补初中教材结构地基).

产物源: data/junior_high/structured/hujiao_{units,sections,section_text}.jsonl
(scripts/extract_hujiao_sections.py 一次性PDF预处理) + data/junior_high/manifest/
textbook_manifest.jsonl(sha256+页数, scripts/build_manifest.py 已有产物)。写入**已有**表
textbooks/units/sections/section_text(不新建表), version_key='hujiao', 与高中
renjiao/waiyan 物理共存同一批表。

Rule1单一计算点边界说明: canonical.build_all/links.build_all(volume:节点+in_volume边的
"标准"创建点)在 init_db.py 里跑在本模块**之前**(高中Layer1/2), 那时初中textbooks/units
行还不存在, 故不会覆盖到初中。本模块在自己的 Layer 3x 时间点独立补齐同一批节点/边(严格
复用相同 concept_id 格式/attrs 结构, 只是换了触发时间点, 非重新发明规则), 避免"孤立
critical node"D0 门(坑, 见commit: 初版只建unit节点不建in_volume边, 触发该门FAIL)。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
S = ROOT / "data" / "junior_high" / "structured"
MANIFEST = ROOT / "data" / "junior_high" / "manifest" / "textbook_manifest.jsonl"
_VERSION = "hujiao"
_PUBLISHER_LABEL = "沪教牛津英语(广深沈)"


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.open(encoding="utf-8")]


def _sync_textbooks_and_volumes(con) -> int:
    """textbooks 行 + volume: 节点(同 canonical._build_volume_rows 口径, concept_id/attrs
    一致); manifest 已有 sha256(scripts/build_manifest.py 产物, 不重算), 页数读
    hujiao_textbook_pages.jsonl(scripts/extract_hujiao_sections.py 用 pdfplumber 实测,
    非估算)。"""
    con.execute("DELETE FROM textbooks WHERE version_key = ?", [_VERSION])
    pages_by_vol = {r["volume_key"]: r["pdf_pages"] for r in _load_jsonl(S / "hujiao_textbook_pages.jsonl")}
    rows = []
    node_rows = []
    for m in _load_jsonl(MANIFEST):
        vol = m["volume"]
        rows.append((_VERSION, vol, _PUBLISHER_LABEL, m["file"], m["sha256"], pages_by_vol.get(vol)))
        node_rows.append((
            f"volume:{_VERSION}/{vol}", "volume", f"{_PUBLISHER_LABEL} {vol}",
            json.dumps({"version": _VERSION, "volume_key": vol}, ensure_ascii=False),
        ))
    if rows:
        con.executemany(
            "INSERT INTO textbooks VALUES (?, ?, ?, ?, ?, ?)", rows)
        con.executemany("INSERT OR REPLACE INTO nodes VALUES (?, ?, ?, ?)", node_rows)
    return len(rows)


def _unit_concept_id(vol: str, unit_number: int) -> str:
    return f"unit:{_VERSION}/{vol}/U{unit_number}"


def _sync_units(con, units: list[dict]) -> None:
    """unit: 节点 + in_volume 边(同高中 links.build_unit_in_volume 口径)。"""
    node_rows = []
    edge_rows = []
    for u in units:
        cid = _unit_concept_id(u["volume_key"], u["unit_number"])
        attrs = '{"page_start": %d, "page_end": %d}' % (u["page_start"], u["page_end"])
        node_rows.append((cid, "unit", u["title"] or f"Unit {u['unit_number']}", attrs))
        edge_rows.append((cid, f"volume:{_VERSION}/{u['volume_key']}", 1.0, None))
    if node_rows:
        con.executemany("INSERT OR REPLACE INTO nodes VALUES (?, ?, ?, ?)", node_rows)
    con.execute("DELETE FROM edges WHERE relation='in_volume' AND src_id LIKE ?", [f"unit:{_VERSION}/%"])
    if edge_rows:
        con.executemany(
            "INSERT INTO edges (src_id, dst_id, relation, weight, evidence_json) "
            "VALUES (?, ?, 'in_volume', ?, ?)", edge_rows)


def load(con) -> dict:
    con.execute("DELETE FROM section_text WHERE version_key = ?", [_VERSION])
    con.execute("DELETE FROM sections WHERE version_key = ?", [_VERSION])
    con.execute("DELETE FROM units WHERE version_key = ?", [_VERSION])

    n_textbooks = _sync_textbooks_and_volumes(con)

    units = _load_jsonl(S / "hujiao_units.jsonl")
    for u in units:
        con.execute(
            "INSERT INTO units VALUES (?, ?, ?, ?, NULL, ?, ?, 'regex_min')",
            [_VERSION, u["volume_key"], u["unit_number"], u["title"],
             u["page_start"], u["page_end"]],
        )
    _sync_units(con, units)

    sections = _load_jsonl(S / "hujiao_sections.jsonl")
    for s in sections:
        con.execute(
            "INSERT INTO sections VALUES (?, ?, ?, ?, ?, NULL, ?, ?, FALSE, FALSE, FALSE)",
            [_VERSION, s["volume_key"], s["unit_number"], s["seq"], s["kind"],
             s["page_start"], s["page_end"]],
        )

    texts = _load_jsonl(S / "hujiao_section_text.jsonl")
    for t in texts:
        con.execute(
            "INSERT INTO section_text VALUES (?, ?, ?, ?, ?, ?)",
            [_VERSION, t["volume_key"], t["unit_number"], t["seq"],
             t["raw_text"], t["n_chars"]],
        )

    return {"初中textbooks新增": n_textbooks, "初中units新增": len(units),
            "初中sections新增": len(sections), "初中section_text新增": len(texts)}
