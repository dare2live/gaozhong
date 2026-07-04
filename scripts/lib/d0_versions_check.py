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
    _check_cumulative_words(con, check)


def _check_cumulative_words(con: duckdb.DuckDBPyConnection, check) -> None:
    """RC1后端审计#1 防回归: cumulative_words_learned 是 D0§1.2 '词量≤已学单元'越纲判断输入,
    原 volume_key=? 谓词把累计锁单册内每跨册重置(末单元低估~10x→误判可学词越纲)。
    断言 **as-served** city_curriculum 公式(非另写公式自证, 防绿门盖坏字段): 沿(册序,unit)单调非递减
    + 末单元≈整版本 distinct 词(running distinct 收敛全集)。"""
    from backend.services.recommend import city_curriculum
    bad = []
    for city in ("沈阳", "锦州"):   # 沈阳=外研 / 锦州=人教, 两版本都验
        r = city_curriculum(con, city)
        us = r.get("units") or []
        if not us:
            continue
        cums = [u["cumulative_words_learned"] for u in us]
        if any(cums[i] < cums[i - 1] for i in range(1, len(cums))):
            bad.append(f"{city}:累计跨册非单调(重置?)")
        tot = con.execute("SELECT COUNT(DISTINCT word) FROM unit_vocab_intro WHERE version_key=?",
                          [r["version_key"]]).fetchone()[0]
        if cums and cums[-1] != tot:
            bad.append(f"{city}:末单元累计{cums[-1]}≠整版本distinct{tot}")
    check("cumulative_words_learned 跨册 running distinct (单调+末≈整版本; 防单册重置低估越纲误判)",
          not bad, f"{bad}")


def check_liaoning_official_data(con: duckdb.DuckDBPyConnection, check) -> None:
    """坑17(2026-07-04全数据审计补): liaoning_allowed_publishers(辽宁省教育厅官方教学用书目录)
    + liaoning_city_textbook_choice(14地市选用版本对照, CLAUDE.md §4锚定) 此前D0/moth零覆盖
    (moth对后者仅有'聚合口径不漂移'类断言, 不校验原始行内容)。数据本身经查正确, 补内容锁防
    未来录入错误(如某市版本录反)无法被任何自动化门抓到。"""
    print("\n=== (39) 辽宁官方教材数据 (allowed_publishers + city_textbook_choice) ===")
    n_pub = con.execute("SELECT COUNT(*) FROM liaoning_allowed_publishers").fetchone()[0]
    check("liaoning_allowed_publishers = 8 (辽宁省教育厅2023年目录官方8个版本)", n_pub == 8, f"{n_pub}")
    cities = con.execute("SELECT city, publisher_short FROM liaoning_city_textbook_choice").fetchall()
    n_city = len(cities)
    check("liaoning_city_textbook_choice = 14 地市 (CLAUDE.md §4 锚定)", n_city == 14, f"{n_city}")
    dup_or_missing = 14 - len({c for c, _ in cities})
    check("14 地市不重不漏 (distinct city == 14)", dup_or_missing == 0, f"重复/缺失={dup_or_missing}")
    bad_pub = [c for c, p in cities if p not in ("外研版", "人教版")]
    check("publisher_short 只取 {外研版,人教版} (CLAUDE.md §4: 辽宁仅这两版本在用)",
          not bad_pub, f"越界: {bad_pub}")
    waiyan_cities = {c for c, p in cities if p == "外研版"}
    renjiao_cities = {c for c, p in cities if p == "人教版"}
    check("外研版10市/人教版4市 (CLAUDE.md §4 精确名单锁)",
          len(waiyan_cities) == 10 and renjiao_cities == {"锦州", "铁岭", "朝阳", "葫芦岛"},
          f"外研={sorted(waiyan_cities)} 人教={sorted(renjiao_cities)}")
