-- 07_versions.sql — 真相源版本注册表 (PIT §3.1; KG层横切机制, docs/kg_layer_design.md §3)
--
-- 单一新表承载: 逐年新卷追加 / 课标·教材·课程换版 / 血缘版本指针 / 松耦合.
-- 换版 = append 新行 + 老行 effective_to 收口, **不删不改旧行** (旧版 PIT 保留, 2018真题对齐旧版不被新版覆盖).
-- 键 = (kind, variant): 辽宁并发2教材(waiyan/renjiao) + 课标分学段(高中2017/义教2022) + 卷流(高考辽宁/中考沈阳) → 非(kind,year)唯一.
-- 不给业务表加版本列(那会 cascade); 派生边的版本指针塞 edges.evidence_json.lineage (奥卡姆, 不另起血缘宽表).
CREATE TABLE IF NOT EXISTS source_versions (
    version_id          VARCHAR PRIMARY KEY,   -- 语义ID 如 textbook:waiyan:2019 (版本无关下游引 concept_id, 此ID只在血缘指针出现)
    kind                VARCHAR NOT NULL,      -- curriculum | textbook | course | exam_paper
    variant             VARCHAR,               -- 并发流区分: textbook=publisher / exam_paper=卷流 / curriculum=学段; 单流=NULL
    label               VARCHAR NOT NULL,
    effective_from_year INTEGER NOT NULL,
    effective_to_year   INTEGER,               -- NULL = 至今
    manifest_ref        VARCHAR,               -- 指 build_manifest sha256/URL, 不重存文件
    supersedes          VARCHAR,               -- 上一版 version_id (换版链, 可空; P2 才用)
    notes               VARCHAR
);
CREATE INDEX IF NOT EXISTS idx_srcver_kind_variant_year ON source_versions(kind, variant, effective_from_year);
