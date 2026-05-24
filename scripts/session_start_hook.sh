#!/usr/bin/env bash
# SessionStart hook — 新 session 开始时把 lessons 前几条 + 架构铁律前几条注入到 Claude context.
# 不靠用户提醒 (用户 2026-05-24).

PROJ="/Users/dp/Documents/M/gaozhong"
cd "$PROJ" 2>/dev/null || exit 0

cat <<'BANNER'
[session-start gaozhong]
────────────────────────────────────────────────
项目铁律 (docs/architecture.md §0 八条):
  1. 单一计算点 (派生事实只在 services/ 算 1 次入表)
  2. Canonical First (entity 必先 PK 表再谈关联)
  3. Edges 一等公民 (N:M 走 edges 表 + graph service)
  4. 模块化 (新功能先扩, 不新建; 用 codegraph query 查)
  5. 可复用 (≥2 处出现的逻辑必抽到 common)
  6. 可扩展 (schema 加列 + 不破; relation 走白名单)
  7. 不牵一发动全身 (fan-in>3 改前必 codegraph)
  8. 反模式禁令 (god-module 400L / CC>15 / inline 大块 / 'try: pass')

强制 hook:
  PreToolUse  改 god-module/fan-in>5 BLOCK
  UserPromptSubmit  git uncommitted 提醒
  Stop  数据 FAIL/复杂度/前端 inline 任一升级则阻断

新 session 必读 (按需):
  goal.md / CLAUDE.md / docs/architecture.md / docs/lessons_learned.md
  docs/data_completeness_report.md / docs/pr_checklist.md
────────────────────────────────────────────────
近期教训 (docs/lessons_learned.md 最新 5 条):
BANNER

# print last 5 lesson section headers
if [ -f docs/lessons_learned.md ]; then
  grep -E '^## L-' docs/lessons_learned.md | tail -5 | sed 's/^## /  · /'
fi

cat <<'TAIL'

完成"X" 前自检:
  □ init_db 0 FAIL
  □ 无新增 CC>10 函数
  □ 前端无新增 inline 大块
  □ claim 含 "覆盖率/趋势/模型/借鉴" 都有真证据
────────────────────────────────────────────────
TAIL

exit 0
