-- 01_textbook.sql — 教材层 (域A 实现: unit/section/vocab/phrase)
-- (从 schema.sql 模块化拆分, 2026-06-20; 单库分模块, init_db 按序加载)

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
    extract_method VARCHAR,              -- 'outline' | 'regex_min' | 'empty' (STEP 2 textbook extractor)
    PRIMARY KEY (version_key, volume_key, unit_number)
);

-- 单元内 section (Reading/Listening/Writing/Project/...)
CREATE TABLE IF NOT EXISTS sections (
    version_key    VARCHAR NOT NULL,
    volume_key     VARCHAR NOT NULL,
    unit_number    INTEGER NOT NULL,
    seq            INTEGER NOT NULL,
    kind           VARCHAR NOT NULL,
    title          VARCHAR,
    page_start     INTEGER,
    page_end       INTEGER,
    is_narrative   BOOLEAN DEFAULT FALSE,   -- 标"叙事性" (读后续写复用源)
    is_applied     BOOLEAN DEFAULT FALSE,   -- 标"应用文"
    is_listening   BOOLEAN DEFAULT FALSE,   -- 标"听力素材"
    PRIMARY KEY (version_key, volume_key, unit_number, seq)
);
CREATE INDEX IF NOT EXISTS idx_sections_unit ON sections(version_key, volume_key, unit_number);

-- Section 文本 (page 范围抽出, 给短语/句型抽 + 后续 LLM 用)
CREATE TABLE IF NOT EXISTS section_text (
    version_key    VARCHAR NOT NULL,
    volume_key     VARCHAR NOT NULL,
    unit_number    INTEGER NOT NULL,
    seq            INTEGER NOT NULL,
    raw_text       VARCHAR NOT NULL,
    n_chars        INTEGER,
    PRIMARY KEY (version_key, volume_key, unit_number, seq)
);

-- 教材短语 / 句型 / 功能表达 (E, 规则版)
CREATE TABLE IF NOT EXISTS phrases (
    phrase_id      BIGINT PRIMARY KEY,
    version_key    VARCHAR NOT NULL,
    volume_key     VARCHAR NOT NULL,
    unit_number    INTEGER NOT NULL,
    canonical      VARCHAR NOT NULL,
    phrase_type    VARCHAR,                  -- verb_phrase | collocation | function_expression | sentence_pattern
    evidence       VARCHAR,                  -- 原句
    pattern_id     VARCHAR                    -- 来源模式 id
);
CREATE INDEX IF NOT EXISTS idx_phrases_unit ON phrases(version_key, volume_key, unit_number);
CREATE INDEX IF NOT EXISTS idx_phrases_canonical ON phrases(canonical);
CREATE SEQUENCE IF NOT EXISTS phrase_id_seq START 1;

-- 教材词条引入位置 (mapping 到 cefr_vocab)
-- in_curriculum 是 load 时占位; 实际真值由 links/build_introduces_word 算 (LEFT JOIN cefr_vocab)
CREATE TABLE IF NOT EXISTS unit_vocab_intro (
    version_key    VARCHAR NOT NULL,
    volume_key     VARCHAR NOT NULL,
    unit_number    INTEGER NOT NULL,
    word           VARCHAR NOT NULL,
    in_curriculum  BOOLEAN NOT NULL,
    pos            VARCHAR,
    zh_def         VARCHAR,
    raw_marker     VARCHAR,
    PRIMARY KEY (version_key, volume_key, unit_number, word)
);
CREATE INDEX IF NOT EXISTS idx_unit_vocab_word ON unit_vocab_intro(word);

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
