# 运营操作手册 (第五阶段交付)

> 给沈阳/辽宁持牌教育机构英语老师用. 双击 `start.command` 即用, 不需要技术背景.

## 1. 启动 (3 秒)

1. **首次**: 终端运行一次依赖检查
   ```bash
   cd /Users/dp/Documents/M/gaozhong
   python3 -c "import duckdb, pypdf, yaml; print('依赖 OK')"
   ```
2. **每次**: Finder 双击 `start.command`
   - 首次自动跑 `scripts/init_db.py` (3-5 秒)
   - 启动 backend (端口 8765)
   - 自动打开 `http://127.0.0.1:8765/app`

3. **停止**: Finder 双击 `stop.command`

## 2. 7 tab 用法

| tab | 用途 | 主要操作 |
|---|---|---|
| **A. 工作台** | 今日待办 + 数据健康 | 一眼看完进度 |
| **B. 教学 ⭐** | 40 节课程方案 | 按 layer (G1/G2/G3/G_FINAL) 折叠, 点课节卡片弹**讲义** |
| **C. 题库+组卷** | 题库浏览 + 条件组卷 + 听力题 | 现暂转 /teacher 旧 UI |
| **D. 数据管理** | 14 数据集 + 自动审计 | 看 FAIL/WARN 即时知道问题 |
| **E. 学生档案** | 学生 CRUD + 班级 + 弱点 + 推荐课节 | 点学生卡片看弱点 + **自动推送对应课节** |
| **F. 知识图谱** | 知识图谱可视化 | iframe 复用旧 /teacher |
| **G. 扫描 OCR** | 试卷扫描上传 (待补 POST UI) | API 通, UI 待 4.7.C |

## 3. 40 节课程方案 (B tab 核心)

按 4 层分:
- **G1** 10 节 高一系统课 (~1200 词)
- **G2** 10 节 高二系统课 (~2200 词, G1 累计)
- **G3** 10 节 高三上学期 (~3000 词, G2 累计)
- **G_FINAL** 10 节 **高考前突击** (~3500 词, 真题密集)

每节 120 分钟, 7 段结构:
```
0-15   开场 hook (Time/NatGeo/SciAm 风新闻)
15-25  上节复习
25-50  核心教学 (词/语法/句型) + 关联拓展 ≥3 (R1)
50-70  真题溯源 + 趋势曲线
70-90  场景练习 (≥3 场景 R3)
90-105 易错点
105-115 总结 + 下节预告
115-120 作业 10 题 (R4 tag ⊆ 本节)
```

老师点课节 → 看完整 markdown 讲义 (含本节核心词 + 关联词 + 真题题号 + 作业题 id).

## 4. 6 条课程铁律 (系统自动校验)

| 铁律 | 含义 | 触发拦截 audit |
|---|---|---|
| R1 关联 | 每节 ≥3 知识点关联 | audit_course_relations |
| R2 不抄 | 与教材无 ≥10 词连续重叠 | audit_course_no_textbook_copy |
| R3 场景 | 每知识点 ≥3 场景 | audit_course_scenarios |
| R4 作业 | 作业 tag 100% ⊆ 本节 | audit_homework_alignment |
| R5 分层 | 节内所有词 ⊆ lexical_layer | audit_course_lexical_layer |
| R6 标位 | 每词/语法 必带 year+教材位置 | audit_course_textbook_position |
| 听力 | 听力题必有 transcript | audit_listening_transcript_required |
| 政治 | 主题/篇/transcript 不含政治词 | audit_no_political |

任一 FAIL → 启动时 D tab 显示警告. 老师不用懂规则, 看 D tab 红色就找技术处理.

## 5. 改课程内容怎么办

40 节配置在 `backend/config/course_templates.yaml`. 改完重启 `start.command` 即生效.

例子: 把 #11 主题换成"实习生日记":
```yaml
- course_id: 11
  themes_main: 实习生日记       # 改这里
```

主题池在 `backend/config/theme_pool.yaml` (50 主题, 10 类). 加新主题改这个文件.

## 6. 学生档案 (E tab)

1. 学生列表 — 显示 5 个 demo 学生 (沈阳市第二中学高三1班)
2. 点学生 → modal 弹: 学生信息 + 弱点列表 + **推送课节**
   - eg 王芳 弱在"宾语从句" → 自动推 #14 G2 宾从课

真实学生导入: csv 格式同 schema (待 4.7.D 实装).

## 7. 数据健康 (D tab)

- 0 FAIL = 数据全通过
- WARN 一般是可接受偏差 (eg "讲义文本未持久化") , 不影响使用
- 详细审计: 链接 /teacher 旧 UI

## 8. 故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| 8765 端口被占 | 旧 server 没退 | `pkill -f backend/api/main.py` |
| init_db 失败 | 依赖缺 | 终端跑 `python3 scripts/init_db.py` 看具体错 |
| 浏览器没自动开 | OS 拦 | 手动 `http://127.0.0.1:8765/app` |
| 课程不显示 | yaml 改错 spec | 看 D tab audit FAIL |

## 9. 反馈渠道

老师试用反馈记到 `docs/teacher_feedback_round1.md` (待建).
