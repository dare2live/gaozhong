#!/usr/bin/env bash
# M4->M5 接力演练脚本（课表/审计/接口 smoke）
# 目的：一条命令输出可复验证据，不替代复核收尾
set -euo pipefail

PROJECT_DIR="/Users/dp/Documents/M/gaozhong"
cd "$PROJECT_DIR"

PORT=8765
RUN_ID=""

while [ $# -gt 0 ]; do
  case "$1" in
    --run-id)
      RUN_ID="${2:-}"
      if [ -z "$RUN_ID" ]; then
        echo "❌ 缺少 --run-id 值"
        exit 1
      fi
      shift 2
      ;;
    --port)
      PORT="${2:-}"
      if [ -z "$PORT" ]; then
        echo "❌ 缺少 --port 值"
        exit 1
      fi
      shift 2
      ;;
    --help|-h)
      echo "用法: bash scripts/m4_m5_smoke.sh [--run-id <run_id>] [--port <port>]"
      exit 0
      ;;
    *)
      echo "❌ 未知参数: $1"
      echo "用法: bash scripts/m4_m5_smoke.sh [--run-id <run_id>] [--port <port>]"
      exit 1
      ;;
  esac
done

TS="$(date +%Y%m%d-%H%M%S)"
LOG="logs/m4_m5_smoke_${TS}.log"
mkdir -p logs

run_cmd() {
  local desc="$1"; shift
  echo "[SMOKE] $desc" | tee -a "$LOG"
  if "$@" >>"$LOG" 2>&1; then
    echo "  ✅ PASS" | tee -a "$LOG"
  else
    echo "  ❌ FAIL: $desc" | tee -a "$LOG"
    echo "  log => $LOG"
    exit 1
  fi
}

{
  echo "===== M4->M5 smoke ====="
  echo "time: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "project: $PROJECT_DIR"
  echo "log: $LOG"
  echo ""
} | tee "$LOG"

run_cmd "data_accuracy_check" python3 scripts/data_accuracy_check.py
run_cmd "stop_gate" bash scripts/stop_gate.sh
run_cmd "course/service smoke" sh -c "PYTHONPATH=. python3 tests/test_course_smoke.py"

if [ -n "$RUN_ID" ]; then
  run_cmd "verification protocol generate" \
    python3 scripts/tools/monitor/verification_protocol.py --generate --run-id "$RUN_ID"
fi

run_cmd "api payload gate" python3 scripts/api_payload_check.py --port "$PORT"

echo "===== END =====" | tee -a "$LOG"
echo "log: $LOG" | tee -a "$LOG"
