#!/usr/bin/env bash
# 双击启动 — Mac Finder 双击此文件即可:
#   1. 切到项目目录
#   2. (首次) 自动 init DB
#   3. 后台启 backend
#   4. 浏览器打开教师端 + 主页 + 学生端

set -u
cd "$(dirname "$0")"

# 1. DB 不存在时自动建
if [ ! -f data/db/gaozhong.duckdb ]; then
  echo "[start] 首次启动, 跑 init_db (3-5 秒) ..."
  python3 scripts/init_db.py >/tmp/gaozhong_initdb.log 2>&1 || {
    echo "[start] init_db 失败, 看 /tmp/gaozhong_initdb.log"
    open /tmp/gaozhong_initdb.log
    read -n1 -p "按任意键退出"
    exit 1
  }
fi

# 2. 后台启 server (端口 8765)
PORT=8765
# 若占用先 kill
if lsof -i :$PORT >/dev/null 2>&1; then
  echo "[start] 端口 $PORT 被占用, 关旧 server"
  pkill -f 'backend/api/main.py' 2>/dev/null
  sleep 1
fi

mkdir -p logs
LOGFILE="logs/gaozhong-$(date +%Y%m%d-%H%M%S).log"
nohup python3 backend/api/main.py --host 127.0.0.1 --port $PORT \
  > "$LOGFILE" 2>&1 &
SERVER_PID=$!
echo "[start] server PID $SERVER_PID, log: $LOGFILE"

# 3. 等 server 就绪
for i in 1 2 3 4 5; do
  if curl -s -o /dev/null http://127.0.0.1:$PORT/api/stats 2>/dev/null; then
    echo "[start] server 就绪"
    break
  fi
  sleep 1
done

# 4. 浏览器开 /app 单入口 (5.1 统一 SPA)
echo "[start] 打开浏览器"
open "http://127.0.0.1:$PORT/app"

echo ""
echo "================================================================"
echo "  gaozhong 已启动 · http://127.0.0.1:$PORT/"
echo "  教师端: http://127.0.0.1:$PORT/teacher"
echo "  日志:   $LOGFILE"
echo ""
echo "  停止: 双击 stop.command  (或 pkill -f backend/api/main.py)"
echo "================================================================"
read -n1 -p "按任意键关闭此窗口 (不影响 server)"
