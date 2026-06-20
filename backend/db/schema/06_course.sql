-- 06_course.sql — Lineage + 课程方案 + 设计宪法
-- (从 schema.sql 模块化拆分, 2026-06-20; 单库分模块, init_db 按序加载)

-- ====== Lineage / manifest (审计) ======

CREATE TABLE IF NOT EXISTS file_manifest (
    rel_path       VARCHAR PRIMARY KEY,
    file_type      VARCHAR NOT NULL,    -- textbook | curriculum | structured_repo | official_directory
    sha256         VARCHAR NOT NULL,
    size_bytes     BIGINT NOT NULL,
    source_url     VARCHAR,
    fetched_at     VARCHAR NOT NULL
);

-- ====== 第五阶段: 40 节课程方案 (5.5.A 3 新表) ======

-- 40 节课程定义 (init_db 从 backend/config/course_templates.yaml 灌, M3 数据外置)
CREATE TABLE IF NOT EXISTS courses (
    course_id          INTEGER PRIMARY KEY,            -- 1..40
    layer              VARCHAR NOT NULL,                -- G1 | G2 | G3 | G_FINAL  (R5)
    title              VARCHAR NOT NULL,
    block_kind         VARCHAR NOT NULL,                -- vocab|grammar|reading|cloze|gramfill|applied|narrative|mock|listening
    block_order        INTEGER NOT NULL,                -- 层内序号 1..10
    duration_min       INTEGER DEFAULT 120,
    listening_required BOOLEAN DEFAULT false,
    description        VARCHAR,
    themes_main        VARCHAR,                          -- 主选场景 (一句)
    themes_aux         VARCHAR                           -- JSON list: 副选场景 (R3)
);
CREATE INDEX IF NOT EXISTS idx_courses_layer ON courses(layer);
CREATE INDEX IF NOT EXISTS idx_courses_block_kind ON courses(block_kind);

-- 每节关联 graph 实体 / 题 (auto + manual 混合)
CREATE TABLE IF NOT EXISTS course_materials (
    course_id          INTEGER NOT NULL,
    seq                INTEGER NOT NULL,                -- 节内顺序 (≥1)
    kind               VARCHAR NOT NULL,                -- word|grammar|phrase|exam_question|reading_section|listening_clip
    ref_id             VARCHAR NOT NULL,                -- → nodes.concept_id 或 question_bank.qb_id
    year_level         INTEGER,                          -- 1|2|3|99 (99=课标补充)        R6
    textbook_position  VARCHAR,                          -- "外研·必修3·U2·Grammar"       R6
    source             VARCHAR,                          -- auto_from_trend | manual | from_scenario | from_lesson_plan
    reason             VARCHAR,                          -- eg "近 3 年真题 freq=5"
    PRIMARY KEY (course_id, seq)
);
CREATE INDEX IF NOT EXISTS idx_cm_kind ON course_materials(kind);
CREATE INDEX IF NOT EXISTS idx_cm_ref ON course_materials(ref_id);

-- 老师实际授课记录
CREATE TABLE IF NOT EXISTS course_sessions (
    session_id         VARCHAR PRIMARY KEY,
    course_id          INTEGER NOT NULL,
    class_id           VARCHAR,
    teacher_id         VARCHAR,
    taught_at          VARCHAR,
    notes              VARCHAR                           -- 课后笔记
);
CREATE INDEX IF NOT EXISTS idx_cs_course ON course_sessions(course_id);
CREATE INDEX IF NOT EXISTS idx_cs_class ON course_sessions(class_id);

-- ====== 设计宪法 (模型驱动内容生成, 用户 2026-05-25 硬约束) ======

CREATE TABLE IF NOT EXISTS constitution (
    rule_id        VARCHAR PRIMARY KEY,     -- P1 / V1 / PRINCIPLE_1 等
    rule_type      VARCHAR NOT NULL,        -- 'principle' | 'iron_law' | 'violation'
    title          VARCHAR NOT NULL,
    description    VARCHAR NOT NULL,
    enforcement    VARCHAR,                 -- 如何强制执行
    ref_section    VARCHAR,                 -- 对应宪法文档章节 (§1.2 等)
    sort_order     INTEGER NOT NULL DEFAULT 0
);
