# /app 验收快照（Round 1，M3）

## run_id
- `20260610T074134Z`

## 核验范围
- V1~V8 `/app` 人机验收清单（功能入口与链路可追溯）

## 代码级可复核证据

### 1) 7-tab 入口完整性
- 文件：`frontend/app.html:14-21`
- 证据：侧边栏 nav 明确包含 `#/workbench`、`#/teaching`、`#/qbank`、`#/data`、`#/students`、`#/graph`、`#/scan`
- 数量：7 个 `<a data-tab=...>`；另 `route()` 默认跳转/回退逻辑确保 `workbench` 启动可达。

### 2) 路由 mount 注册完整性（7 个 tab）
- 文件：`frontend/static/app_router.js`
- 证据：`register()` 覆盖：`workbench`、`teaching`、`qbank`、`data`、`students`、`graph`、`scan`
- 对应行：`register("workbench")` `register("teaching")` `register("qbank")` `register("data")` `register("students")` `register("graph")` `register("scan")`

### 3) 打印能力
- 文件：`frontend/static/app_router.js:117-123`
- 证据：讲义 modal 内有 `<button class="print-btn" onclick="window.print()">`
- 说明：V8 判定以按钮存在 + `window.print()` 可调用为准（打印流不依赖后端返回 PDF 文件）

### 4) `/app` 关键功能链路
- 文件：`frontend/static/app_router.js`
- 教学：课程列表 + 点击卡片触发 `window._openHandout`（讲义 + 课程材料）
- 题库/组卷：`qbank` tab 加载 `listening` 与 `listening` 题目列表
- 学生：`students` tab 可查看学生列表与弱点/推荐
- 图谱：`graph` tab 与 `/graph_popup.js` 联动
- 扫描：`scan` tab 提供文件上传+列表查询链路

## 结论
- `/app` 前端链路为静态代码可追溯闭环，V8 打印能力在讲义 modal 层存在。该快照可复核。
