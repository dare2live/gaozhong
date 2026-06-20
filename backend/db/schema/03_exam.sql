-- 03_exam.sql — 真题 + 审计 (域A 检验; exam_type 中考/高考判别)
-- (从 schema.sql 模块化拆分, 2026-06-20; 单库分模块, init_db 按序加载)
--
-- 设计 (K12 inc1, 防 blast-radius): 物理表 exam_questions_all 含中考+高考(exam_type 判别);
-- VIEW exam_questions = 高考过滤视图 → **现有 25+ 高考消费者零改动, 仍只见高考** (零回归);
-- VIEW zhongkao_questions = 中考视图。**写入只准对 exam_questions_all** (视图不可写), 读高考走 exam_questions。

-- ====== 真题物理表 (中考+高考, 辽宁卷锚定) ======

CREATE TABLE IF NOT EXISTS exam_questions_all (
    question_id    VARCHAR PRIMARY KEY,   -- 高考 "gb/..." / "pdf/..." ; 中考 "ZK-LN-YYYY-NN"
    year           INTEGER,
    province       VARCHAR,                -- "辽宁" / "全国 II" — 高考走 extraction/exam.py 推断; 中考="辽宁"
    paper_type     VARCHAR,                -- "新课标 II 卷" / "辽宁省统一(2024起...)"
    question_type  VARCHAR,                -- 高考: 完形|阅读|语法填空|读后续写 ; 中考: 阅读理解(四选一)|五选四|...
    raw_question   VARCHAR,                -- 题面 (可能含选项)
    answer         VARCHAR,
    analysis       VARCHAR,                -- 高考解析 ; 中考: 语篇填空逐空考点
    source_file    VARCHAR,
    source_index   INTEGER,
    source_repo    VARCHAR DEFAULT 'OpenLMLab/GAOKAO-Bench',
    exam_type      VARCHAR DEFAULT '高考'   -- 高考|中考|校本测评 — 检验来源模块判别维 (K12设计§1)
);
CREATE INDEX IF NOT EXISTS idx_exam_year ON exam_questions_all(year);
CREATE INDEX IF NOT EXISTS idx_exam_prov ON exam_questions_all(province);
CREATE INDEX IF NOT EXISTS idx_exam_type ON exam_questions_all(question_type);
CREATE INDEX IF NOT EXISTS idx_exam_examtype ON exam_questions_all(exam_type);

-- 高考视图 (= 原 exam_questions 同列形 11 列, 现有消费者零改动只见高考)
CREATE VIEW IF NOT EXISTS exam_questions AS
    SELECT question_id, year, province, paper_type, question_type, raw_question,
           answer, analysis, source_file, source_index, source_repo
    FROM exam_questions_all WHERE exam_type = '高考';

-- 中考视图 (含 exam_type, 给中考/K12 衔接消费者) + 派生 content_status (审计HIGH#8 空心诚实标记)
-- 单一计算点: 题面/答案完整性从 raw_question+answer 派生一次, 前端/分析统一消费, 不在各处重判。
-- CREATE OR REPLACE: 视图随 schema 更新 (加列后无需全量重建即生效)。
CREATE OR REPLACE VIEW zhongkao_questions AS
    SELECT *,
        CASE
            WHEN raw_question LIKE 'walled%' OR raw_question IS NULL OR TRIM(raw_question) = ''
                THEN 'stem_walled'      -- 题面门控/缺 (2024 免费源全门控, 仅官方答案可得; 诚实不伪造题面)
            WHEN answer IS NULL OR TRIM(answer) = ''
                THEN 'answer_pending'   -- 有题面缺答案 (2025 部分小题答案待补)
            ELSE 'complete'             -- 题面+答案俱全
        END AS content_status
    FROM exam_questions_all WHERE exam_type = '中考';

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
