# 断点续传 — 新 session 第一份读物

> 用户原话 (2026-05-25): "下次我说从中断处继续时能无缝衔接"
> 新 session 一打开, 先读本文件 + `goal.md` 顶部 D0, 立即接上.

最后停止时间: **2026-05-25**
最后 commit: **`(pending)`** feat(7.2+7.3): 听力 25 题 + 写作 10+10 + 打印+播放器

---

## 1. 当前状态 — 全绿

跑一遍验证 (3 个命令):

```bash
cd /Users/dp/Documents/M/gaozhong

# (a) D0 全数据 100% 准校验 — 18 章 39+ 项, 必须 exit 0
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

codex review 全部落地:
  ✅ Q2 加权 greedy (稀有 tag 优先)
  ✅ Q3 阈值 重命名 + 提下界 (consolidate_floor 70/70/65)
  ✅ Q4 弱点 trace 限 kind ('word','grammar' only)
  ✅ Q5 per-student seed (反作弊, alice/bob 不同卷)
  ✅ Q6 错题追问 followup endpoint (二阶段 3-5 题深挖弱点)
```

详 `goal.md` 各阶段 + `docs/data_accuracy_audit.md`.

---

## 3. 当前状态 — 全部 task 已完成

所有 codex review 改进 (Q2-Q6) 已落地, #68 错题追问 endpoint 已实装.

**系统已具备交付运营条件**:
- D0 100% 准 (20 章 45+ 项, 全绿)
- 4945 nodes / 34728 edges / 40 节课程 / 578 题库
- 二阶段摸底 (一阶段粗分 + 追问深挖) 完整闭环
- 前端 7 tab SPA + 全局图谱浮窗 + 概念互链

**Phase 7 进度 (2026-05-25)**:
- ✅ 7.1 充实讲义 40/40 节 DONE (180K+ chars, 超纲词=0)
- ✅ vocab_guard 模块 + API + D0 校验 + thresholds.yaml
- ✅ 前端讲义分段渲染 + 生成规则面板
- ✅ 7.2 听力 25 题 (短对话 10 + 长对话 9 + 独白 6, 全 transcript)
  - audio_config.yaml + data/audio/ 目录 + 命名规范
  - listening.py 服务 + API /api/listening/{list,detail}
  - 前端 C tab 听力面板 (筛选+原文展开+播放器)
  - 前端 <audio> 播放器 (play/pause/progress/speed)
  - @media print CSS + 讲义打印按钮
- ✅ 7.3 续写 10 题 + 应用文 10 篇 (含范文+评分维度)
- 🔲 7.4 题目质量升级 (578→700+, 需 ~120 题)
- 🔲 7.5 前端 Quiz mode + 年级标注 tooltip
- 🔲 7.6 真人验证
- 🔲 7.7 管线

**继续命令**:
```
"继续 Phase 7, 从 7.4 题目质量升级开始"
```

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
