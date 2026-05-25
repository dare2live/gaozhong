# 断点续传 — 新 session 第一份读物

> 用户原话 (2026-05-25): "下次我说从中断处继续时能无缝衔接"
> 新 session 一打开, 先读本文件 + `goal.md` 顶部 D0, 立即接上.

最后停止时间: **2026-05-25**
最后 commit: **`9fe5145`** feat(codex review): placement Q2+Q3+Q4+Q5 4 改进落地

---

## 1. 当前状态 — 全绿

跑一遍验证 (3 个命令):

```bash
cd /Users/dp/Documents/M/gaozhong

# (a) D0 全数据 100% 准校验 — 17 章 39+ 项, 必须 exit 0
python3 scripts/data_accuracy_check.py
# 期望: ✅ D0 100% 准确率达成, 全部检查通过

# (b) Stop hook 完整模拟
bash scripts/stop_gate.sh; echo "exit=$?"
# 期望: exit=0

# (c) (可选) init_db 重建数据
python3 scripts/init_db.py | tail -5
# 期望末尾: 审计: 0 FAIL, 0 WARN
```

任一不 0 → 接 §4 排查; 全 0 → 接 §3 继续干活.

---

## 2. 进度地图 — 我们做完了什么

```
第一阶段 ✅  数据基石 (4945 nodes / 34728 edges / 14 教材)
第二阶段 ✅  题库 + 条件组卷 (509 题 + 10641 tag)
第三阶段 ✅  教师端 + 本地部署 (start.command)
第四阶段 ✅  真问题修 (data/UI/趋势/economist)
第五阶段 ✅  统一教学系统 + 40 节分层课程 (G1/G2/G3/G_FINAL 各 10)
第六阶段 ✅  全局图谱浮窗 + 学生档案 + csv import + 弱点真算 + R2 audit 真扫
            + 跨版本算法 v4 100% (30 对验证)
            + D0 强约束 hook + 全数据校验脚本

刚做完 (codex review 落地):
  ✅ Q2 加权 greedy (稀有 tag 优先)
  ✅ Q3 阈值 重命名 + 提下界 (consolidate_floor 70/70/65)
  ✅ Q4 弱点 trace 限 kind ('word','grammar' only)
  ✅ Q5 per-student seed (反作弊, alice/bob 不同卷)
```

详 `goal.md` 各阶段 + `docs/data_accuracy_audit.md`.

---

## 3. 唯一未做 task — 直接续

### #68 codex Q6: 错题追问 endpoint (1-2 h)

**背景** (codex 评 placement):
> "9-11 题只能粗分流, 不能快速测准. 当 screener, 边界再加 3-5 题自适应追问."

**目标**: 新加二阶段测验流程:
- 一阶段 9-11 题答完 → 根据错题/边界正确率
- 二阶段抽 3-5 题深挖弱点 concept (eg 错的是 word:until → 追 3 题考 until 的)
- 最终 layer 推荐综合两阶段 (二阶段权重高)

**实施 (从这里开 1 个 session 能干完)**:

```
1. backend/services/placement/followup.py — 新模块
   pick_followup_questions(con, student_id, wrong_qids, n=5):
     - 抽错题的 word/grammar tag
     - 从 question_bank 抽其它带相同 tag 的题 (排除一阶段已答)
     - greedy: 每错点抽 1-2 题 covered

2. backend/api/routes/placement.py — 新 endpoint
   /api/placement/followup?student_id=&grade=  (POST: {wrong_qids: [...]})
   → 返 3-5 题 follow-up paper
   /api/placement/final_score (POST: {first_answers, followup_answers})
   → 综合两阶段最终 verdict

3. frontend/static/app_router.js — E tab 入测流程改:
   一阶段答完 → 若边界 (verdict='consolidate' 或 'below') → 自动入二阶段
   全部答完 → 显示最终 verdict + 弱点 + 推送

4. data_accuracy_check.py +1 章节: followup spec 验证
   _check_18_followup(con) — 验证 followup pick 工作

5. docs 更新:
   docs/data_accuracy_audit.md 加 placement followup 条目
   goal.md 第六阶段标 Q6 ✅
```

**开干命令**:
```bash
cd /Users/dp/Documents/M/gaozhong
# 这就是新 session 续命第一句
```

跟我说 "**继续 #68**" 我就开干.

---

## 4. 故障排查 (任一验证 fail 时用)

| 现象 | 处理 |
|---|---|
| D0 校验 fail | 看 `/tmp/d0.log` tail; 大概率是新加 task 没更新 check |
| stop_gate exit 2 | 看 stderr — `audit FAIL/WARN > 0` 或 `CC>10 > 10` |
| init_db crash | 看 stdout — schema/loader bug; `data/db/gaozhong.duckdb` 删后重 init |
| server 起不来 | `pkill -9 -f backend/api/main.py; lsof -ti :8765 \| xargs kill -9` |
| Edit hook BLOCK | god-module 阈值触发 — 拆文件再改 (eg 用 idempotent DDL 替直改 schema.sql) |

---

## 5. 关键约束 (D0 + M1-M8 + R1-R6) — 必须 100% 守

```
D0 (顶层): 任意数据+关联 100% 准, hook 强执行
M1-M8 (模块化原则): 三层严分 / 插件 dispatch / yaml 外置 / API 稳 / 单测 / CC≤10 / fan-in≤5 / 零依赖
R1-R6 (课程铁律): 关联≥3 / 不抄教材 / ≥3 场景 / 作业⊆本节 / 词分层 / 教材位置必标
```

任何新代码必须:
1. 通 PreToolUse hook (改 db.py 等 fan-in>5 文件被拦)
2. 通 stop_gate (D0 + CC)
3. 加进 `data_accuracy_check.py` (新 API/算法)
4. 更新 `docs/data_accuracy_audit.md`

---

## 6. 后续阶段 (用户拍前不动)

- 阶段 7+ LLM 增强 / sklearn 难度 / 跨学科
- ⏸️ 跳过项: 老师真试 30 分钟 (4.6.E) / Docker 多人部署 (4.6.A-D)
  替代: 自身完整度 + D0 100% 准

---

## 7. 快速接续 quote (给新 session 用户)

```
"读 docs/RESUME.md, 然后继续 #68 codex Q6 错题追问 endpoint"
```

或直接:

```
"继续"
```

(我会自动 Read 本文件 + 接 #68)
