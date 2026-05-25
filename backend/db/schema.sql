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

-- ====== 学生档案 (用户 2026-05-23: 不开学生端, 但要数据层) ======
-- 后续支持: 扫描录入 / OCR / 手动批量导入
CREATE TABLE IF NOT EXISTS students (
    student_id    VARCHAR PRIMARY KEY,    -- 内部 ID (e.g. "sy-2024-001")
    name          VARCHAR,                 -- 中文姓名 (扫描 OCR 后)
    school        VARCHAR,                 -- 学校名 (eg "沈阳市第二中学")
    city          VARCHAR,                 -- 14 地市之一 (→ liaoning_city_textbook_choice)
    grade         VARCHAR,                 -- "高一"/"高二"/"高三"
    class_id      VARCHAR,                 -- 班级编号 (校内)
    enroll_year   INTEGER,                 -- 入学年份
    created_at    VARCHAR,
    source        VARCHAR                  -- "scan_ocr" | "csv_import" | "manual" | "sso"
);
CREATE INDEX IF NOT EXISTS idx_students_school ON students(school);
CREATE INDEX IF NOT EXISTS idx_students_city ON students(city);

-- 学生答题日志 (从扫描卷面 OCR 或在线答题, 后续接入)
CREATE TABLE IF NOT EXISTS student_answers (
    answer_id      BIGINT PRIMARY KEY,
    student_id     VARCHAR NOT NULL,
    question_id    VARCHAR,                 -- → exam_questions OR synth_questions
    paper_id       VARCHAR,                 -- → exercise_papers (本次试卷)
    student_choice VARCHAR,                 -- 学生填的答案 (eg "A"/"B" 或文本)
    is_correct     BOOLEAN,
    answered_at    VARCHAR,
    source         VARCHAR                  -- "scan_ocr" / "online" / "manual_review"
);
CREATE INDEX IF NOT EXISTS idx_sa_student ON student_answers(student_id);
CREATE INDEX IF NOT EXISTS idx_sa_question ON student_answers(question_id);

-- 学生薄弱点 (派生自 student_answers 统计, 由 services/profile.py 算)
CREATE TABLE IF NOT EXISTS student_weakness (
    student_id     VARCHAR NOT NULL,
    concept_id     VARCHAR NOT NULL,        -- → nodes (word/grammar/theme)
    weakness_score DOUBLE,                  -- 0-1, 越高越弱
    sample_n       INTEGER,
    last_seen_at   VARCHAR,
    PRIMARY KEY (student_id, concept_id)
);

-- 扫描原件 (留 raw 文件路径, OCR 任务 queue)
CREATE TABLE IF NOT EXISTS scan_uploads (
    upload_id      VARCHAR PRIMARY KEY,
    student_id     VARCHAR,
    file_rel_path  VARCHAR NOT NULL,
    file_sha256    VARCHAR,
    upload_kind    VARCHAR,                 -- "answer_sheet" | "homework" | "essay"
    uploaded_at    VARCHAR,
    ocr_status     VARCHAR,                 -- "pending" | "done" | "failed"
    ocr_text_path  VARCHAR
);

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
