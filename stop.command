#!/usr/bin/env bash
# 双击停止 backend server.

cd "$(dirname "$0")"

n=$(pgrep -f 'backend/api/main.py' | wc -l | tr -d ' ')
if [ "$n" -eq 0 ]; then
  echo "server 未运行"
else
  pkill -f 'backend/api/main.py'
  sleep 1
  echo "已停 $n 个 server 进程"
fi
read -n1 -p "按任意键关闭"
