#!/usr/bin/env bash
# PreToolUse hook for Edit|Write|MultiEdit (registered in .claude/settings.local.json).
# Reads JSON from stdin, looks at file path, outputs stderr advisories.
# Non-blocking (always exit 0). Goal: 提醒 Claude/user 在改"重要文件"前先跑 codegraph
# 或 complexity check, 不强制 block.

set -u
input=$(cat)

# extract file_path; tolerate missing keys
file=$(printf '%s' "$input" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    f = d.get("tool_input", {}).get("file_path", "")
    print(f)
except Exception:
    pass
' 2>/dev/null)

[ -z "$file" ] && exit 0

# normalize to repo-relative if absolute under project root
case "$file" in
  /Users/dp/Documents/M/gaozhong/*) rel="${file#/Users/dp/Documents/M/gaozhong/}";;
  *) rel="$file";;
esac

# only check files we care about
critical=0
case "$rel" in
  backend/services/*|backend/db/*|backend/api/*|scripts/init_db.py|scripts/extract_*.py)
    critical=1
    ;;
esac

[ "$critical" -eq 0 ] && exit 0

# print structured stderr (Claude Code surfaces stderr to model)
if [ -f "$file" ]; then
  lines=$(wc -l < "$file" | tr -d ' ')
  funcs=$(grep -c '^def \|^class ' "$file" 2>/dev/null || echo 0)
  warn=""
  [ "$lines" -gt 250 ] && warn="$warn  · 行数 $lines > 250 (接近 god-module)"
  [ "$funcs" -gt 15 ] && warn="$warn  · 函数/类数 $funcs > 15"
  imports=$(grep -cE '^(import|from )' "$file" 2>/dev/null || echo 0)
  [ "$imports" -gt 15 ] && warn="$warn  · imports $imports > 15"

  echo "[precode-check] 即将修改关键文件: $rel" >&2
  echo "  size: $lines L · funcs/classes: $funcs · imports: $imports$warn" >&2

  # fan-in: who else imports this module? (cheap heuristic)
  modname=$(printf '%s' "$rel" | sed 's@/@.@g; s/\.py$//')
  fanin=$(grep -rEl "(^|from )$modname( |$)" backend/ scripts/ 2>/dev/null | grep -v "$file" | wc -l | tr -d ' ')
  [ "$fanin" -gt 0 ] && echo "  fan-in: $fanin 文件依赖此模块 — 改 API 前先看调用方" >&2

  # Cyclomatic complexity (stdlib ast, 仅 .py)
  case "$file" in
    *.py)
      cc_out=$(python3 /Users/dp/Documents/M/gaozhong/scripts/lib/complexity_check.py "$file" 2>/dev/null | head -5)
      hi_cc=$(echo "$cc_out" | grep -c '⚠️ WARN' || true)
      if [ "$hi_cc" -gt 0 ]; then
        echo "  complexity: 有 $hi_cc 函数 CC>10, top:" >&2
        echo "$cc_out" | grep -E 'CC=' | head -3 >&2
      fi
      ;;
  esac

  if [ "$lines" -gt 250 ] || [ "$funcs" -gt 15 ] || [ "$fanin" -gt 3 ] || [ "${hi_cc:-0}" -gt 2 ]; then
    echo "  >> 建议先跑 /codegraph-architecture-audit 看 hotspot 再改 (codegraph query <symbol>)" >&2
  fi
else
  echo "[precode-check] 新建文件: $rel — 写前请确认模块边界 (见 docs/architecture.md §2)" >&2
fi

exit 0
