#!/usr/bin/env bash
# M5 weekly healthcheck wrapper with visible failure flag.
set -euo pipefail

PROJECT_DIR="/Users/dp/Documents/M/gaozhong"
cd "$PROJECT_DIR"

FLAG="${GAOZHONG_HEALTHCHECK_ALERT_FLAG:-/tmp/gaozhong_ALERT_weekly_healthcheck.flag}"
TS="$(date +%Y%m%d-%H%M%S)"
LOG="logs/gaozhong-weekly-healthcheck-wrapper-${TS}.log"
mkdir -p logs

set +e
bash scripts/weekly_healthcheck.sh "$@" > "$LOG" 2>&1
RC=$?
set -e

if [ "$RC" -eq 0 ]; then
  rm -f "$FLAG"
  {
    echo "[OK] weekly healthcheck passed"
    echo "time=$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    echo "log=$LOG"
    echo "flag_cleared=$FLAG"
  } | tee -a "$LOG"
  exit 0
fi

{
  echo "severity=P1"
  echo "project=$PROJECT_DIR"
  echo "time=$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "exit_code=$RC"
  echo "command=bash scripts/weekly_healthcheck.sh $*"
  echo "log=$LOG"
  echo "action=run health replay, inspect log, keep this flag until a passing wrapper run clears it"
} > "$FLAG"

if command -v osascript >/dev/null 2>&1; then
  osascript -e 'display notification "weekly_healthcheck failed; inspect /tmp/gaozhong_ALERT_weekly_healthcheck.flag" with title "gaozhong M5 alert"' >/dev/null 2>&1 || true
fi

cat "$FLAG" >&2
exit "$RC"
