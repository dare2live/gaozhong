#!/usr/bin/env bash
# 实质改动后的 commit + push 辅助 (配合 .cursor/rules/commit-push-discipline.mdc)
# 用法: bash scripts/tools/git/commit_push.sh "commit message"
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"
MSG="${1:-}"
if [[ -z "$MSG" ]]; then
  echo "usage: $0 \"commit message\"" >&2
  exit 2
fi
if [[ -z "$(git status --porcelain)" ]]; then
  echo "nothing to commit"
  exit 0
fi
git status --short
git add -u
# 常见新路径(不盲加全部 untracked)
git add \
  .cursor/rules/ \
  backend/ \
  data/structured/ \
  docs/RESUME.md \
  frontend/static/ \
  scripts/ \
  tests/ \
  .moth/ \
  2>/dev/null || true
git commit -m "$MSG"
git push -u origin HEAD
git status -sb
echo "OK: committed + pushed"
