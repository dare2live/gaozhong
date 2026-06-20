-- 00_curriculum.sql — 课标 + 辽宁地市侧 (域A 脊柱)
-- (从 schema.sql 模块化拆分, 2026-06-20; 单库分模块, init_db 按序加载)

-- ====== 课标层 (master, 跨版本/跨地市共享) ======

CREATE TABLE IF NOT EXISTS cefr_vocab (
    word           VARCHAR PRIMARY KEY,
    cefr_level     VARCHAR NOT NULL,   -- 义教 | 必修 | 选必
    raw_suffix     VARCHAR,            -- ''/'*'/'**' (原标记)
    source         VARCHAR NOT NULL    -- '4.普通高中英语课程标准（2017年版2020年修订）.pdf 附录2'
);
CREATE INDEX IF NOT EXISTS idx_cefr_vocab_level ON cefr_vocab(cefr_level);

CREATE TABLE IF NOT EXISTS grammar_items (
    grammar_item_id VARCHAR PRIMARY KEY,  -- hierarchical "三/10/(3)/a"
    depth           INTEGER NOT NULL,
    parent_id       VARCHAR,              -- → grammar_items.grammar_item_id, NULL for depth=1
    category        VARCHAR,
    label           VARCHAR NOT NULL,
    cefr_level      VARCHAR NOT NULL,     -- 义教 | 必修 | 选必 | 选修
    seq             INTEGER,
    source          VARCHAR NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_grammar_depth ON grammar_items(depth);
CREATE INDEX IF NOT EXISTS idx_grammar_parent ON grammar_items(parent_id);

CREATE TABLE IF NOT EXISTS theme_contexts (
    theme_context_id VARCHAR PRIMARY KEY,  -- e.g. "人与自我/生活与学习"
    level1          VARCHAR NOT NULL,      -- 人与自我 | 人与社会 | 人与自然
    level2          VARCHAR,                -- 主题群
    level3          VARCHAR,                -- 子主题
    source          VARCHAR NOT NULL
);

-- ====== 辽宁地市侧 (truth source, 教材选用约束) ======

CREATE TABLE IF NOT EXISTS liaoning_allowed_publishers (
    rank           INTEGER,
    subject        VARCHAR NOT NULL,
    chief_editor   VARCHAR,
    publisher      VARCHAR NOT NULL,
    book_title     VARCHAR NOT NULL,
    volumes_json   VARCHAR NOT NULL,    -- ["必修 第一册",...]
    source         VARCHAR NOT NULL,
    PRIMARY KEY (subject, publisher)
);

CREATE TABLE IF NOT EXISTS liaoning_city_textbook_choice (
    city           VARCHAR NOT NULL,
    subject        VARCHAR NOT NULL,
    publisher_short VARCHAR NOT NULL,   -- "外研版" | "人教版"
    source         VARCHAR NOT NULL,
    PRIMARY KEY (city, subject)
);
