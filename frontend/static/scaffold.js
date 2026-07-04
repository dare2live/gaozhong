/* 骨架 / hub 页模块 — 北极星 Phase A 产物 (docs/product_master_plan.md).
 *
 * 注册 IA 重构后新增的页面: 真题特点骨架 (zhenti)、基础库 hub (jichu)、初中板块占位 (jr_*)。
 * 决策 C: 建框架不生成内容 — 这些页是诚实的"建设中/即将"骨架, 标清楚 Phase + 将呈现什么 + 数据现状,
 * 不伪造图表/不甩原始题号。可用的子库 (教材库/考试词典) 直接链到现有 working tab。
 */
(function () {
  const { registerTab, fetchSafe, isErr, errorBox, ensureECharts, initChart, pageHead } = window.GZ;

  // 通用骨架渲染: 标题 + Phase 徽章 + 引言 + 计划模块卡片
  function _scaffold({ title, badge, lead, cards }) {
    const cardHTML = (cards || []).map(c => {
      // "现可用"徽章删 (设计规范 §05: 全 ready 时信息量为零, 真实计数即状态); 仅建设中标注
      const chip = c.status === "ready" ? "" : `<span class="sc-chip">${c.phase || "建设中"}</span>`;
      const inner =
        `<div class="sc-card-h"><svg class="sc-ic" viewBox="0 0 24 24" stroke="currentColor" fill="none" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${c.icon || ""}</svg>`
        + `<span class="sc-card-t">${c.title}</span>${chip}</div>`
        + `<p class="sc-card-d">${c.desc}</p>`;
      return c.href
        ? `<a class="sc-card link" href="${c.href}">${inner}<span class="sc-go">进入 →</span></a>`
        : `<div class="sc-card">${inner}</div>`;
    }).join("");
    return `<section class="scaffold">
      ${pageHead(badge, title, lead)}
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
  // 学段→数据色 (设计规范 §02/§03: 义务三段=蓝阶深→浅, 高中两段=红族"你该主攻的重点", 未分类=灰+斜纹不估算;
  // 白字仅 --down/--down-2/红段; --down-3 段用 --ink; 全部 design-system 令牌, 禁 ad-hoc hex)
  const STAGE_SEG = {
    "小学":     { bg: "var(--down)",       fg: "#fff" },
    "初中":     { bg: "var(--down-2)",     fg: "#fff" },
    "义务教育": { bg: "var(--down-3)",     fg: "var(--ink)" },
    "高中必修": { bg: "var(--accent-ink)", fg: "#fff" },
    "高中选修": { bg: "var(--accent)",     fg: "#fff" },
    "未分类":   { bg: "repeating-linear-gradient(-45deg, var(--data-gray), var(--data-gray) 3px, #C9C7BF 3px, #C9C7BF 6px)" /* #C9C7BF = --data-gray 亮变体, decal 纹理专用 (非数据编码色) */, fg: "var(--ink)" },
  };

  function _stageSrTable(d) {
    const rows = d.stages.map(s => `<tr><td>${s.stage}</td><td>${s.pct}%</td><td>${s.n}</td></tr>`).join("");
    return `<table class="sr-only"><caption>辽宁高考考查词学段分布</caption><thead><tr><th>学段</th><th>占比</th><th>词数</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  // 王牌视觉锤 (设计规范 §03): 巨号 75.7% + 单条 100% 学段带 + 花括号跨段注 + 明细表。纯 CSS (打印友好/零图表库开销)。
  function _stageHero(d) {
    const segs = d.stages.map(s => {
      const c = STAGE_SEG[s.raw_stage || s.stage] || STAGE_SEG["未分类"];
      const label = s.pct >= 8 ? `${esc(s.stage)} ${s.pct}%` : "";
      return `<div class="zt-dna-seg" style="width:${s.pct}%;background:${c.bg};color:${c.fg}" title="${esc(s.stage)} ${s.pct}% · ${s.n}词">${label}</div>`;
    }).join("");
    const rows = d.stages.map(s => {
      const c = STAGE_SEG[s.raw_stage || s.stage] || STAGE_SEG["未分类"];
      return `<tr><td><span class="zt-sq" style="background:${c.bg}"></span>${esc(s.stage)}</td><td>${s.n}</td><td>${s.pct}%</td></tr>`;
    }).join("");
    return `
      <div class="zt-hero-num">${d.foundation_pct}<span class="zt-hero-pct">%</span></div>
      <p class="zt-hero-line"><b>你在初中前已学过的词, 占高考考查词的 ${d.foundation_pct}%</b> — 真正属于高中新增的只有 <b class="zt-hero-sr">${d.senior_pct}%</b>, 这就是课程主攻的 delta。</p>
      <div class="zt-dna" role="img" aria-label="高考考查词学段构成: ${d.stages.map(s => `${s.stage} ${s.pct}%`).join(", ")}">${segs}</div>
      <div class="zt-brace"><div class="zt-brace-f" style="width:${d.foundation_pct}%">${d.foundation_pct}% 入学前已学</div><div class="zt-brace-s" style="width:${d.senior_pct}%">${d.senior_pct}% 高中新增</div><div style="flex:1"></div></div>
      <table class="zt-stage-tbl"><thead><tr><th>学段</th><th>词数</th><th>占比</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  // 题材×设问思维 套路卡: cognitive_by_content 每题材主导技能 (era 2015-20, dual_model 方向性)。
  // thin 题材不静默丢 (D0 数字一个不删): 照渲但整行降透明 + 「样本薄」尾缀; 厚样本行在前 (稳定序)。
  function _taoluCard(cbc) {
    const bc = cbc.by_content || {};
    const keys = Object.keys(bc).filter(g => bc[g].skills && bc[g].skills.length);
    keys.sort((a, b) => (bc[a].thin ? 1 : 0) - (bc[b].thin ? 1 : 0));
    const rows = keys.map(g => {
      const top = bc[g].skills[0], thin = !!bc[g].thin;
      return `<div class="kb-row${thin ? " zt-thinrow" : ""}"><span class="kb-row-h">${esc(g)}</span><span class="zt-taolu">主导 <strong>${esc(top.label)}</strong> ${top.pct}%<span class="kb-dim"> · ${bc[g].total}子题</span>${thin ? '<span class="zt-thin-tag">样本薄</span>' : ""}</span></div>`;
    }).join("");
    return rows || '<p class="kb-dim">题材×思维数据不足。</p>';
  }
  const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  // N3: 设问思维 4 技能 — 2×2 常显卡 (学习者最可迁移的知识不折叠; ≤820px 降 1 列)。
  // 技能名与分布 = 教研显式标签真值; 「怎么想」与信号词 = 教学归纳。
  const _COG_EXPLAIN = [
    { skill: "推断", what: "据字面信息推未明说的言外之意、作者态度、隐含结论。", sig: ["infer", "suggest", "imply", "probably", "most likely", "learn from"] },
    { skill: "理解主旨要义", what: "抓全文中心、标题、段落大意。", sig: ["main idea", "best title", "mainly about", "purpose of the text"] },
    { skill: "理解具体信息", what: "定位某处细节事实 (时间/原因/数字/做法) — 拿题干关键词回原文找。", sig: ["according to", "what", "when", "why", "how many"] },
    { skill: "理解词汇", what: "据上下文猜词义、猜指代, 不背也能推。", sig: ["the word X means", "refers to", "closest in meaning"] },
  ];
  function _cogExplainPanel() {
    const cards = _COG_EXPLAIN.map(c =>
      `<div class="zt-cogcard"><div class="zt-cogcard-s">${esc(c.skill)}</div><p class="zt-cogcard-w">${esc(c.what)}</p><div class="zt-cogcard-sig">${c.sig.map(x => `<span class="zt-sig">${esc(x)}</span>`).join("")}</div></div>`).join("");
    return `<p class="kb-dim" style="margin:0 0 8px;">设问思维 = 题目要你<strong>怎么想</strong>, 不只是考什么。同一篇文章, 设问换个思维就是另一道题。高考阅读主要考这 4 种 — 看到卡里的设问信号词, 就知道该用哪种思维:</p>
      <div class="zt-cog-grid">${cards}</div>`;
  }

  // N2: 语法考点卡 (tests_grammar 课标第二级子类 辽宁考查频次热点)
  function _grammarCard(ge) {
    if (!ge || !ge.by_category || !ge.by_category.length) return '<p class="kb-dim">语法考查数据不足。</p>';
    const max = ge.by_category[0].n || 1;
    return ge.by_category.map(c => {
      const w = Math.round(100 * c.n / max);
      const tops = (c.top || []).map(t => esc(t.label.length > 16 ? t.label.slice(0, 16) + "…" : t.label)).join(" · ");
      return `<div class="zt-gram"><span class="zt-gram-c">${esc(c.category)}</span><span class="zt-gram-bar"><span class="zt-gram-fill" style="width:${w}%"></span></span><span class="zt-gram-n">${c.n}次 ${c.pct}%</span><div class="zt-gram-top">${tops}</div></div>`;
    }).join("");
  }
  // 样本量诚实标注 (坑12: 分布可用但 n 透明; n=次数=考查边, 非题数 — 一题可考多个语法点)
  // 坑(2026-07-04 全数据审计坑12): 旧版只写"直接来自历年试卷", 未披露当前 100% 数据来自
  // 2015-2020 旧课标II(2021+新高考因build_tests_grammar对英文答案桩文本关键词匹配缺席), 会让
  // 人误以为反映当前卷制。改读 eras_missing(单一计算点, 复用 grammar_exam_stats 已算字段)。
  // era 内部 key(如 "2015-2020_旧课标II")→人话短标签, 只做展示层清洗不碰数据。
  const _eraShort = era => (era || "").replace(/^[\d.+-]+_/, "").replace(/_/g, " ") || era;
  function _grammarCaption(ge) {
    if (!ge || ge.n_questions == null) return "";
    const base = `共 ${ge.n_questions} 题 · ${ge.n_edges || ge.total} 条考查记录 (一题可考多个语法点) — 量不大, 排序可信、小数点别抠。`;
    if (ge.eras_missing && ge.eras_missing.length) {
      const covered = (ge.eras_covered || []).map(_eraShort).join("、") || "历史";
      const missing = ge.eras_missing.map(_eraShort).join("、");
      return base + ` <span style="background:var(--accent-wash);color:var(--accent-ink);padding:0 6px;border-radius:8px;font-size:10px;white-space:nowrap;">仅 ${covered} 卷制 · ${missing} 暂无考查记录</span>`;
    }
    return base;
  }
  // N2: 教材搭配/句型/表达库卡 (phrases, 出现非考查)
  function _phraseCard(te) {
    if (!te || !te.by_group) return "";
    const chips = te.by_group.map(g => `<span class="tk-tchip">${esc(g.group)} <b>${g.n}</b></span>`).join("");
    return `${chips}<span class="tk-tchip" style="border-style:dashed">合计 <b>${te.total}</b></span>`;
  }

  registerTab("zhenti", async () => {
    const C = document.querySelector("#content");
    C.innerHTML = '<div class="loading-state"><span class="ls-dot"></span>载入真题特点…</div>';
    const [d, cbc, gram] = await Promise.all([
      fetchSafe("/api/k12/tested_word_stage"),
      fetchSafe("/api/exam_point/cognitive_by_content"),
      fetchSafe("/api/grammar/stats"),
    ]);
    if (isErr(d)) { C.innerHTML = errorBox({ title: "真题特点加载失败", msg: "后端未就绪或数据未算出 — 真实错误, 非空数据。" }); return; }
    const gramHTML = (!isErr(gram)) ? _grammarCard(gram.grammar_exam) : '<p class="kb-dim">语法考查数据加载失败。</p>';
    const taoluHTML = (!isErr(cbc)) ? _taoluCard(cbc) : '<p class="kb-dim">套路数据加载失败。</p>';
    C.innerHTML = `<section class="scaffold">
      ${pageHead("高中 · 真题实证", "真题长什么样", "辽宁卷到底考哪个学段的词、每类文章怎么设问 — 每个数字都能点开追到真题原卷。")}
      <div class="sc-takeaway">
        <div class="sc-tk-h">结论 · 用最少课程覆盖最大考点</div>
        <p class="sc-tk-body">辽宁高考<strong>离散考点题型</strong>(完形/语法填空/短改/单选)考查的词中, <strong class="tk-found">${d.foundation_pct}% 是小学 / 初中阶</strong>(学生入高中前已学), 真正属<strong class="tk-senior">高中新增的仅 ${d.senior_pct}%</strong>。→ 高中课程不必重教基础词, 主攻这 ${d.senior_pct}% 的高中 delta + 高频考点。</p>
        <p class="sc-tk-caveat">口径: 只统计真题里<b>真正考过</b>的词 (教材出现过 ≠ 高考考过), 共 ${d.total} 个去重词; 详细口径见页尾「数据怎么来的?」。</p>
      </div>
      <section class="bk-card">
        <div class="bk-h"><span>辽宁高考考查词 · 哪个学段学的</span><span class="bk-src">/api/k12/tested_word_stage</span></div>
        ${_stageHero(d)}
        ${_stageSrTable(d)}
        <p class="kb-dim" style="margin:10px 0 0;">统计口径 = 真题里<b>真正考查</b>的词 (教材出现过 ≠ 高考考过), 共 ${d.total} 个去重词。<b>已学过 ≠ 都记得</b> — 义务段词仍是考查主体, 主攻 ${d.senior_pct}% 不等于放掉基础。未分类 ${d.unclassified_pct}% 为校本超纲/外省词, 不估算。</p>
      </section>
      <p class="zt-nextlink">近年考什么在变? 完整迁移图 → <a href="#/beike">命题研判</a></p>
      <section class="bk-card">
        <div class="bk-h"><span>命题套路 · 题材 × 设问思维</span><span class="bk-src">/api/exam_point/cognitive_by_content</span></div>
        ${_cogExplainPanel()}
        <div class="kb-list">${taoluHTML}</div>
        <p class="kb-dim" style="margin:8px 0 0;">"每类语篇主导哪种思维" = 命题套路 (设问思维=教研显式标签真值; 题材=双模型方向性; era 2015–20, 2021+ 桥缺)。</p>
      </section>
      <section class="bk-card">
        <div class="bk-h"><span>语法考点 · 时态 / 从句 / 句型 / 词法 (辽宁考查热点)</span><span class="bk-src">/api/grammar/stats</span></div>
        <div class="zt-gramlist">${gramHTML}</div>
        <p class="kb-dim" style="margin:8px 0 0;">辽宁卷语法考查频次 (直接来自历年试卷, 按课标语法体系分类)。前 4 类 (从句/被动/非谓语/时态) 合计约七成 — 语法主攻顺序即此。${(!isErr(gram)) ? _grammarCaption(gram.grammar_exam) : ""}</p>
      </section>
      <p class="zt-nextlink">这些套路怎么变成课? → <a href="#/teaching">40 节课程</a> · 固定搭配/句型/表达库已移入 <a href="#/jichu">基础库</a></p>
      <details class="zt-datahow"><summary>数据怎么来的?</summary>
        <ul>
          <li><b>「出现 ≠ 考查」</b>: 教材里出现过的词不算, 只统计真题里真正被考的词。</li>
          <li><b>新老高考分开统计</b>: 2021 起辽宁用新高考 II 卷, 与 2015–2020 老卷分开算, 不混着平均。</li>
          <li><b>设问思维是事实标签</b>: 题型标签直接来自教研解析原文, 不是 AI 猜的; 题材/主题由两个 AI 独立标注、结论一致才计入 (方向参考)。</li>
          <li>原始口径: ${esc(d.caveat || "")}${d.stage_note ? " · " + esc(d.stage_note) : ""}</li>
        </ul>
      </details>
    </section>`;
  });

  // ③ 基础库 hub (设计规范 §06): 检索台首屏第一交互 + 四书架活取计数 + 教材短语收编 + 页脚数据凭证。
  // 一切学习者可见计数 API 活取; 辽宁真题数一律 liaoning_browse total (190 口径, 禁 474 全库冒充)。
  function _jichuSearchWire() {
    const inp = document.querySelector("#jc-q"), box = document.querySelector("#jc-hits");
    if (!inp || !box) return;
    let t = null;
    inp.oninput = () => {
      clearTimeout(t);
      const q = inp.value.trim();
      if (!q) { box.innerHTML = ""; return; }
      t = setTimeout(async () => {
        const r = await fetchSafe(`/api/exam_dictionary?prefix=${encodeURIComponent(q)}&limit=8`);
        if (isErr(r)) { box.innerHTML = '<p class="kb-dim">词典查询失败 — 后端未就绪。</p>'; return; }
        const rows = r.rows || [];
        if (!rows.length) { box.innerHTML = '<p class="kb-dim">没找到 — 只按词头检索, 试试更短的开头。</p>'; return; }
        box.innerHTML = rows.map(w =>
          `<button type="button" class="jc-hit" data-w="${esc(w.word)}">
            <b>${esc(w.word)}</b><span class="jc-hit-g">${esc((w.gloss || "").slice(0, 26))}</span>
            ${w.gaokao_hit_ln ? `<span class="jc-hit-ln">辽宁考过 ${w.gaokao_hit_ln} 次</span>` : '<span class="jc-hit-ln dim">未在辽宁卷命中</span>'}
            <span class="jc-hit-st">${esc(w.stage || w.curriculum_level || "")}</span>
          </button>`).join("");
        box.querySelectorAll(".jc-hit").forEach(b => b.onclick = () => window.GZ.openPopup && window.GZ.openPopup("word:" + b.dataset.w));
      }, 300);
    };
  }
  registerTab("jichu", async () => {
    const C = document.querySelector("#content");
    C.innerHTML = '<div class="loading-state"><span class="ls-dot"></span>载入基础库…</div>';
    const [stats, browse, cur, dict, gram, stg] = await Promise.all([
      fetchSafe("/api/stats"), fetchSafe("/api/exam/liaoning_browse"),
      fetchSafe("/api/curriculum/summary"), fetchSafe("/api/exam_dictionary?prefix=zz&limit=1"),
      fetchSafe("/api/grammar/stats"), fetchSafe("/api/k12/tested_word_stage"),
    ]);
    // 计数 fetch 失败 → 显原描述不显假数字 (D0 诚实)
    const shelf = (title, icon, href, sub, fallback) =>
      `<a class="sc-card link" href="${href}"><div class="sc-card-h"><svg class="sc-ic" viewBox="0 0 24 24" stroke="currentColor" fill="none" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${icon}</svg><span class="sc-card-t">${title}</span></div><p class="sc-card-d">${sub || fallback}</p><span class="sc-go">进入 →</span></a>`;
    C.innerHTML = `<section class="scaffold">
      ${pageHead("高中 · 基础库", "去哪查、有多少", "教材 · 真题 · 课标 · 词典 — 每条数据可回溯原始 PDF 与真题原卷。")}
      <div class="jc-search">
        <input id="jc-q" type="search" placeholder="查一个词: 释义 · 学段 · 高考是否考过" aria-label="词典检索 (按词头)" autocomplete="off">
        <div id="jc-hits" class="jc-hits" aria-live="polite"></div>
      </div>
      <div class="sc-grid">
        ${shelf("教材库", IC.book, "#/textbook",
          !isErr(stats) && stats.textbooks ? `${stats.textbooks} 册 · 外研社 + 人教 (辽宁主用) — 单元 / 词表 / 课文直读` : "", "外研社版 + 人教版单元 / 词表 / 课文, 按学习序列浏览。")}
        ${shelf("真题库", IC.paper, "#/tiku",
          !isErr(browse) && browse.total ? `${browse.total} 题 · ${(browse.years || []).length ? Math.min(...browse.years) + "–" + Math.max(...browse.years) : ""} 辽宁卷 — 每题可溯源原卷` : "", "辽宁卷高考真题按年/题型浏览, 每题溯源到原卷。")}
        ${shelf("考试词典", IC.words, "#/dict",
          !isErr(dict) && dict.total ? `${Number(dict.total).toLocaleString()} 词 · 辽宁高考命中标记 + 学段归属 ${!isErr(stg) ? window.GZ.stageMiniBand(stg) : ""}` : "", "考纲词汇释义 + 辽宁高考命中 / 学段标记。")}
        ${shelf("课标库", IC.std, "#/kebiao",
          !isErr(cur) && cur.vocab_total ? `${Number(cur.vocab_total).toLocaleString()} 词 · ${cur.grammar_total} 语法项 · 主题语境 ${cur.themes_total} 项` : "", "课程标准: 主题群 / 语法体系 / 词汇结构化浏览。")}
      </div>
      <section class="bk-card" style="margin-top:14px">
        <div class="bk-h"><span>教材 固定搭配 / 句型 / 表达方式</span><span class="bk-src">/api/grammar/stats · phrases</span></div>
        <div class="tk-types">${(!isErr(gram)) ? _phraseCard(gram.textbook_expr) : '<p class="kb-dim">加载失败。</p>'}</div>
        <p class="kb-dim" style="margin:8px 0 0;"><strong>教材里出现过 ≠ 高考考过</strong> — 这里是教材库存, 不冒充考查频次。</p>
      </section>
      <p class="jc-cred">${!isErr(stats) ? `${Number(stats.nodes || 0).toLocaleString()} 个知识节点 · ${Number(stats.edges || 0).toLocaleString()} 条关联 · ` : ""}数据每日自动校验</p>
      <details class="zt-datahow"><summary>数据怎么来的?</summary>
        <ul>
          <li>教材/课标 = 官方 PDF 解析入库, 每条可回溯页码; 真题 = 历年辽宁卷 (2021 起新高考 II 卷), 每题可回溯原卷。</li>
          <li>词典「辽宁考过 N 次」= 该词在辽宁卷离散考点题型中被考查的次数 (出现 ≠ 考查)。</li>
        </ul>
      </details>
    </section>`;
    _jichuSearchWire();
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
