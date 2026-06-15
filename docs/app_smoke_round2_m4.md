# /app 复核快照（Round 2，M4）

## run_id
- `20260610T135344Z`

## 说明
- 本轮为 M4 课程主链路静态复核快照，聚焦课程主流程、学生弱点闭环、知识图谱跳转、扫描/OCR 入口。
- 本文件仅记录静态链路可复查证据，不替代复核。

## 证据索引

### 1. 课程主列表与课程详情（教学闭环）
- 文件：`frontend/app.html:14-21`
  - 侧边栏 nav 固定 7 个 tab 锚点，教学 tab 为 `#/teaching`。
- 文件：`frontend/static/app_router.js:30-35`
  - 路由注册 `register("teaching", async () => { ... })`，默认以卡片列表分层渲染课程（`G1`/`G2`/`G3`/`G_FINAL`）。
- 文件：`frontend/static/app_router.js:107-124`
  - 课程卡片 `onclick="window._openHandout(${c.course_id})"`，覆盖课程详情入口。
- 文件：`frontend/static/app_router.js:185-204`
  - `_openHandout` 使用 `/api/course/handout?id=<cid>` 加载讲义；渲染含课后测验按钮 `window._startQuiz(${cid})`（课程主流程 7+段教材可见）。

### 2. 学生弱点与推送课节（复用链路）
- 文件：`frontend/static/app_router.js:458-507`
  - `students` tab 渲染学生列表并支持 `window._openStudent('${s.student_id}')`。
- 文件：`frontend/static/app_router.js:641-665`
  - `_openStudent` 同时并发读取 ` /api/students/get`、`/api/students/weakness`、`/api/students/recommend`，并在弹窗中展示 `推送课节 (${recRows.length})`。
- 文件：`frontend/static/app_router.js:656-658`
  - 推送课节以 `window._openHandout(${r.course_id})` 落到课程讲义链路，形成弱点→推荐课节闭环可追溯。

### 3. 知识图谱联动与真题跳转（图谱闭环）
- 文件：`frontend/static/app_router.js:669-732`
  - `graph` tab 渲染节点联想与趋势入口，加载 `top exam words`，每个项通过概念链接 `GZ.conceptLink` 发起跳转。
- 文件：`frontend/static/common.js:56-67`
  - `conceptLink` 输出 `<a class="gz-concept" data-concept="...">`。
- 文件：`frontend/static/graph_popup.js:11-17` 与 `:51-54`
  - 全局 click 监听 `.gz-concept[data-concept]`，并请求 `/api/graph/popup?id=<cid>` 弹出联通图与真题列表（课程主链路“概念跳转”可复现）。

### 4. 题库与扫描 OCR 入口（课外链路补齐）
- 文件：`frontend/static/app_router.js:302-330`
  - `qbank` tab 通过 `/api/stats`、`/api/listening/list` 展示听力与题库全貌，支持 `GZ.audioPlayer` 与原文显示。
- 文件：`frontend/static/app_router.js:735-831`
  - `scan` tab 提供上传表单并 POST `/api/scan/upload?...`，列表读取 `/api/scan/list`（包括 upload_id / OCR 状态 / 时间），形成扫描链路入口与可回溯数据面。

## 结论
- M4 课程主链路已形成可静态复核证据链：课程列表-讲义/测验、学生弱点-课节推荐、图谱概念跳转、扫描入口均有前端代码路径与后端 API 对齐。
- 本快照对应当前 `M4` 一次性执行产物链路，复核以闭环结果在里程碑边界收口。
