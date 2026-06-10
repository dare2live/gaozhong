# Milestone A 真值源清单（2021-2025）

本里程碑将真值抽样固定为以下 3 类来源，不进行人工猜测/估算补齐。

## 1) 结构化真值源
- ` /Users/dp/Documents/M/gaokao/data/structured/english_xgkii_2021_2025.jsonl `
  - 用途：2021~2025 辽宁真题结构化题干映射
  - 执行脚本加载字段：`year`, `question_type`, `stem`, `options`, `answer`, `analysis`, `id`

## 2) JSONL 校验源
- `data/gaokao_verified_xgkii_2023_2024.jsonl`
  - 用途：对 `exam_questions` 的可验证样本做交叉核验；不作为缺口填充来源
  - 执行脚本字段：`year`, `question_type`, `question`, `answer`, `analysis`, `source`, `source_file`

## 3) 数据库真值（待验）
- `data/db/gaozhong.duckdb` 内 `exam_questions`
  - 范围条件：`year 2021~2025` 且 `province LIKE '%辽宁%'`
  - 匹配策略：年份 + 题型 + token overlap 备援

## 4) 当前已知缺口（本轮）
- 2021: 19 条已提取真题，目标 55，缺口 36
- 2022: 0 条已提取真题，目标 55，缺口 55

## 5) 规则约束
- 缺口仅写入为 `status=in_truth_source_only`（保留 `needs_verification` 与 `source_file` 追溯）
- 非人工确认，不执行 `--import-missing`
- 报告必须带 `run_id`、`manifest` 与落盘路径
