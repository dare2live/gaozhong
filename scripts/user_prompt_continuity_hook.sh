#!/usr/bin/env bash
# UserPromptSubmit hook — 提醒 Claude 先完成手头工作再回应新消息.
# 触发: 每次用户发消息.
# 输出: stderr (Claude Code 注入到 Claude context).
#
# 检测的"未完成":
#   1. git 工作树有 uncommitted 改动 (说明上一轮改完没 commit)
#   2. .claude/in_progress.md 存在且非空 (Claude 手动声明的"当前任务")
#   3. /tmp/claude-501/*/tasks/*.output 有 background task 还在跑

set -u
PROJ="/Users/dp/Documents/M/gaozhong"
cd "$PROJ" 2>/dev/null || exit 0

reminders=""

# 1. git uncommitted
n_dirty=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
if [ "$n_dirty" -gt 0 ]; then
  reminders="$reminders
  ⏳ git 有 $n_dirty 个未 commit 改动 — 先 commit 完手头工作再处理新消息"
fi

# 2. in_progress.md (Claude 手动维护)
if [ -f .claude/in_progress.md ] && [ -s .claude/in_progress.md ]; then
  ip=$(head -3 .claude/in_progress.md | tr '\n' ' ')
  reminders="$reminders
  ⏳ .claude/in_progress.md 声明当前焦点: $ip"
fi

# 3. background tasks unfinished (heuristic: recent .output files)
bg_count=$(find /tmp/claude-501 -name "*.output" -mmin -30 2>/dev/null | wc -l | tr -d ' ')
if [ "$bg_count" -gt 0 ]; then
  reminders="$reminders
  ⏳ 30 分钟内有 $bg_count 个 background task 输出 — 检查是否需收尾"
fi

if [ -n "$reminders" ]; then
  cat >&2 <<EOF
[continuity-hook] 收到新消息前请检查未完成工作:$reminders

  原则: 不要因新消息丢弃手头进度. 流程:
    (1) 先把现有改动 commit 或回滚到 clean state
    (2) 清空 .claude/in_progress.md (touch /dev/null)
    (3) 再开始新消息的工作
  例外: 新消息明确说"停止"/"先做X" → 才中断手头.
EOF
fi

exit 0
