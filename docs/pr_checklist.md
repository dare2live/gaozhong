# PR / Commit Checklist (每次"完成" 前必走)

> 用户 2026-05-24: "确保后续可持续使用, 不是每次都要我提醒".
> 配 Stop hook 自动跑 (`.claude/settings.local.json` 的 Stop event), 任一 FAIL 阻断 stop.

---

## 1. 数据治理真审计

```bash
python3 scripts/init_db.py 2>&1 | tail -5
```
要求:
- 审计行末 `0 FAIL` (任何 FAIL 必须修)
- WARN 数不增加 (新增 WARN 必须解释)

## 2. complexity 全扫无 hot func

```bash
python3 scripts/lib/complexity_check.py $(find backend scripts -name '*.py' -not -path '*/__pycache__/*' | tr '\n' ' ') 2>&1 | grep WARN | wc -l
```
要求:
- CC>10 函数数不增加
- 新增的函数 CC ≤ 10 (老遗留可豁免, 但每轮要清 1-2 个)

## 3. 前端复用检测

```bash
python3 -m backend.services.audit.frontend_dupe
```
要求:
- 任何 frontend/*.html 内 `<script>` 块 ≤ 80 L (超出抽 common.js)
- inline `<style>` 块 ≤ 30 L (超出抽 css)
- `fetch(` 重复 ≥ 2 文件未走 common.js → WARN

## 4. claim vs evidence 自检

每个 commit message / 完成汇报里说的"X 完成", 必须能 grep 到真数据:
- 说"覆盖率 X%" → 必须有 SQL 查询出处
- 说"模型分析" → 必须有 sklearn/numpy import + docs/*_analysis.md
- 说"借鉴 X 风格" → 必须有 docs/design_reference_X.md 拆解
- 说"打通了 X 链路" → 必须有 smoke test 真 200
- 说"M/G 项完成" → 必须 audit 真 OK

## 5. lessons / docs 更新

任何踩坑必写 L-编号:
- `docs/lessons_learned.md` 加条目 (现象/根因/自动化兜底/教训)
- 反复 ≥ 2 次的失误必须 hook 化, 不能只写在 lessons

任何新模块写 docstring + 在 architecture.md §2 模块表里登记 (如适用).

---

## Stop hook 实装 (本仓 .claude/settings.local.json)

```bash
bash scripts/stop_gate.sh
```

会跑 1-3, 失败 exit 2 阻断 stop. claim/evidence 自检靠 LLM 自律 + 用户抽查 (无法机器化).

---

## 反模式 (任何一条命中 = 不能 commit)

| 反模式 | 检测 | 修法 |
|---|---|---|
| 数据 audit 新增 FAIL | init_db 末尾 | 修, 不豁免 |
| frontend html 内嵌 100+ 行 JS | frontend_dupe audit | 抽 common.js |
| 新函数 CC>10 | complexity_check | 拆 helper |
| "完成" 汇报含 "覆盖率/趋势/模型/借鉴" 无证据 | 自检 (L-J) | 补真数据/真模型/reference doc |
| 用户重复反馈同一类问题 ≥ 2 次 | M-6 | hook 化, 不口头承诺 |
