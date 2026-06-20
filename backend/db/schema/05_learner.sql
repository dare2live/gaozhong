-- 05_learner.sql — 学生数据 (域B 多租户: student/answer/weakness/scan, teacher_id 隔离)
-- (从 schema.sql 模块化拆分, 2026-06-20; 单库分模块, init_db 按序加载)

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
