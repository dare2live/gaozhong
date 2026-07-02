/* SPA hash router — 学习者产品 IA (北极星: 初中|高中 两板块 × 命题研判/真题特点/基础库/课程).
   每 tab 一个 mount() 注册到 TABS; 独立视图模块 (beike/scaffold/jichu_pages/dict/textbook 等) 经
   GZ.registerTab 挂载。教师子系统 (workbench/data/students/scan) 2026-07-02 删除 (后端服务按北极星保留)。 */

(function () {
  const { $, $$, fetchJSON, fetchSafe, isErr, errorBox, mdToHtml } = window.GZ;
  const CONTENT = $("#content");

  // 板块状态 (初中/高中) — 北极星 IA 两大板块; 默认高中 (决策 B 先跑通)
  let _section = localStorage.getItem("gz_section") || (window.GZ_SECTIONS && window.GZ_SECTIONS[0] && window.GZ_SECTIONS[0].id) || "senior";
  function _sectionOf(tabId) {
    for (const g of (window.GZ_NAV || [])) if (g.tabs.some(t => t.id === tabId)) return g.section || _section;
    return _section;
  }

  // 侧栏从 nav-config.js 数据渲染 (IA = 配置驱动, 非 hardcode HTML; 用户 no-hardcode 硬约束)
  // 顶部板块切换器 (GZ_SECTIONS) + 当前板块的分组 (GZ_NAV 按 section 过滤)。
  function renderSidebar() {
    const nav = $(".tabnav");
    if (!nav || !window.GZ_NAV) return;
    const secs = window.GZ_SECTIONS || [];
    const switcher = secs.length > 1
      ? `<div class="section-switch" role="tablist" aria-label="学段板块">` + secs.map(s =>
          `<button type="button" role="tab" class="ss-btn${s.id === _section ? " active" : ""}" data-section="${s.id}" aria-selected="${s.id === _section}" title="${s.hint || ""}">${s.label}</button>`
        ).join("") + `</div>`
      : "";
    const groups = (window.GZ_NAV || []).filter(g => !g.section || g.section === _section).map(g =>
      `<div class="navgroup">${g.group}${g.tag ? `<span class="gtag">${g.tag}</span>` : ""}<span class="gline"></span></div>` +
      g.tabs.map(t =>
        `<a href="#/${t.id}" data-tab="${t.id}"><svg class="ic" viewBox="0 0 24 24" stroke="currentColor">${t.icon}</svg> ${t.label}${t.count ? `<span class="cnt" id="nav-cnt-${t.id}"></span>` : ""}</a>`
      ).join("")
    ).join("");
    nav.innerHTML = switcher + groups;
    nav.querySelectorAll(".ss-btn").forEach(b => b.onclick = () => {
      const g = (window.GZ_NAV || []).find(x => x.section === b.dataset.section);
      if (g && g.tabs[0]) location.hash = "#/" + g.tabs[0].id;  // 切板块=跳该板块首页; route() 同步 _section + 重渲
    });
  }

  // nav 资产计数 (后端真实数据, count 源由配置定 — 非硬编码数字)
  async function populateNavCounts() {
    const tabs = (window.GZ_NAV || []).flatMap(g => g.tabs).filter(t => t.count);
    if (!tabs.length) return;
    const s = await fetchJSON("/api/stats").catch(() => ({}));
    let dictTotal = null;
    if (tabs.some(t => t.count === "dict")) dictTotal = (await fetchJSON("/api/exam_dictionary?prefix=zz&limit=1").catch(() => ({}))).total;
    tabs.forEach(t => {
      const v = t.count === "dict" ? dictTotal : s[t.count];
      const el = $("#nav-cnt-" + t.id);
      if (el && v != null) el.textContent = Number(v).toLocaleString();
    });
    // #17: 侧栏 audit 状态改 live (原硬编码 "0 FAIL" 数据真FAIL时仍绿=虚假安全感, 违D0诚实)
    const ax = $("#sb-audit");
    if (ax) {
      const fnd = await fetchJSON("/api/audit/findings").catch(() => []);
      const rows = Array.isArray(fnd) ? fnd : (fnd.findings || []);
      const fail = rows.filter(r => r.severity === "FAIL").length;
      const warn = rows.filter(r => r.severity === "WARN").length;
      // 双态学习者文案 (设计规范 §05): 正常=信任语言; 异常=红字计数, 永不隐藏 (D0 异常必须可见)
      ax.textContent = (fail || warn) ? `数据校验异常 ${fail + warn} 项` : "数据每日自动校验 · 全部通过";
      ax.style.color = fail ? "var(--accent-ink)" : (warn ? "var(--warn)" : "");
    }
  }

  // -- 注册表 (M2)
  const TABS = {};
  function register(name, mount) { TABS[name] = mount; }
  window.GZ.registerTab = register;   // 暴露给独立视图模块 (beike.js 等), 不在本god-file堆新tab


  // -- router
  function route() {
    const hash = (location.hash || "#/beike").slice(2);  // strip "#/" (命题研判=默认落地页)
    const name = (hash.split("/")[0] || "beike").toLowerCase();
    // 板块同步: 路由到的页若属另一板块 (含 hub 内链/直接 hash), 切板块并重渲侧栏
    const sec = _sectionOf(name);
    if (sec !== _section) { _section = sec; localStorage.setItem("gz_section", _section); renderSidebar(); populateNavCounts(); }
    $$(".tabnav a").forEach(a => a.classList.toggle("active", a.dataset.tab === name));
    // RC1: 切 tab 回顶 (滚动容器在不同布局下可能是 window / documentElement / body / .content, 全复位)
    window.scrollTo(0, 0);
    if (document.scrollingElement) document.scrollingElement.scrollTop = 0;
    if (CONTENT) CONTENT.scrollTop = 0;
    const mount = TABS[name];
    if (mount) {
      // RC1: 即时加载占位 (不白等上一屏看似卡死)
      CONTENT.innerHTML = '<div class="loading-state"><span class="ls-dot"></span>载入中…</div>';
      mount().catch(err => {
        // RC1 / D0 诚实: 加载失败=可见错误, 不冒充空数据 (后端未起/数据未就绪都该显式告知)
        CONTENT.innerHTML = '<div class="error-state">'
          + '<div class="es-title">该模块加载失败</div>'
          + `<div class="es-msg">页面 <code>${name}</code>: ${String(err && err.message || err)}。可能后端未启动或数据未就绪 — 这是真实错误, 非"无数据"。</div>`
          + '<button class="es-retry" type="button" onclick="location.reload()">重新载入</button></div>';
      });
    } else {
      CONTENT.innerHTML = `<div class="error-state"><div class="es-title">未知页面</div><div class="es-msg">页面 <code>${name}</code> 不存在。</div></div>`;
    }
  }
  window.addEventListener("hashchange", route);

  // 全量收敛: 旧 /teacher /legacy 已 302 收敛到此(?moved=X), 顶部一次性提示(可关), 让旧书签用户知道入口已统一
  function movedBanner() {
    const m = new URLSearchParams(location.search).get("moved");
    if (!m) return;
    const label = m === "teacher" ? "教师工作台" : "旧版数据面板";
    const bar = document.createElement("div");
    bar.style.cssText = "background:#FBF3E0;border-bottom:1px solid #E3CF95;color:#7A5A12;font-size:13px;padding:8px 14px;display:flex;justify-content:space-between;align-items:center;";
    bar.innerHTML = `<span>旧版「${label}」入口已统一到本学习者平台 (初中/高中两板块)。请更新书签到本页。</span>` +
      `<button class="gz-iconbtn" aria-label="关闭" title="关闭" style="padding:0 6px;">${GZ.icon("close")}</button>`;
    bar.querySelector("button").onclick = () => bar.remove();
    document.body.insertBefore(bar, document.body.firstChild);
  }

  window.addEventListener("DOMContentLoaded", () => {
    // ?debug=1 = 开发者模式: 显示 API 路径徽章 (.bk-src) 等工程溯源标记 (学习者默认不见, 设计规范 §05)
    if (new URLSearchParams(location.search).has("debug")) document.body.classList.add("gz-debug");
    renderSidebar(); movedBanner(); if (!location.hash) location.hash = "#/beike"; route(); populateNavCounts();
  });


  // ===================================================================
  // B. 40 节课程 — L3 框架 (北极星 Phase C): 覆盖模型 + 教学提纲(考点焦点+作业真题溯源, content=null)
  //    替代旧 course-grid+handout (旧生成内容已回滚; 内容生成是 Phase D, 需就绪门)。
  // ===================================================================
  const _esc = s => String(s == null ? "" : s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  function _covLine(cov) {
    const ax = (cov && cov.axes) || {};
    const part = (k, name) => {
      if (!ax[k] || !ax[k].n_total) return "";
      const eff = Math.round(100 * ax[k].high_yield_n / ax[k].n_total);
      return `${name} ${ax[k].n_total} 考点 (覆盖${cov.target_pct}%需 ${ax[k].high_yield_n}, 即 ${eff}%)`;
    };
    return [part("genre", "题材"), part("theme_l2", "主题群"), part("word", "高频考词"), part("grammar", "语法")].filter(Boolean).join(" · ");
  }
  function _lessonCard(l) {
    // 溯源友好化: 显示"年份 辽宁卷 · #题号", 原始 source_file#index 入 title (机器血缘); 不甩裸 gb/... 路径
    const _srcShort = q => `${q.year} 辽宁卷 · #${(q.source || "").split("#").pop()}`;
    const hw = (l.evidence_questions || []).map(q =>
      `<li class="ks-hw"><span class="ks-hw-t">${_esc(q.question_type)}</span><span class="ks-hw-p">${_esc(q.preview)}…</span><span class="ks-hw-s" title="原卷溯源: ${_esc(q.source)}">${_esc(_srcShort(q))}</span></li>`).join("");
    return `<details class="ks-lesson"><summary class="ks-sum">
        <span class="ks-seq">第 ${l.seq} 节</span>
        <span class="ks-focus">考点焦点: ${_esc(l.focus)}</span>
        <span class="ks-w" title="本节命题权重份额 = 该主题群辽宁频次 ÷ 该主题节数">权重 ${l.trend_weight}</span>
        <span class="ks-hwn">作业 ${(l.evidence_questions || []).length} 真题</span>
      </summary>
      <div class="ks-body"><div class="ks-body-h">作业真题 (辽宁卷, 可溯源原卷; 非生成)</div><ul class="ks-hwlist">${hw || '<li class="ks-hw">本节真题作业整理中</li>'}</ul></div>
    </details>`;
  }
  register("teaching", async () => {
    CONTENT.innerHTML = '<div class="loading-state"><span class="ls-dot"></span>载入 40 节课程框架…</div>';
    const [syl, cov] = await Promise.all([fetchSafe("/api/course/syllabus"), fetchSafe("/api/course/coverage")]);
    if (isErr(syl)) { CONTENT.innerHTML = '<div class="error-state"><div class="es-title">课程框架加载失败</div><div class="es-msg">后端未就绪 — 真实错误。</div></div>'; return; }
    CONTENT.innerHTML = `<section class="scaffold">
      ${GZ.pageHead("高中 · 40 节课程", `${syl.n_lessons} 节课覆盖高考主题全集`, "按命题频次分配 — 用最少的课覆盖最大的考查权重; 每节一个考点焦点 + 可溯源的辽宁真题作业。")}
      <div class="caveat-banner"><span class="cb-tag">进度</span><span><b>讲义制作中</b> — 每节已定考点焦点与真题作业, <b>作业现在就能做</b>; 可背诵正文上线前不占位不伪造。</span></div>
      <div class="sc-takeaway">
        <div class="sc-tk-h">覆盖模型 · 用最少课程覆盖最大考点</div>
        <p class="sc-tk-body">${isErr(cov) ? "覆盖数据加载失败。" : _esc(_covLine(cov))}。${syl.coverage ? _esc(syl.coverage.note) : ""}</p>
        <p class="sc-tk-caveat">考点焦点↔真题作业全程可溯源到原卷。详见<a href="#/zhenti">真题特点</a>的小初高词占比与命题套路。</p>
      </div>
      <div class="ks-list">${syl.lessons.map(_lessonCard).join("")}</div>
    </section>`;
  });


  // ===================================================================
  // C. 题库 + 组卷
  // ===================================================================
  register("qbank", async () => {
    // 题库浏览器: 按题型筛真题 (全 fetch /api/qb/* 单算点; 仅真题无押题)。
    CONTENT.innerHTML = `<h2>题库 + 组卷</h2><p class="muted">载入中...</p>`;
    const st = await fetchJSON("/api/qb/stats").catch(() => ({ by_type: {}, by_difficulty: {} }));
    // 后端审计#7: difficulty 实为 len(题面) 篇幅档(非教研难度), 且跨 source 粒度混淆(2021子题短/2015篇章长)
    // → 据实标"篇幅"(长/中/短), 不冒充"难度"(老师筛"短"得短题=诚实, 非误导难度伪影)。
    const DIFF = { hard: ["长", "var(--ink-2)"], mid: ["中", "var(--ink-3)"], easy: ["短", "var(--ink-3)"] };
    const types = Object.entries(st.by_type || {});
    const totalN = st.total || types.reduce((a, [, n]) => a + n, 0);
    // #6: 默认 type_mix 用库内真实题型动态生成 (去掉 legacy 硬编码的库内不存在题型; 阅读多, 其余各2)
    const defMix = types.slice(0, 4).map(([k]) => `${k}:${k.includes("阅读") ? 4 : 2}`).join(",") || "阅读理解:4";
    let qtype = null;
    const d = st.by_difficulty || {};
    CONTENT.innerHTML = `
      <h2>题库 + 组卷 <span class="muted" style="font-size:14px;font-weight:400">${totalN} 题 · 仅已核验真题 (无押题)</span></h2>
      <p class="muted" style="margin:2px 0 10px;font-size:12.5px">按题型筛选浏览; 或一键生成蓝图练习卷(题面均历年真题, 结构对齐非预测)。题面篇幅(字数估·非难度) 长 ${d.hard || 0} · 中 ${d.mid || 0} · 短 ${d.easy || 0}。</p>
      <div class="bk-filter" id="qb-blueprint" style="margin-bottom:10px;">
        <span class="bk-flabel">蓝图练习卷</span>
        <label style="font-size:12px;color:var(--ink-3);">题量 <input id="qb-bp-total" type="number" value="30" min="5" max="60" style="width:54px;padding:3px 6px;border:1px solid var(--line);border-radius:6px;"></label>
        <button id="qb-bp-go" class="bk-pill on">${GZ.icon("grid")} 生成蓝图练习卷</button>
        <span class="muted" style="font-size:11px;">按考纲蓝图结构从真题加权抽样 · 非预测/非押题</span>
      </div>
      <details id="qb-compose" style="margin-bottom:10px;font-size:13px;"><summary style="cursor:pointer;color:var(--accent-ink);">${GZ.icon("gear")} 自定义组卷 (按题型/标签/难度/年份精确组卷, 收敛自 legacy)</summary>
        <div class="bk-filter" style="margin-top:8px;flex-wrap:wrap;">
          <label>题型分布 <input id="qb-c-mix" value="${defMix}" style="width:280px;padding:3px 6px;border:1px solid var(--line);border-radius:6px;"></label>
          <label>必含标签 <input id="qb-c-req" placeholder="word:abandon,unit:waiyan/bixiu_1/U1" style="width:200px;padding:3px 6px;border:1px solid var(--line);border-radius:6px;"></label>
          <label>题面篇幅 <select id="qb-c-diff" aria-label="组卷题面篇幅筛选(字数估, 非难度)" style="padding:3px;border:1px solid var(--line);border-radius:6px;"><option value="">混合</option><option value="easy">短</option><option value="mid">中</option><option value="hard">长</option></select></label>
          <label>年份 <input id="qb-c-year" placeholder="2021,2022,2023" style="width:120px;padding:3px 6px;border:1px solid var(--line);border-radius:6px;"></label>
          <label>种子 <input id="qb-c-seed" type="number" value="42" style="width:60px;padding:3px 6px;border:1px solid var(--line);border-radius:6px;"></label>
          <button id="qb-c-go" class="bk-pill on">组卷</button>
        </div>
      </details>
      <div id="qb-paper"></div>
      <div class="bk-filter" id="qb-filters">
        <button class="bk-pill on" data-qt="__all">全部 ${totalN}</button>
        ${types.map(([k, n]) => `<button class="bk-pill" data-qt="${k}">${k} ${n}</button>`).join("")}
      </div>
      <div id="qb-list"><p class="muted">载入中...</p></div>`;
    const loadList = async () => {
      const url = "/api/qb/browse?limit=80" + (qtype ? "&type=" + encodeURIComponent(qtype) : "");
      const rows = await fetchJSON(url).catch(() => []);
      const list = Array.isArray(rows) ? rows : (rows.rows || []);
      $("#qb-list").innerHTML = list.length ? `<div class="qb-list">${list.map(r => {
        const df = DIFF[r.difficulty] || ["", "var(--ink-3)"];
        return `<div class="qb-row"><span class="qb-tb">${r.question_type || ""}</span><span class="qb-stem">${(r.stem_preview || "").replace(/</g, "&lt;").slice(0, 90)}</span><span class="qb-ans">${r.answer || ""}</span><span class="qb-diff" style="color:${df[1]}">${df[0]}</span></div>`;
      }).join("")}</div>` : '<p class="muted">该题型无题</p>';
    };
    $$("#qb-filters [data-qt]").forEach(b => b.onclick = () => {
      qtype = b.dataset.qt === "__all" ? null : b.dataset.qt;
      $$("#qb-filters .bk-pill").forEach(p => p.classList.toggle("on", p.dataset.qt === b.dataset.qt));
      loadList();
    });
    // 共享试卷渲染 (Rule5: 蓝图练习卷 + 自定义组卷 复用; stem 3000 容阅读完整篇章不截小题)
    const esc = s => (s || "").replace(/</g, "&lt;");
    const paperHTML = (p, title, basisHtml) => {
      const sf = p.shortfalls;
      const hasSf = Array.isArray(sf) ? sf.length : (sf && Object.values(sf).some(v => v > 0));
      const shortf = hasSf ? `<p class="muted" style="color:var(--warn);font-size:12px;margin:4px 0;">注 部分题型库存不足: ${esc(JSON.stringify(sf))}（诚实披露, 不补押题）</p>` : "";
      return `<div class="bk-card" style="margin:6px 0 12px;">
        <div class="bk-h"><span>${title} <small>${p.actual_total}/${p.target_total} 题</small></span>
          <button id="qb-paper-print" class="bk-export">${GZ.icon("printer")} 打印此卷</button></div>
        ${basisHtml || ""}${shortf}
        <ol style="padding-left:1.4rem;font-size:13px;line-height:1.55;">
          ${p.questions.map(q => `<li style="margin:6px 0;"><span class="qb-tb">${esc(q.qtype)}</span> <span style="color:var(--ink-3);font-size:11px;">#${q.qb_id}·${esc(q.difficulty || "")}</span><br><span style="white-space:pre-wrap;">${esc((q.stem || "").slice(0, 3000))}</span> <span style="color:var(--accent-ink);">[答:${esc(q.answer || "")}]</span></li>`).join("")}
        </ol></div>`;
    };
    const mountPaper = (box, html) => { box.innerHTML = html; const pb = $("#qb-paper-print"); if (pb) pb.onclick = () => window.GZ.printWithCharts(); };
    // #12: 蓝图练习卷接矿口 (/api/exercise/blueprint_practice 原0前端消费空转; 诚实=结构对齐非预测)
    const genBlueprint = async () => {
      const total = Math.max(5, Math.min(60, parseInt($("#qb-bp-total").value, 10) || 30));
      const box = $("#qb-paper");
      box.innerHTML = `<p class="muted">生成中...</p>`;
      const p = await fetchSafe(`/api/exercise/blueprint_practice?total=${total}`);
      if (isErr(p)) { box.innerHTML = errorBox({ title: "蓝图练习卷生成失败", msg: "后端接口错误 (非题库为空)。" }); return; }
      if (!p.questions || !p.questions.length) { box.innerHTML = `<p class="muted" style="padding:12px">该结构下暂无可组题</p>`; return; }
      const cb = p.composition_basis || {};
      mountPaper(box, paperHTML(p, "蓝图练习卷",
        `<p class="muted" style="font-size:12px;margin:0 0 4px;">${esc(cb.positioning)}</p><p class="muted" style="font-size:11px;margin:0 0 8px;">依据: <b>${esc(cb.selection_basis)}</b></p>`));
    };
    $("#qb-bp-go").onclick = genBlueprint;
    // #6: 自定义组卷接矿口 (/api/paper/compose; 收敛自 legacy /teacher#compose)
    const genCompose = async () => {
      const box = $("#qb-paper");
      box.innerHTML = `<p class="muted">组卷中...</p>`;
      const q = new URLSearchParams();
      q.set("type_mix", $("#qb-c-mix").value);
      const req = $("#qb-c-req").value, diff = $("#qb-c-diff").value, year = $("#qb-c-year").value, seed = $("#qb-c-seed").value;
      if (req) q.set("require_tags", req);
      if (diff) q.set("difficulty", diff);
      if (year) q.set("year_in", year);
      if (seed) q.set("seed", seed);
      const p = await fetchSafe("/api/paper/compose?" + q);
      if (isErr(p)) { box.innerHTML = errorBox({ title: "组卷失败", msg: "后端接口错误。" }); return; }
      if (p.error) { box.innerHTML = errorBox({ title: "组卷失败", msg: esc(p.error), retry: false }); return; }
      mountPaper(box, paperHTML(p, "自定义组卷", `<p class="muted" style="font-size:11px;margin:0 0 8px;">题面均历年真题(无押题); 缺额诚实披露。</p>`));
    };
    $("#qb-c-go").onclick = genCompose;
    await loadList();
  });



  // ===================================================================
  // F. 知识图谱 (本tab: stats概览 + 高频考点词入口; 力导向SVG探索仍在 /legacy, 见 needs_user_decision UI收敛)
  // ===================================================================
  // 渲染考点共现网络 — 复用 GZ.renderCooccurNetwork 单一口径(与「讲课调取」C' 同源同配色, 防漂移)。
  // 弃旧通用 subgraph (会暴露教材版本/城市行政结构 + 问题星形噪声); 只渲真正有教研意义的考点关联。
  async function _renderCooccur(era, eraLabel) {
    const box = document.getElementById("graph-viz");
    if (!box) return;
    const ctr = document.getElementById("graph-center"); if (ctr) ctr.textContent = eraLabel;
    box.innerHTML = '<div class="loading-state"><span class="ls-dot"></span>载入考点共现…</div>';
    let co;
    try { co = await fetchJSON("/api/exam_point/cooccurrence"); }
    catch (e) { box.innerHTML = `<div class="error-state" style="margin:0"><div class="es-title">考点共现载入失败</div><div class="es-msg">${e.message}</div></div>`; return; }
    const pairs = ((co.by_era || {})[era] || {}).pairs || [];
    if (!pairs.length) { box.innerHTML = '<p class="muted" style="padding:16px">该卷制暂无考点共现数据</p>'; return; }
    if (!(await GZ.ensureECharts())) { GZ.chartLoadError(box); return; }
    box.innerHTML = '<div id="graph-viz-c" style="height:520px"></div>';
    if (window.__gGraphInst) { try { window.__gGraphInst.dispose(); } catch (e) { /* 已游离 */ } }   // 释放上次实例(防累积泄漏)
    window.__gGraphInst = GZ.renderCooccurNetwork(document.getElementById("graph-viz-c"), pairs, { eraLabel, srEl: "#graph-sr" });
    if (!window.__rzGraph) { window.__rzGraph = 1; window.addEventListener("resize", () => window.__gGraphInst && window.__gGraphInst.resize()); }
  }

  register("graph", async () => {
    CONTENT.innerHTML = '<div class="loading-state"><span class="ls-dot"></span>载入知识图谱…</div>';
    const [gstats, trend] = await Promise.all([
      fetchJSON("/api/graph/stats"),  // RC1/D0: 图谱主数据, 失败必抛 → route() 错误态
      fetchJSON("/api/trend/summary").catch(() => ({})),
    ]);
    const nodeKinds = gstats.nodes || gstats.by_node_type || {};
    const relations = gstats.edges || gstats.by_relation || {};
    const totN = gstats.total_nodes || Object.values(nodeKinds).reduce((a, v) => a + v, 0);
    const totE = gstats.total_edges || Object.values(relations).reduce((a, v) => a + v, 0);
    const topTypes = Object.entries(nodeKinds).sort((a, b) => b[1] - a[1]).slice(0, 6)
      .map(([k, v]) => `${k} <b style="color:var(--ink)">${v}</b>`).join(" · ");

    CONTENT.innerHTML = `
      ${GZ.pageHead("高中 · 考点关联", "哪些考点总是一起考", "共现 = 同一道真题里同时考到; 高频组合就是命题套路。点大 = 考查次数多 · 线粗 = 同题一起考 · 点任意考点看它的真题。")}

      <section class="bk-card" style="margin-bottom:14px">
        <div class="bk-h"><span>考点共现关联 <small id="graph-center" style="color:var(--accent-ink)">新高考II 2021+</small></span>
          <span class="bk-src">/api/exam_point/cooccurrence</span></div>
        <div style="margin:2px 0 8px;font-size:12px;color:var(--ink-3)">卷制:
          <button class="bk-pill gz-era on" data-era="2021+_新高考II" data-label="新高考II 2021+">2021+ 新高考II</button>
          <button class="bk-pill gz-era" data-era="2015-2020_旧课标II" data-label="旧课标II 2015–20">2015–2020 旧课标II</button>
        </div>
        <div id="graph-viz" style="min-height:520px"></div>
        <div id="graph-sr" class="sr-only"></div>
      </section>

      <div class="bk-grid">
        <section class="bk-card"><div class="bk-h"><span>图谱规模 <small>底座资产</small></span><span class="bk-src">/api/graph/stats</span></div>
          <div style="font-size:12.5px;color:var(--ink-2);line-height:1.9">共 <b style="color:var(--ink)">${totN.toLocaleString()}</b> 节点 / <b style="color:var(--ink)">${totE.toLocaleString()}</b> 边 · ${topTypes}</div>
          <p class="muted" style="font-size:11px;margin:6px 0 0">单概念深入(某词/语法的 4 路追溯) → 「讲课调取」tab</p>
        </section>
        <section class="bk-card"><div class="bk-h"><span>命题趋势 · 题型分布(卷制era)</span><span class="bk-src">/api/trend/summary</span></div>
          ${trend.trend_reliable === false ? `<div class="caveat-banner" style="margin:0 0 6px"><span class="cb-tag">样本不足</span><span>逐年样本不足不画斜率; 按卷制 era 看分布(跨 2021 断点不混算)</span></div>` : ""}
          ${Object.entries(trend.type_distribution_by_era || {}).map(
            ([era, types]) => `<div style="font-size:12.5px;margin:3px 0"><b>${era}</b>: ${Object.entries(types).sort((a, b) => b[1] - a[1]).slice(0, 4).map(([t, n]) => `${t}(${n})`).join(" / ")}</div>`
          ).join("") || '<p class="muted" style="font-size:12px">无趋势数据</p>'}
          <p class="muted" style="font-size:11px;margin:6px 0 0">注 题量为真题**条目数**, 跨 source 粒度不一(2021/22 子题级, 其余年篇章级) → 仅看各 era 内题型相对构成, 不作跨 era 题量直接比较。题型存废真值见上"题型结构演变"(粒度无关)。</p>
        </section>
      </div>`;

    CONTENT.querySelectorAll(".gz-era").forEach(b => b.onclick = () => {
      CONTENT.querySelectorAll(".gz-era").forEach(x => x.classList.remove("on"));
      b.classList.add("on");
      _renderCooccur(b.dataset.era, b.dataset.label);
    });
    _renderCooccur("2021+_新高考II", "新高考II 2021+");
  });

})();
