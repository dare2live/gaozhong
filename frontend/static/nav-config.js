/* 导航 / 信息架构配置 (数据驱动, 非 hardcode HTML).
 *
 * 2026-06-27 产品重置 (北极星 docs/product_master_plan.md): 面向学习者的产品 IA。
 * 顶层 = 初中 | 高中 两大板块 (GZ_SECTIONS); 每板块四页 (① 命题研判 ② 真题特点 ③ 基础库 ④ 课程)。
 * 教师工具 (备课/讲课/组卷/学情/扫描) 已下线 (后端服务保留, 不在 nav)。高中先跑通, 初中 Phase E 镜像建设中。
 *
 * app_router.js renderSidebar() 渲染: 板块切换器 (GZ_SECTIONS) + 当前板块的分组 (GZ_NAV 按 section 过滤)。
 * 加/改/排页面 = 改本配置一处, 不动 HTML/CSS。
 *
 * section: 所属板块 (senior=高中 / junior=初中)
 * tabs[].id:    路由 #/<id> + data-tab (复用现有 mount: beike/teaching/textbook/dict; 新 mount 见 scaffold.js)
 * tabs[].label: 显示名
 * tabs[].icon:  Tabler 风格内联 SVG path (currentColor, stroke 1.6 由 CSS)
 * tabs[].count: nav 角标计数源 — stats 字段名 (courses 等); 省略=无角标
 */
window.GZ_SECTIONS = [
  { id: "senior", label: "高中", hint: "辽宁新高考 II 卷" },
  { id: "junior", label: "初中", hint: "沈阳中考 · 建设中" },
];

const _IC = {
  yanpan:  '<path d="M4 14a8 8 0 1 1 16 0"/><path d="M13.5 11.5 12 14"/>',
  zhenti:  '<path d="M4 19V5"/><path d="M4 19h16"/><path d="M8 16v-4"/><path d="M13 16V8"/><path d="M18 16v-6"/>',
  jichu:   '<rect x="4" y="3" width="6" height="18" rx="1"/><rect x="14" y="3" width="6" height="18" rx="1"/><path d="M4 8h6"/><path d="M14 8h6"/>',
  kecheng: '<path d="M3 4h18"/><path d="M4 4v10a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V4"/><path d="M12 15v4"/><path d="M9 19h6"/>',
};

window.GZ_NAV = [
  // ── 高中 (北极星 Phase A/B/C; 数据最全, 先跑通) ──
  { section: "senior", group: "高中 · 辽宁新高考 II 卷", tabs: [
    { id: "beike",    label: "命题研判", icon: _IC.yanpan },              // ① 结论先行首页 (复用考点驾驶舱)
    { id: "zhenti",   label: "真题特点", icon: _IC.zhenti },             // ② 统计/热力 + 小初高词占比 (Phase B)
    { id: "jichu",    label: "基础库",   icon: _IC.jichu },             // ③ 教材库 / 真题库 / 课标库
    { id: "teaching", label: "40 节课程", icon: _IC.kecheng, count: "courses" }, // ④ L3 课程 (Phase C 框架)
  ]},
  // ── 初中 (北极星 Phase E; 同结构镜像高中, 建设中) ──
  { section: "junior", group: "初中 · 沈阳中考 (建设中)", tabs: [
    { id: "jr_beike",   label: "命题研判", icon: _IC.yanpan },
    { id: "jr_zhenti",  label: "真题特点", icon: _IC.zhenti },
    { id: "jr_jichu",   label: "基础库",   icon: _IC.jichu },
    { id: "jr_kecheng", label: "课程",     icon: _IC.kecheng },
  ]},
];
