-- 02_graph.sql — 知识图谱 canonical (域A, 铁律3 edges一等公民)
-- (从 schema.sql 模块化拆分, 2026-06-20; 单库分模块, init_db 按序加载)

-- ====== 知识图谱核心 (架构 §0 Rule 3, edges 一等公民) ======

CREATE TABLE IF NOT EXISTS nodes (
    concept_id  VARCHAR PRIMARY KEY,    -- e.g. "word:apple", "grammar:三/10/(3)/a", "city:沈阳"
    node_type   VARCHAR NOT NULL,        -- word|grammar|theme|volume|unit|section|phrase|question|exam_year|publisher|city|cefr_level
    label       VARCHAR NOT NULL,        -- 展示名
    attrs_json  VARCHAR                  -- 额外属性 (pos/ipa/page/year 等)
);
CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(node_type);

CREATE SEQUENCE IF NOT EXISTS edge_id_seq START 1;
CREATE TABLE IF NOT EXISTS edges (
    edge_id        BIGINT PRIMARY KEY DEFAULT nextval('edge_id_seq'),
    src_id         VARCHAR NOT NULL,
    dst_id         VARCHAR NOT NULL,
    relation       VARCHAR NOT NULL,    -- cefr_level | introduces_word | tests_word | city_uses | ...
    weight         DOUBLE,
    evidence_json  VARCHAR,
    UNIQUE (src_id, dst_id, relation)
);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src_id, relation);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst_id, relation);
CREATE INDEX IF NOT EXISTS idx_edges_rel ON edges(relation);
