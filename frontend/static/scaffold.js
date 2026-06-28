/* 骨架 / hub 页模块 — 北极星 Phase A 产物 (docs/product_master_plan.md).
 *
 * 注册 IA 重构后新增的页面: 真题特点骨架 (zhenti)、基础库 hub (jichu)、初中板块占位 (jr_*)。
 * 决策 C: 建框架不生成内容 — 这些页是诚实的"建设中/即将"骨架, 标清楚 Phase + 将呈现什么 + 数据现状,
 * 不伪造图表/不甩原始题号。可用的子库 (教材库/考试词典) 直接链到现有 working tab。
 */
(function () {
  const { registerTab, fetchSafe, isErr, errorBox, ensureECharts, initChart } = window.GZ;

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

  // ② 真题特点: 小初高词占比 (真实数据, 王牌实证) + 分布迁移/套路热力 (Phase B 占位)
  const STAGE_COLOR = {
    "小学": "#2E7D54", "初中": "#3C7AA6", "义务教育": "#6BA3C4",
    "高中必修": "#BE3A2B", "高中选修": "#9C2C20", "未分类": "#B4B2A9",
  };

  function _stageSrTable(d) {
    const rows = d.stages.map(s => `<tr><td>${s.stage}</td><td>${s.pct}%</td><td>${s.n}</td></tr>`).join("");
    return `<table class="sr-only"><caption>辽宁高考考查词学段分布</caption><thead><tr><th>学段</th><th>占比</th><th>词数</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  function _renderStageChart(d) {
    const el = document.querySelector("#zt-stage");
    if (!el) return;
    const cats = d.stages.map(s => s.stage);
    const data = d.stages.map(s => ({ value: s.pct, itemStyle: { color: STAGE_COLOR[s.stage] || "#B4B2A9" } }));
    const inst = initChart(el);
    inst.setOption({
      grid: { left: 70, right: 56, top: 10, bottom: 24 },
      xAxis: { type: "value", max: Math.ceil(Math.max(...d.stages.map(s => s.pct)) / 10) * 10, axisLabel: { formatter: "{value}%", fontSize: 11, color: "#76716A" }, splitLine: { lineStyle: { color: "#F0ECE4" } } },
      yAxis: { type: "category", inverse: true, data: cats, axisLabel: { fontSize: 12, color: "#45413A" }, axisTick: { show: false } },
      series: [{
        type: "bar", data, barWidth: "58%",
        label: { show: true, position: "right", formatter: p => `${d.stages[p.dataIndex].pct}% · ${d.stages[p.dataIndex].n}词`, fontSize: 11, color: "#76716A" },
      }],
    });
    el.setAttribute("aria-label", `辽宁高考考查词学段分布条形图: ` + d.stages.map(s => `${s.stage} ${s.pct}%`).join(", "));
    if (!el._wired) { window.addEventListener("resize", () => inst.resize()); el._wired = true; }
  }

  registerTab("zhenti", async () => {
    const C = document.querySelector("#content");
    C.innerHTML = '<div class="loading-state"><span class="ls-dot"></span>载入真题特点…</div>';
    const d = await fetchSafe("/api/k12/tested_word_stage");
    if (isErr(d)) { C.innerHTML = errorBox({ title: "真题特点加载失败", msg: "后端未就绪或数据未算出 — 真实错误, 非空数据。" }); return; }
    const placeholders = _scaffold({
      badge: "", title: "", lead: "",
      cards: [
        { title: "题材 · 主题 · 设问思维 分布与迁移", icon: IC.chart, phase: "Phase B",
          desc: "按卷制 era 分层 (不取全历史平均) 看体裁/课标主题群/设问思维的占比与年际迁移; 样本不足维度诚实标\"方向性\"。底层 L2 数据已在命题研判页, 本页聚合为 Phase B。" },
        { title: "命题套路热力 (考点 × 题型)", icon: IC.heat, phase: "Phase B",
          desc: "哪些考点/题型/题材在升温, 对应怎么考 — 数据驱动方向性指引 (非押题; 样本量诚实, D0 红线)。" },
      ],
    }).replace('<header class="sc-head">', '<header class="sc-head" hidden>');
    C.innerHTML = `<section class="scaffold">
      <header class="sc-head">
        <div class="sc-badge">高中 · 真题特点</div>
        <h1 class="sc-title">真题特点</h1>
        <p class="sc-lead">围绕辽宁高考真题 (新课标 II 卷) 的命题特点 — 用数据回答"高考考什么、怎么考、近年怎么变"。</p>
      </header>
      <div class="sc-takeaway">
        <div class="sc-tk-h">结论 · 用最少课程覆盖最大考点</div>
        <p class="sc-tk-body">辽宁高考<strong>离散考点题型</strong>(完形/语法填空/短改/单选)考查的词中, <strong class="tk-found">${d.foundation_pct}% 是小学 / 初中阶</strong>(学生入高中前已学), 真正属<strong class="tk-senior">高中新增的仅 ${d.senior_pct}%</strong>。→ 高中课程不必重教基础词, 主攻这 ${d.senior_pct}% 的高中 delta + 高频考点。</p>
        <p class="sc-tk-caveat">${d.caveat || ""} · 共 ${d.total} 个去重考查词${d.unclassified_pct ? `; 未分类 ${d.unclassified_pct}% 为校本超纲/外省词, 不估算` : ""}。</p>
      </div>
      <section class="bk-card">
        <div class="bk-h"><span>辽宁高考考查词 · 学段分布</span><span class="bk-src">/api/k12/tested_word_stage</span></div>
        <div id="zt-stage" role="img" aria-label="辽宁高考考查词学段分布条形图" style="height:300px;"></div>
        ${_stageSrTable(d)}
      </section>
      ${placeholders}
    </section>`;
    if (await ensureECharts()) _renderStageChart(d);
    else { const e = document.querySelector("#zt-stage"); if (e) window.GZ.chartLoadError(e); }
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
        { title: "真题库", icon: IC.paper, status: "ready", href: "#/tiku",
          desc: "辽宁卷高考真题按年/题型浏览, 每题溯源到原卷 — 课程作业的题源。" },
        { title: "课标库", icon: IC.std, status: "ready", href: "#/kebiao",
          desc: "普通高中英语课程标准: 主题群 / 语法体系 / 词汇 (按学段) 结构化浏览。" },
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
