-- 04_qbank_org.sql — 题库 + 教学组织 (题库/标签/教师/班级/试卷)
-- (从 schema.sql 模块化拆分, 2026-06-20; 单库分模块, init_db 按序加载)

-- ====== 题库 (用户 2026-05-24: 题库 + 标签 + 条件组卷, 替代 LLM 合成) ======

-- 统一题库 (真题 + 合成 + 教师手填都进这一张)
CREATE TABLE IF NOT EXISTS question_bank (
    qb_id          BIGINT PRIMARY KEY,
    origin         VARCHAR NOT NULL,         -- 'real' | 'rule_synth' | 'manual'
    origin_ref     VARCHAR,                   -- exam_questions.question_id 或 manual ID
    question_type  VARCHAR NOT NULL,         -- 含 listening_short / listening_dialog / listening_passage (5.5.B)
    stem           VARCHAR NOT NULL,
    options_json   VARCHAR,                   -- "[{label:'A',text:'...'},...]" or null (非选择)
    answer         VARCHAR,
    analysis       VARCHAR,
    difficulty     VARCHAR DEFAULT 'mid',     -- easy | mid | hard
    reviewed_by    VARCHAR,                   -- 老师 ID (人工 review 后填)
    created_at     VARCHAR NOT NULL,
    -- 5.5.B 听力扩字段 (用户 2026-05-24: 听力统一入题库, 不另起表)
    has_audio      BOOLEAN DEFAULT false,
    audio_id       VARCHAR,                   -- "audio:2024/A/Q1" lineage
    transcript     VARCHAR,                   -- 听力文字稿 (必填 if has_audio, audit_listening_transcript_required)
    audio_speakers VARCHAR,                   -- JSON: [{"id":"M","label":"男1"}]
    audio_duration INTEGER                    -- 秒
);
CREATE INDEX IF NOT EXISTS idx_qb_type ON question_bank(question_type);
CREATE INDEX IF NOT EXISTS idx_qb_origin ON question_bank(origin);
CREATE SEQUENCE IF NOT EXISTS qb_id_seq START 1;

-- 标签字典 (统一各类 tag)
CREATE TABLE IF NOT EXISTS tag_dictionary (
    tag_id         VARCHAR PRIMARY KEY,       -- 'word:abandon' / 'grammar:三/10/(3)/a' / 'theme:人与自然' / 'unit:waiyan/bixiu_1/U1' / 'year:2022' / 'difficulty:hard'
    tag_kind       VARCHAR NOT NULL,           -- 'word'|'grammar'|'theme'|'unit'|'year'|'difficulty'|'question_type'|'paper_section'
    label          VARCHAR NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tag_kind ON tag_dictionary(tag_kind);

-- 题 ↔ 标签 多对多
CREATE TABLE IF NOT EXISTS question_tags (
    qb_id          BIGINT NOT NULL,
    tag_id         VARCHAR NOT NULL,
    weight         DOUBLE DEFAULT 1.0,         -- 标签强度 (考点权重)
    PRIMARY KEY (qb_id, tag_id)
);
CREATE INDEX IF NOT EXISTS idx_qt_tag ON question_tags(tag_id);

-- 教师 / 班级 (M5 学生端推后, 但教师端是主交付)
CREATE TABLE IF NOT EXISTS teachers (
    teacher_id     VARCHAR PRIMARY KEY,
    name           VARCHAR,
    school         VARCHAR,
    city           VARCHAR,
    created_at     VARCHAR
);

CREATE TABLE IF NOT EXISTS classes (
    class_id       VARCHAR PRIMARY KEY,
    teacher_id     VARCHAR,
    school         VARCHAR,
    grade          VARCHAR,
    name           VARCHAR,
    created_at     VARCHAR
);

-- 试卷 (组卷器输出)
CREATE TABLE IF NOT EXISTS papers (
    paper_id       VARCHAR PRIMARY KEY,
    teacher_id     VARCHAR,
    class_id       VARCHAR,
    title          VARCHAR,
    spec_json      VARCHAR,                    -- 组卷条件
    created_at     VARCHAR
);
CREATE TABLE IF NOT EXISTS paper_questions (
    paper_id       VARCHAR NOT NULL,
    seq            INTEGER NOT NULL,
    qb_id          BIGINT NOT NULL,
    score          DOUBLE DEFAULT 1.0,
    PRIMARY KEY (paper_id, seq)
);
