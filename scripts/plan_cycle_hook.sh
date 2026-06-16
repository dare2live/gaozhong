#!/usr/bin/env bash
# UserPromptSubmit hook — 固化"改代码前充分计划 → 用工具审计 → 开工 → 做完再审计"循环.
#
# 缺口 (2026-06-16 用户指出): 本项目"改后审计"已由 stop_gate(Stop) 硬固化, "改前用工具"由
# precode_review(PreToolUse) 提醒, 但"改代码前充分计划"无任何机制 = 规则停在文档没进流程.
# 本 hook 在**实质代码任务** prompt 时把完整循环 + 本项目工具链注入 Claude context (非阻断,
# 塑造计划而非事后补救)。纯问答/查看类 prompt 不触发, 避免噪声 (mio §7 不过度制度化).
#
# 输出: stderr (Claude Code 注入 context). 始终 exit 0 (非阻断).
set -u
PROJ="/Users/dp/Documents/M/gaozhong"
cd "$PROJ" 2>/dev/null || exit 0

# UserPromptSubmit 经 stdin 传 JSON ({"prompt": "..."}); 取 prompt 文本判实质性
raw=$(cat 2>/dev/null)
prompt=$(printf '%s' "$raw" | python3 -c "import sys,json
try: print(json.load(sys.stdin).get('prompt',''))
except Exception: print('')" 2>/dev/null)
[ -z "$prompt" ] && prompt="$raw"

# 实质代码工作关键词 (触发循环注入); 纯"查/看/解释/是什么"不触发
if printf '%s' "$prompt" | grep -qiE '重构|实现|新建|新增|修复|修 ?bug|feat|fix|refactor|迁移|拆分|加(一?个)?(功能|字段|列|表|轴|断言|门|hook|校验|维度)|改(代码|逻辑|service|schema|api|前端|门|算法|表)|建(表|轴|门|service|模块|断言)|落(表|地|库)'; then
  cat >&2 <<'EOF'
[plan-cycle] 实质代码任务 — 固化循环 (改前充分计划 → 工具审计 → 开工 → 做完再审计):
  1. 计划: 读相关真相源/doc(agent.md/architecture.md八铁律/data_accuracy_audit), 先设计单一计算点 +
     铁律对照(Rule1单一计算点/Canonical First/Edges一等公民/扩模块不新建协调层), 不 bottom-up 堆码.
  2. 改前审计(工具优先非人肉grep): codegraph query <symbol> 查 fan-in/blast-radius; 大改(>20文件/god-module)
     先 /codegraph-architecture-audit; 抓 baseline 备"行为等价证明".
  3. 开工: 单一计算点收口 / 判断规则进 backend/config/*.yaml(不 hardcode) / 诚实降级(算不出标 unknown).
  4. 做完再审计(三门全绿才算完): python3 scripts/data_accuracy_check.py(D0 exit0) + moth assert --repo .(PASS)
     + bash scripts/stop_gate.sh(exit0); 对抗验证(注入故障必被 gate 抓再自愈); 大改 Rule10 spawn review 再 commit.
  说明: 本项目"改后审计"由 stop_gate(Stop)硬阻断; "改前计划"靠此注入(无硬门 — 硬门.plan_ok可 echo 绕过=摆设,
        mio §7 不为上工具而上工具); 真执行力 = 你把循环走完, 不是门替你走.
EOF
fi
exit 0
