"""D0 真相源版本注册表完整性 (KG层横切机制; docs/kg_layer_design.md §3.1, 坑17).

锁 PIT 不变量: 每 (kind,variant) 内区间不重叠+无空洞+只末行可开(to=null)+同年唯一。
区间错 → effective_version 返多版/漏版 → 血缘指针错 → 整层 PIT 失真, 故 D0 门死守。
"""
from __future__ import annotations

import duckdb


def check_versions(con: duckdb.DuckDBPyConnection, check) -> None:
    print("\n=== (29) 真相源版本注册表 PIT 完整性 (KG层横切地基) ===")
    n = con.execute("SELECT COUNT(*) FROM source_versions").fetchone()[0]
    check("source_versions 已灌种子 (≥9 真实版本)", n >= 9, f"{n} 行")

    # 区间不重叠+无空洞: 每 (kind,variant) 按 from 排序, 相邻 to+1==下一 from, 仅末行可 to=null
    rows = con.execute(
        "SELECT kind, COALESCE(variant,''), version_id, effective_from_year, effective_to_year "
        "FROM source_versions ORDER BY kind, COALESCE(variant,''), effective_from_year").fetchall()
    streams: dict[tuple, list] = {}
    for kind, variant, vid, frm, to in rows:
        streams.setdefault((kind, variant), []).append((frm, to, vid))
    bad_overlap, bad_open = [], []
    for key, segs in streams.items():
        for i, (frm, to, vid) in enumerate(segs):
            is_last = i == len(segs) - 1
            if to is None and not is_last:
                bad_open.append(vid)                     # 开区间(to=null)只能是末行
            if not is_last:
                nxt_from = segs[i + 1][0]
                if to is None or to + 1 != nxt_from:     # 须 to+1==下一from (无空洞无重叠)
                    bad_overlap.append((vid, to, nxt_from))
    check("版本区间无重叠无空洞 (每 kind+variant 内相邻 to+1==下一 from)",
          not bad_overlap, f"{bad_overlap[:3]}")
    check("开区间(至今)只末行 (无中间悬挂 to=null)", not bad_open, f"{bad_open[:3]}")

    # 同 (kind,variant,year) 唯一: 抽样几个已知年验 effective_version 返单一 (no-overlap 的行为级确认)
    from backend.services.lineage import effective_version
    cases = [("exam_paper", 2021, "liaoning_gaokao"), ("exam_paper", 2018, "liaoning_gaokao"),
             ("curriculum", 2022, "gaozhong"), ("exam_paper", 2024, "shenyang_zhongkao")]
    miss = [c for c in cases if effective_version(con, c[0], c[1], c[2]) is None]
    check("effective_version 已知年解析到唯一版本 (PIT 行为级)", not miss, f"未解析: {miss}")
