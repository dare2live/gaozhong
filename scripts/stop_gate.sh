#!/usr/bin/env bash
# Stop hook gate (project local) — Claude 报"完成" 前自动跑 3 检.
# 触发: .claude/settings.local.json Stop event.
# 任一失败 exit 2 阻断 stop.

set -u
PROJ="/Users/dp/Documents/M/gaozhong"
cd "$PROJ" 2>/dev/null || exit 0

# 只在 git working tree 有 .py / *.sql / *.html / *.js 改动时跑
changed=$(git status --porcelain 2>/dev/null | grep -cE '\.(py|sql|html|js|css)$' || echo 0)
if [ "$changed" -eq 0 ]; then
  exit 0
fi

fails=""

# 1. D0 数据 audit FAIL + WARN 都 BLOCK (用户 2026-05-24 硬约束 100% 准)
if [ -f data/db/gaozhong.duckdb ]; then
  sev_counts=$(python3 -c "
import duckdb
try:
    con = duckdb.connect('data/db/gaozhong.duckdb', read_only=True)
    f = con.execute(\"SELECT COUNT(*) FROM audit_findings WHERE severity='FAIL'\").fetchone()[0]
    w = con.execute(\"SELECT COUNT(*) FROM audit_findings WHERE severity='WARN'\").fetchone()[0]
    print(f'{f} {w}')
except Exception:
    print('0 0')
" 2>/dev/null || echo '0 0')
  n_fail=$(echo "$sev_counts" | awk '{print $1}')
  n_warn=$(echo "$sev_counts" | awk '{print $2}')
  if [ "$n_fail" -gt 0 ]; then
    fails="$fails
  ❌ D0 违反: audit 有 $n_fail FAIL — 100% 准约束失败"
  fi
  if [ "$n_warn" -gt 0 ]; then
    fails="$fails
  ❌ D0 违反: audit 有 $n_warn WARN — 100% 准约束失败 (重归类成 OK 或修真问题)"
  fi
fi

# 1b. D0 强执行: data_accuracy_check.py 全数据校验
if [ -f data/db/gaozhong.duckdb ] && [ -f scripts/data_accuracy_check.py ]; then
  if ! python3 scripts/data_accuracy_check.py > /tmp/d0_check.log 2>&1; then
    fails="$fails
  ❌ D0 违反: scripts/data_accuracy_check.py 失败 — 看 /tmp/d0_check.log"
  fi
fi

# 2. complexity hot funcs (新增的, > old baseline)
hot_now=$(python3 scripts/lib/complexity_check.py \
  $(find backend scripts -name '*.py' -not -path '*/__pycache__/*' 2>/dev/null | tr '\n' ' ') 2>&1 \
  | grep -c 'WARN' || echo 0)
HOT_BASELINE=13   # 收紧 14→13 (2026-05-24 拆 3 老函数后, M6 持续收紧)
if [ "$hot_now" -gt "$HOT_BASELINE" ]; then
  fails="$fails
  ❌ CC>10 函数 $hot_now > baseline $HOT_BASELINE — 修后再 stop (或 update baseline)"
fi

# 3. 前端 inline block 阈值
n_big_inline=$(python3 -c "
import re, pathlib
n = 0
for p in pathlib.Path('frontend').glob('*.html'):
    t = p.read_text(encoding='utf-8')
    for block in re.findall(r'<script(?![^>]*src=)[^>]*>(.*?)</script>', t, re.DOTALL | re.IGNORECASE):
        if block.count(chr(10)) + 1 > 80: n += 1
    for block in re.findall(r'<style[^>]*>(.*?)</style>', t, re.DOTALL | re.IGNORECASE):
        if block.count(chr(10)) + 1 > 30: n += 1
print(n)
" 2>/dev/null || echo 0)
INLINE_BASELINE=4  # 现有重复 baseline; 不允许增
if [ "$n_big_inline" -gt "$INLINE_BASELINE" ]; then
  fails="$fails
  ❌ 前端 inline 大块 $n_big_inline > baseline $INLINE_BASELINE — 抽 common.js / css 后再 stop"
fi

if [ -n "$fails" ]; then
  cat >&2 <<EOF
[stop-gate] 阻断 stop, 必须修这些再 stop:$fails

通过条件:
  (1)  D0 audit 0 FAIL + 0 WARN  (任何 WARN 必须重归类 OK 或修)
  (1b) D0 data_accuracy_check.py 全通过  (词/语法/教案/图谱/关联 全 100%)
  (2)  CC>10 函数 ≤ $HOT_BASELINE  (跑 python3 scripts/lib/complexity_check.py <files>)
  (3)  前端 inline 大块 ≤ $INLINE_BASELINE  (抽到 common.js / common.css)

只有当当前改动让基线**变更恶化** 时才阻断; 持平或改善 OK.
临时绕过 (不推荐): echo > /tmp/skip_stop_gate (然后下次 stop 内自动重置)
EOF
  if [ ! -f /tmp/skip_stop_gate ]; then
    exit 2
  fi
  rm -f /tmp/skip_stop_gate
fi

exit 0
