#!/usr/bin/env bash
# Stop hook gate (project local) — Claude 报"完成" 前自动跑 3 检.
# 触发: .claude/settings.local.json Stop event.
# 任一失败 exit 2 阻断 stop.

set -u
PROJ="/Users/dp/Documents/M/gaozhong"
cd "$PROJ" 2>/dev/null || exit 0

# 只在 git working tree 有 .py / *.sql / *.html / *.js 改动时跑
to_int() {
  local v=$1
  if [[ "$v" =~ ^[0-9]+$ ]]; then
    printf '%s' "$v"
  else
    printf '%s' "0"
  fi
}

# yaml/yml 纳入: 架构/数据契约 (sources/import_policies/project_architecture/exam_paper_contracts...)
# 走 config, 配置型架构漂移 (悬挂doc/未数据化importer) 也要触发架构契约门 (gate 4)
changed=$(git status --porcelain 2>/dev/null | grep -cE '\.(py|sql|html|js|css|yaml|yml)$' || echo 0)
changed=$(to_int "$changed")
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
  n_fail=$(to_int "$n_fail")
  n_warn=$(to_int "$n_warn")
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
#     exit 3 = DB 被写连接占用(init_db 重建中) → 延后, 非阻断 (流程级根治锁冲突假阳性)
if [ -f data/db/gaozhong.duckdb ] && [ -f scripts/data_accuracy_check.py ]; then
  python3 scripts/data_accuracy_check.py > /tmp/d0_check.log 2>&1
  d0_rc=$?
  if [ "$d0_rc" -eq 3 ]; then
    echo "[stop-gate] ⏸ D0 校验延后: DB 正被 init_db 重建占用 (非数据错误); 重建完成后下次 stop 自动校验" >&2
  elif [ "$d0_rc" -ne 0 ]; then
    fails="$fails
  ❌ D0 违反: scripts/data_accuracy_check.py 失败 — 看 /tmp/d0_check.log"
  fi
fi

# 2. complexity gates — 单次扫描派生两道门 (CC>10 总数 + CC>15 单函数硬阈)
cc_out=$(python3 scripts/lib/complexity_check.py \
  $(find backend scripts -name '*.py' -not -path '*/__pycache__/*' 2>/dev/null | tr '\n' ' ') 2>&1)
# 2a. CC>10 总数门 (减债 backlog 整体趋势)
hot_now=$(printf '%s\n' "$cc_out" | grep -c 'WARN' || echo 0)
hot_now=$(to_int "$hot_now")
HOT_BASELINE=37  # 2026-06-15 god-module 拆分后 CC>10 函数 42->37; 减债 backlog task_90d55f25 继续降. 仅当 >37 才阻断回归
if [ "$hot_now" -gt "$HOT_BASELINE" ]; then
  fails="$fails
  ❌ CC>10 函数 $hot_now > baseline $HOT_BASELINE — 修后再 stop (或 update baseline)"
fi
# 2b. CC>15 单函数硬阈门 (Rule8 反模式禁令). 2026-06-16 缺口: 仅靠 2a 总数门, 单函数 CC=18
#     只要总数没破 37 就滑过 (commit a9e671a 实证); 此门按 CC>15 计数 baseline, 跨硬阈新增即阻断.
cc15_now=$(printf '%s\n' "$cc_out" | grep -oE 'CC= *[0-9]+' | grep -oE '[0-9]+' | awk '$1>15{n++} END{print n+0}')
cc15_now=$(to_int "$cc15_now")
CC15_BASELINE=12  # 现存 CC>15 减债 backlog task_90d55f25; Rule8 硬阈(15)单函数只减不增, 新增即阻断
if [ "$cc15_now" -gt "$CC15_BASELINE" ]; then
  fails="$fails
  ❌ CC>15 单函数 $cc15_now > baseline $CC15_BASELINE (Rule8 反模式禁令硬阈) — 拆该函数后再 stop (减债则降 baseline)"
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
n_big_inline=$(to_int "$n_big_inline")
INLINE_BASELINE=4  # 现有重复 baseline; 不允许增
if [ "$n_big_inline" -gt "$INLINE_BASELINE" ]; then
  fails="$fails
  ❌ 前端 inline 大块 $n_big_inline > baseline $INLINE_BASELINE — 抽 common.js / css 后再 stop"
fi

# 4. 架构契约审计 (gate_contracts.project_architecture_audit severity=BLOCK). 2026-06-16 缺口:
#    契约声明为阻断门但 stop_gate 从未调它 → 硬编码PDF路径/悬挂doc引用等架构漂移长期静默躺着.
if ! python3 scripts/tools/audit/project_architecture_audit.py --strict --output /tmp/arch_audit.json >/tmp/arch_audit.log 2>&1; then
  fails="$fails
  ❌ 架构契约审计 BLOCK — 看 /tmp/arch_audit.log (legacy importer未数据化/悬挂doc/缺失模块路径等)"
fi

if [ -n "$fails" ]; then
  cat >&2 <<EOF
[stop-gate] 阻断 stop, 必须修这些再 stop:$fails

通过条件:
  (1)  D0 audit 0 FAIL + 0 WARN  (任何 WARN 必须重归类 OK 或修)
  (1b) D0 data_accuracy_check.py 全通过  (词/语法/教案/图谱/关联 全 100%)
  (2)  CC>10 函数 ≤ $HOT_BASELINE  (跑 python3 scripts/lib/complexity_check.py <files>)
  (2b) CC>15 单函数 ≤ $CC15_BASELINE  (Rule8 硬阈; 单函数跨15即超, 拆函数)
  (3)  前端 inline 大块 ≤ $INLINE_BASELINE  (抽到 common.js / common.css)
  (4)  架构契约审计 0 BLOCK  (python3 scripts/tools/audit/project_architecture_audit.py --strict)

只有当当前改动让基线**变更恶化** 时才阻断; 持平或改善 OK.
临时绕过 (不推荐): echo > /tmp/skip_stop_gate (然后下次 stop 内自动重置)
EOF
  if [ ! -f /tmp/skip_stop_gate ]; then
    exit 2
  fi
  rm -f /tmp/skip_stop_gate
fi

exit 0
