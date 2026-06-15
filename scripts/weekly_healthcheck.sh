#!/usr/bin/env bash
# gaozhong 每周巡检（M5）脚本
# 用法: bash scripts/weekly_healthcheck.sh [--port 8765]
set -euo pipefail

PROJECT_DIR="/Users/dp/Documents/M/gaozhong"
cd "$PROJECT_DIR"

PORT=8765
if [ "${1:-}" = "--port" ]; then
  if [ -z "${2:-}" ]; then
    echo "❌ 缺少 --port 值"
    exit 1
  fi
  PORT="$2"
fi

TS="$(date +%Y%m%d-%H%M%S)"
OUT="logs/gaozhong-weekly-healthcheck-${TS}.log"
mkdir -p logs

{
  echo "===== Weekly Healthcheck ====="
  echo "time: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "project: $PROJECT_DIR"
  echo "port: $PORT"
  echo "log: $OUT"
  echo ""
} | tee "$OUT"

run_cmd() {
  local desc="$1"; shift
  echo "[CHK] $desc" | tee -a "$OUT"
  if "$@" >>"$OUT" 2>&1; then
    echo "  ✅ PASS" | tee -a "$OUT"
  else
    echo "  ❌ FAIL: $desc" | tee -a "$OUT"
    echo "----- tail ----" | tee -a "$OUT"
    tail -n 40 "$OUT" | tee -a "$OUT"
    exit 1
  fi
}

run_cmd "data_accuracy_check" python3 scripts/data_accuracy_check.py
run_cmd "stop_gate" bash scripts/stop_gate.sh
run_cmd "course smoke test" sh -c "PYTHONPATH=. python3 tests/test_course_smoke.py"

run_cmd "api payload gate" python3 scripts/api_payload_check.py --port "$PORT"

echo "===== END =====" | tee -a "$OUT"
