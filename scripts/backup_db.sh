#!/usr/bin/env bash
# DB 备份 (A9 交付运维: gaozhong.duckdb gitignored 且无自动备份; 真实学情/导入落库后一旦误删无恢复路径).
# 用法: bash scripts/backup_db.sh [keep_n]   默认保留最近 10 份。建议 launchd/cron 每日跑。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DB="$ROOT/data/db/gaozhong.duckdb"
BAK_DIR="$ROOT/data/db/backups"
KEEP="${1:-10}"

[ -f "$DB" ] || { echo "❌ DB 不存在: $DB"; exit 1; }
mkdir -p "$BAK_DIR"
TS="$(date +%Y%m%d_%H%M%S)"
DEST="$BAK_DIR/gaozhong_${TS}.duckdb"
cp "$DB" "$DEST"
echo "✅ 备份: $DEST ($(du -h "$DEST" | cut -f1))"

# 滚动保留最近 KEEP 份, 删更旧的
ls -1t "$BAK_DIR"/gaozhong_*.duckdb 2>/dev/null | tail -n +"$((KEEP + 1))" | while read -r old; do
  rm -f "$old"; echo "  清理旧备份: $(basename "$old")"
done
echo "现有备份: $(ls -1 "$BAK_DIR"/gaozhong_*.duckdb 2>/dev/null | wc -l | tr -d ' ') 份 (保留 $KEEP)"
