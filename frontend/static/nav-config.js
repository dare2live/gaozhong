/* 导航 / 信息架构配置 (数据驱动, 非 hardcode HTML).
 *
 * 用户硬约束: 硬编码全局移除, 用模块+数据+配置。侧栏分组/tab/图标/计数源 = 这份数据,
 * app_router.js 的 renderSidebar() 从此渲染。加/改/排 tab = 改本配置一处, 不动 HTML/CSS。
 *
 * group: 工作流分组标题 (研判→备课→组卷→学情→数据, 贴合教师流程)
 * tag:   分组角标 (如 "示例" 标 demo 数据组, 诚实化)
 * tabs[].id:    路由 #/<id> + data-tab
 * tabs[].label: 显示名
 * tabs[].icon:  Tabler 风格内联 SVG path (currentColor, stroke 1.6 由 CSS)
 * tabs[].count: nav 角标计数源 — stats 字段名(nodes/question_bank/courses) 或 'dict'(词典 total); 省略=无角标
 */
window.GZ_NAV = [
  { group: "研判 · 命题真值", tabs: [
    { id: "beike", label: "考点驾驶舱", icon: '<path d="M4 14a8 8 0 1 1 16 0"/><path d="M13.5 11.5 12 14"/>' },
    { id: "graph", label: "知识图谱", count: "nodes", icon: '<circle cx="6" cy="12" r="2.4"/><circle cx="18" cy="6" r="2.4"/><circle cx="18" cy="18" r="2.4"/><path d="M8.3 10.9 15.7 7.1"/><path d="M8.3 13.1l7.4 3.8"/>' },
  ]},
  { group: "备课", tabs: [
    { id: "dict", label: "考试词典", count: "dict", icon: '<path d="M19 4v16H7a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"/><path d="M9 4v16"/>' },
    { id: "jiangke", label: "讲课调取", icon: '<path d="M3 5a17 17 0 0 1 9 2 17 17 0 0 1 9-2v13a17 17 0 0 0-9 2 17 17 0 0 0-9-2z"/><path d="M12 7v15"/>' },
    { id: "lesson", label: "单元备课", icon: '<path d="M4 5a2 2 0 0 1 2-2h9l5 5v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/><path d="M14 3v5h5"/><path d="M8 13h6"/><path d="M8 17h4"/>' },
    { id: "textbook", label: "教材浏览", icon: '<rect x="4" y="3" width="6" height="18" rx="1"/><rect x="14" y="3" width="6" height="18" rx="1"/><path d="M4 8h6"/><path d="M14 8h6"/>' },
    { id: "teaching", label: "分层教学", count: "courses", icon: '<path d="M3 4h18"/><path d="M4 4v10a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V4"/><path d="M12 15v4"/><path d="M9 19h6"/>' },
    { id: "k12", label: "K12衔接", icon: '<path d="M9 7H6.5a3 3 0 0 0 0 6H9"/><path d="M15 7h2.5a3 3 0 0 1 0 6H15"/><path d="M8.5 10h7"/>' },
  ]},
  { group: "组卷", tabs: [
    { id: "qbank", label: "题库 + 组卷", count: "question_bank", icon: '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4V3a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v1"/><path d="M9 10h6"/><path d="M9 14h6"/><path d="M9 17.5h4"/>' },
  ]},
  { group: "学情", tag: "示例", tabs: [
    { id: "xisheng", label: "分析学生", icon: '<path d="M4 19V5"/><path d="M4 19h16"/><path d="M8 16v-4"/><path d="M13 16V8"/><path d="M18 16v-6"/>' },
    { id: "students", label: "学生档案", icon: '<rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="9" cy="11" r="2"/><path d="M6 16c0-1.7 1.3-2.5 3-2.5s3 .8 3 2.5"/><path d="M15 10h3.5"/><path d="M15 13.5h3.5"/>' },
    { id: "scan", label: "扫描录入", icon: '<path d="M4 8V6a2 2 0 0 1 2-2h2"/><path d="M4 16v2a2 2 0 0 0 2 2h2"/><path d="M16 4h2a2 2 0 0 1 2 2v2"/><path d="M16 20h2a2 2 0 0 0 2-2v-2"/><path d="M5 12h14"/>' },
  ]},
  { group: "数据 · 设置", tabs: [
    { id: "workbench", label: "工作台", icon: '<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>' },
    { id: "data", label: "数据管理", icon: '<ellipse cx="12" cy="5.5" rx="7.5" ry="2.5"/><path d="M4.5 5.5v6c0 1.4 3.4 2.5 7.5 2.5s7.5-1.1 7.5-2.5v-6"/><path d="M4.5 11.5v6c0 1.4 3.4 2.5 7.5 2.5s7.5-1.1 7.5-2.5v-6"/>' },
  ]},
];
