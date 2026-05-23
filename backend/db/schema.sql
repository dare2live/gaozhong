-- gaozhong DuckDB schema (与 gaokao .duckdb 完全独立, 不共享文件)
-- 设计原则: 课标层 = master truth, 教材层只做 mapping (不当 schema 定义者).
-- 详细说明见 docs/step2_extraction_plan.md "课标驱动" 章节.

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

-- ====== 教材层 (textbook artifact, 仅入仓的 2 个版本) ======

CREATE TABLE IF NOT EXISTS textbooks (
    version_key    VARCHAR NOT NULL,    -- waiyan | renjiao
    volume_key     VARCHAR NOT NULL,    -- bixiu_1 | xuanze_4
    publisher_label VARCHAR NOT NULL,
    pdf_rel_path   VARCHAR NOT NULL,
    pdf_sha256     VARCHAR NOT NULL,
    pdf_pages      INTEGER,
    PRIMARY KEY (version_key, volume_key)
);

CREATE TABLE IF NOT EXISTS units (
    version_key    VARCHAR NOT NULL,
    volume_key     VARCHAR NOT NULL,
    unit_number    INTEGER NOT NULL,    -- 0 for Welcome Unit
    title_en       VARCHAR,
    theme_context_id VARCHAR,           -- → theme_contexts(theme_context_id)
    page_start     INTEGER,
    page_end       INTEGER,
    PRIMARY KEY (version_key, volume_key, unit_number)
);

-- 教材词条引入位置 (mapping 到 cefr_vocab)
CREATE TABLE IF NOT EXISTS unit_vocab_intro (
    version_key    VARCHAR NOT NULL,
    volume_key     VARCHAR NOT NULL,
    unit_number    INTEGER NOT NULL,
    word           VARCHAR NOT NULL,    -- → cefr_vocab(word) if in_curriculum
    in_curriculum  BOOLEAN NOT NULL,
    pos            VARCHAR,
    zh_def         VARCHAR,
    raw_marker     VARCHAR,             -- 教材原标记 (*, △ 等)
    PRIMARY KEY (version_key, volume_key, unit_number, word)
);

-- 短语 / 句型 / 功能表达 (STEP 2 P5 输出)
CREATE TABLE IF NOT EXISTS phrases (
    phrase_id        BIGINT PRIMARY KEY,
    version_key      VARCHAR NOT NULL,
    volume_key       VARCHAR NOT NULL,
    unit_number      INTEGER NOT NULL,
    canonical        VARCHAR NOT NULL,
    phrase_type      VARCHAR,           -- 动词短语 | 搭配 | 习语 | 功能表达
    evidence_sentence VARCHAR,
    theme_context_id VARCHAR,
    oo_syllabus_words_json VARCHAR,     -- 表外词 JSON 数组
    extraction_status VARCHAR           -- keep | keep_extension | flag_for_human
);

-- 语法点出现位置 (mapping 到 grammar_items)
CREATE TABLE IF NOT EXISTS grammar_occurrences (
    occ_id           BIGINT PRIMARY KEY,
    version_key      VARCHAR NOT NULL,
    volume_key       VARCHAR NOT NULL,
    unit_number      INTEGER NOT NULL,
    grammar_item_id  VARCHAR NOT NULL,  -- → grammar_items(grammar_item_id)
    example_sentence VARCHAR
);

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

-- ====== 高考真题 (辽宁卷锚定) ======

CREATE TABLE IF NOT EXISTS exam_questions (
    question_id    VARCHAR PRIMARY KEY,   -- "gb/<file_basename>/<index>"
    year           INTEGER,
    province       VARCHAR,                -- "辽宁" / "全国 II" / "未知" — 走 extraction/exam.py 推断
    paper_type     VARCHAR,                -- "新课标 II 卷" / "全国卷" / etc
    question_type  VARCHAR,                -- 完形|阅读|语法填空|读后续写|MCQ|应用文|改错
    raw_question   VARCHAR,                -- 题面 (可能含选项)
    answer         VARCHAR,
    analysis       VARCHAR,
    source_file    VARCHAR,                -- 原 GAOKAO-Bench json 文件名
    source_index   INTEGER,                -- 原 example 数组下标
    source_repo    VARCHAR DEFAULT 'OpenLMLab/GAOKAO-Bench'
);
CREATE INDEX IF NOT EXISTS idx_exam_year ON exam_questions(year);
CREATE INDEX IF NOT EXISTS idx_exam_prov ON exam_questions(province);
CREATE INDEX IF NOT EXISTS idx_exam_type ON exam_questions(question_type);

-- ====== 审计 (cross-check 结果落表) ======

CREATE TABLE IF NOT EXISTS audit_findings (
    finding_id    BIGINT PRIMARY KEY,
    audit_kind    VARCHAR NOT NULL,    -- file_sha | vocab_recall | grammar_recall | cross_source | publisher_coverage
    severity      VARCHAR NOT NULL,    -- OK | WARN | FAIL
    target        VARCHAR,             -- file path / table.column / publisher 等
    expected      VARCHAR,
    actual        VARCHAR,
    delta         VARCHAR,
    note          VARCHAR,
    audited_at    VARCHAR NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_kind ON audit_findings(audit_kind, audited_at);

-- ====== Lineage / manifest (审计) ======

CREATE TABLE IF NOT EXISTS file_manifest (
    rel_path       VARCHAR PRIMARY KEY,
    file_type      VARCHAR NOT NULL,    -- textbook | curriculum | structured_repo | official_directory
    sha256         VARCHAR NOT NULL,
    size_bytes     BIGINT NOT NULL,
    source_url     VARCHAR,
    fetched_at     VARCHAR NOT NULL
);
