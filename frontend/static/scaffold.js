/* 骨架 / hub 页模块 — 北极星 Phase A 产物 (docs/product_master_plan.md).
 *
 * 注册 IA 重构后新增的页面: 真题特点骨架 (zhenti)、基础库 hub (jichu)、初中板块占位 (jr_*)。
 * 决策 C: 建框架不生成内容 — 这些页是诚实的"建设中/即将"骨架, 标清楚 Phase + 将呈现什么 + 数据现状,
 * 不伪造图表/不甩原始题号。可用的子库 (教材库/考试词典) 直接链到现有 working tab。
 */
(function () {
  const { registerTab } = window.GZ;

  // 通用骨架渲染: 标题 + Phase 徽章 + 引言 + 计划模块卡片
  function _scaffold({ title, badge, lead, cards }) {
    const cardHTML = (cards || []).map(c => {
      const chip = c.status === "ready"
        ? '<span class="sc-chip ready">现可用</span>'
        : `<span class="sc-chip">${c.phase || "建设中"}</span>`;
      const inner =
        `<div class="sc-card-h"><svg class="sc-ic" viewBox="0 0 24 24" stroke="currentColor" fill="none" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${c.icon || ""}</svg>`
        + `<span class="sc-card-t">${c.title}</span>${chip}</div>`
        + `<p class="sc-card-d">${c.desc}</p>`;
      return c.href
        ? `<a class="sc-card link" href="${c.href}">${inner}<span class="sc-go">进入 →</span></a>`
        : `<div class="sc-card">${inner}</div>`;
    }).join("");
    return `<section class="scaffold">
      <header class="sc-head">
        <div class="sc-badge">${badge}</div>
        <h1 class="sc-title">${title}</h1>
        <p class="sc-lead">${lead}</p>
      </header>
      <div class="sc-grid">${cardHTML}</div>
    </section>`;
  }

  const IC = {
    chart: '<path d="M4 19V5"/><path d="M4 19h16"/><path d="M8 16v-4"/><path d="M13 16V8"/><path d="M18 16v-6"/>',
    heat:  '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    words: '<path d="M4 7V5h16v2"/><path d="M9 19h6"/><path d="M12 5v14"/>',
    book:  '<path d="M19 4v16H7a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"/><path d="M9 4v16"/>',
    paper: '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 9h6"/><path d="M9 13h6"/><path d="M9 17h4"/>',
    std:   '<path d="M4 5a2 2 0 0 1 2-2h9l5 5v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/><path d="M14 3v5h5"/>',
    build: '<path d="M3 21h18"/><path d="M5 21V7l8-4v18"/><path d="M19 21V11l-6-4"/><path d="M9 9h.01"/><path d="M9 13h.01"/>',
  };

  // ② 真题特点 (Phase B): 命题特点/趋势/小初高词占比 — 数据在 L2 后端, 前端可视化建设中
  registerTab("zhenti", async () => {
    document.querySelector("#content").innerHTML = _scaffold({
      badge: "高中 · Phase B 建设中",
      title: "真题特点",
      lead: "围绕辽宁高考真题 (新课标 II 卷) 的命题特点与趋势 — 用数据回答\"高考考什么、怎么考、近年怎么变\"。下列模块的底层数据已在 L2 关联层算出, 前端可视化为 Phase B 任务。",
      cards: [
        { title: "题材 · 主题 · 设问思维 分布与迁移", icon: IC.chart, phase: "Phase B",
          desc: "按卷制 era 分层 (不取全历史平均) 看体裁/课标主题群/设问思维的占比与年际迁移; 样本不足的维度诚实标\"方向性\"。" },
        { title: "小学 / 初中 / 高中 词在高考卷的占比", icon: IC.words, phase: "Phase B",
          desc: "本产品\"用最少课程覆盖最大考点\"论点的王牌实证 — 若高考多数词为初中/小学级, 高中课程只攻高频×高中新增的 delta。" },
        { title: "命题套路热力 (考点 × 题型)", icon: IC.heat, phase: "Phase B",
          desc: "哪些考点/题型/题材在升温, 对应怎么考 — 数据驱动的方向性指引 (非押题; 样本量诚实, 见 D0 红线)。" },
      ],
    });
  });

  // ③ 基础库 hub: 教材库 / 真题库 / 课标库 (可用的直接链到现有 working tab)
  registerTab("jichu", async () => {
    document.querySelector("#content").innerHTML = _scaffold({
      badge: "高中 · 基础库",
      title: "基础库",
      lead: "教材、真题、课标三大第一手数据库 — 可查、可溯源 (每条能回溯原始 PDF / 真题)。这是 L1 基础数据层的浏览入口。",
      cards: [
        { title: "教材库", icon: IC.book, status: "ready", href: "#/textbook",
          desc: "外研社版 + 人教版 (辽宁主用) 单元 / 词表 / 课文, 按学习序列浏览。" },
        { title: "考试词典 (考纲词汇)", icon: IC.words, status: "ready", href: "#/dict",
          desc: "考纲词汇释义 + 辽宁高考命中 / 必教标记 (三源溯源)。" },
        { title: "真题库", icon: IC.paper, phase: "Phase B",
          desc: "辽宁高考真题按年/题型/考点浏览, 每题可溯源到原卷 — 作为课程作业的题源 (Phase B)。" },
        { title: "课标库", icon: IC.std, phase: "Phase B",
          desc: "普通高中英语课程标准 (主题群 / 词汇 / 语法) 结构化浏览 (Phase B)。" },
      ],
    });
  });

  // ── 初中板块 (Phase E 镜像建设中) — 四页共用占位 ──
  function _juniorStub(title) {
    return async () => {
      document.querySelector("#content").innerHTML = _scaffold({
        badge: "初中 · Phase E 建设中",
        title: title + " (初中)",
        lead: "初中板块将与高中同结构镜像 (命题研判 / 真题特点 / 基础库 / 课程)。当前优先把高中跑通; 初中需先补齐地基 (沪教牛津教材 + 沈阳中考真题 + 义务课标 2022) 才会建本页。",
        cards: [
          { title: "为什么先做高中", icon: IC.build, phase: "决策 B",
            desc: "高中数据最全 (教材/真题/课标齐), 作样板先跑通三层产品; 初中按同框架镜像放第二步。" },
          { title: "初中地基现状", icon: IC.std, phase: "Phase E 前置",
            desc: "中考 2024/2025 省统一卷已结构化; 沪教牛津教材 + 义务课标产物已抽取, 尚无独立 D0 门 (待补)。" },
        ],
      });
    };
  }
  registerTab("jr_beike", _juniorStub("命题研判"));
  registerTab("jr_zhenti", _juniorStub("真题特点"));
  registerTab("jr_jichu", _juniorStub("基础库"));
  registerTab("jr_kecheng", _juniorStub("课程"));
})();
