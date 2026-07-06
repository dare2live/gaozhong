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
  // 坑(2026-07-06 数据关联设计审查): 原 hash 只解析第一段(page name), 无参数解析能力——
  // "40节课程"课节的 covers_exam_points 后端已算好, 但没法带着跳去"组卷"预筛选, 只能手动
  // 重新在组卷页里找。二级段(#/qbank/exam_point:theme_l2:XX)解析成 param 传给 mount(param),
  // 无参数的旧 tab 不受影响(多余参数JS天然忽略, 无需逐个改签名)。
  function route() {
    const hash = (location.hash || "#/beike").slice(2);  // strip "#/" (命题研判=默认落地页)
    const parts = hash.split("/");
    const name = (parts[0] || "beike").toLowerCase();
    const param = parts.length > 1 ? decodeURIComponent(parts.slice(1).join("/")) : null;
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
      mount(param).catch(err => {
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
  //    替代旧 course-grid+handout (旧生成内容已回滚; 内容生成待就绪门)。
  //    ④ 重构: 覆盖证明4轴微条 + 课程地图分段条 + 主题群章 + 课节timeline (数字全活取 API, 禁编造)。
  // ===================================================================
  const _esc = s => String(s == null ? "" : s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  function _covLine(cov) {
    // coverage fetch 失败时的文本 fallback (数据源 = syllabus 自带 coverage_proof)
    const ax = (cov && cov.axes) || {};
    const part = (k, name) => {
      if (!ax[k] || !ax[k].n_total) return "";
      const eff = Math.round(100 * ax[k].high_yield_n / ax[k].n_total);
      return `${name} ${ax[k].n_total} 考点 (覆盖${cov.target_pct}%需 ${ax[k].high_yield_n}, 即 ${eff}%)`;
    };
    return [part("genre", "题材"), part("theme_l2", "主题群"), part("word", "高频考词"), part("grammar", "语法")].filter(Boolean).join(" · ");
  }
  // ④-1 覆盖证明 4 轴微条: 实色段 = 教的高产出考点集; 空心描边段 = 诚实长尾缺口。语法轴 top 已有人话 label (P2-4 service 映射), 各轴微条 title 带最热 top3。
  const _COV_AXES = [["genre", "题材", "类"], ["theme_l2", "主题群", "组"], ["word", "高频考词", "词"], ["grammar", "语法", "项"]];
  function _covProof(cov) {
    const ax = (cov && cov.axes) || {};
    const rows = _COV_AXES.map(([k, name, unit]) => {
      const a = ax[k];
      if (!a || !a.n_total) return "";
      const fill = Math.round(100 * a.high_yield_n / a.n_total);
      const wpct = Math.round(a.high_yield_pct != null ? a.high_yield_pct : cov.target_pct);
      const tail = a.tail_n != null ? a.tail_n : (a.n_total - a.high_yield_n);
      const gap = fill < 100 ? `<span class="ks-cov-gap" style="width:${100 - fill}%" title="长尾 ${tail} ${unit}: 低频考点, 明确不覆盖 (性价比低)"></span>` : "";
      // 词轴 top 是 say/year/time 停用词级噪声 (方案书 rejected: "背 time"=负价值), 不展示; 其余轴 top3 人话
      const top3 = k === "word" ? "" : (a.top || []).slice(0, 3).map(t => t.label).filter(Boolean).join(" / ");
      return `<div class="ks-cov-row">
        <span class="ks-cov-axis">${name}</span>
        <span class="ks-cov-bar" role="img" aria-label="${name}: 教 ${a.high_yield_n}/${a.n_total} ${unit} = ${wpct}% 考查权重; 长尾 ${tail} ${unit}不教"${top3 ? ` title="最热: ${_esc(top3)}"` : ""}><span class="ks-cov-fill" style="width:${fill}%"></span>${gap}</span>
        <span class="ks-cov-txt">教 <b>${a.high_yield_n}</b>/${a.n_total} ${unit} = <b>${wpct}%</b> 考查权重</span>
      </div>`;
    }).filter(Boolean).join("");
    return rows ? `<div class="ks-cov">${rows}</div>` : "";
  }
  // ④-2 lessons 按 focus 连续分块 → 主题群 (顺序 = 后端命题频次分配序, 前端不重排不发明)
  function _themeGroups(lessons) {
    const gs = [];
    for (const l of (lessons || [])) {
      const last = gs[gs.length - 1];
      if (!last || last.focus !== l.focus) gs.push({ focus: l.focus, ttw: l.theme_total_weight || 0, lessons: [] });
      gs[gs.length - 1].lessons.push(l);
    }
    return gs;
  }
  // 段/章色循环 (设计规范 §02 蓝阶令牌, 相邻异色; 白字仅 --down/--down-2 底, --down-3 浅段标签用 --ink)
  const _SEGC = [["var(--down)", "#fff"], ["var(--down-2)", "#fff"], ["var(--down-3)", "var(--ink)"]];
  function _courseMap(gs) {
    const segs = gs.map((g, i) => {
      const [bg, fg] = _SEGC[i % _SEGC.length];
      const t = `${g.focus} · ${g.lessons.length} 节`;
      return `<button type="button" class="ks-map-seg" data-ch="ks-ch-${i}" style="flex:${g.lessons.length} 1 0;background:${bg};color:${fg}" title="${_esc(t)} — 点击跳到该章">${g.lessons.length >= 3 ? _esc(t) : ""}</button>`;
    }).join("");
    return `<div class="ks-map" role="navigation" aria-label="课程地图: ${gs.length} 个主题群分段, 段宽=节数, 点击跳到对应章">${segs}</div>`;
  }
  // ④-3 章头累计里程碑: coverage.theme_l2.top 按 label 匹配 cum_pct; 无 cum_pct 则 freq/weight_total 前端累加; 都不能算返回 null (省略句, 禁编造)
  function _cumPct(theme, focus) {
    let acc = 0;
    for (const t of ((theme && theme.top) || [])) {
      acc += t.freq || 0;
      if (t.label === focus) {
        if (t.cum_pct != null) return t.cum_pct;
        return theme.weight_total ? Math.round(1000 * acc / theme.weight_total) / 10 : null;
      }
    }
    return null;
  }
  function _chapter(g, i, sumTtw, theme) {
    const [bg] = _SEGC[i % _SEGC.length];
    const wpct = sumTtw ? Math.round(100 * g.ttw / sumTtw) : null;
    const cum = _cumPct(theme, g.focus);
    return `<section class="ks-chapter" id="ks-ch-${i}">
      <header class="ks-ch-head">
        <div class="ks-ch-row">
          <span class="ks-ch-dot" style="background:${bg}"></span>
          <h2 class="ks-ch-name">${_esc(g.focus)}</h2>
          <span class="ks-ch-n">${g.lessons.length} 节</span>
          ${wpct != null ? `<span class="ks-ch-wbar" title="本主题群占全部主题考查权重的 ${wpct}%"><span style="width:${wpct}%"></span></span><span class="ks-ch-wtxt">考查权重 ${wpct}%</span>` : ""}
        </div>
        ${cum != null ? `<p class="ks-ch-cum">学完本组已覆盖考试权重 ${cum}%</p>` : ""}
      </header>
      <div class="ks-tl">${g.lessons.map(l => `<div class="ks-tl-item">${_lessonCard(l)}</div>`).join("")}</div>
    </section>`;
  }
  // ④-4 课节行: timeline 节点 + 「第 N 节 · 作业 N 道真题」(裸权重数字已上收章头); 展开 = 作业清单 + 正文状态
  function _lessonCard(l) {
    // 溯源友好化: 显示"年份 辽宁卷 · #题号", 原始 source_file#index 入 title (机器血缘); 不甩裸 gb/... 路径
    const _srcShort = q => `${q.year} 辽宁卷 · #${(q.source || "").split("#").pop()}`;
    // 坑(2026-07-05 教师视角审计): preview 有时是原文段落, 有时是子题设问句本身(如"32. What does
    // Levine want to explain..."), 卡片外观统一当"原文预览"展示, 后者读起来像截断的乱码而非
    // 有意义的设问。加"设问:"前缀区分, 不改数据(内容本身是真实来源, 只是展示层加了归类标签)。
    // 坑(2026-07-05 根因审计): 判断已抽共享 GZ.isSubqPreview(≥3处需要, Rule5); preview 现由后端
    // clean_preview 统一裁边界+按需补省略号, 前端不再无条件追加"…"。
    const hw = (l.evidence_questions || []).map(q =>
      `<li class="ks-hw"><span class="ks-hw-t">${_esc(q.question_type)}</span><span class="ks-hw-p">${GZ.isSubqPreview(q.preview) ? "设问: " : ""}${_esc(q.preview)}</span><span class="ks-hw-s" title="原卷溯源: ${_esc(q.source)}">${_esc(_srcShort(q))}</span></li>`).join("");
    // 坑(2026-07-06 数据关联设计审查): covers_exam_points 后端早算好但前端从未读取, 老师想给这节课
    // 补充练习只能手动去组卷页重新找。带着考点焦点跳组卷预筛选(route()新支持二级hash参数)。
    const focus = (l.covers_exam_points || [])[0];
    const focusLink = focus ? `<a class="ks-hw-more" href="#/qbank/${encodeURIComponent(focus)}">按此考点补充练习 →</a>` : "";
    return `<details class="ks-lesson"><summary class="ks-sum">
        <span class="ks-seq">第 ${l.seq} 节</span>
        <span class="ks-hwn">· 作业 ${(l.evidence_questions || []).length} 道真题</span>
      </summary>
      <div class="ks-body">
        <div class="ks-body-h">作业真题 (辽宁卷, 可溯源原卷; 非生成)</div>
        <ul class="ks-hwlist">${hw || '<li class="ks-hw">本节真题作业整理中</li>'}</ul>
        <div class="ks-soon">正文即将上线</div>
        ${focusLink}
      </div>
    </details>`;
  }
  register("teaching", async () => {
    CONTENT.innerHTML = '<div class="loading-state"><span class="ls-dot"></span>载入课程框架…</div>';
    const [syl, cov, stg] = await Promise.all([fetchSafe("/api/course/syllabus"), fetchSafe("/api/course/coverage"), fetchSafe("/api/k12/tested_word_stage")]);
    if (isErr(syl)) { CONTENT.innerHTML = '<div class="error-state"><div class="es-title">课程框架加载失败</div><div class="es-msg">后端未就绪 — 真实错误。</div></div>'; return; }
    const gs = _themeGroups(syl.lessons);
    const sumTtw = gs.reduce((a, g) => a + (g.ttw || 0), 0);
    const covOk = !isErr(cov) && cov && cov.axes;
    const theme = covOk ? cov.axes.theme_l2 : null;
    CONTENT.innerHTML = `<section class="scaffold">
      ${GZ.pageHead(`高中 · ${syl.n_lessons} 节课程`, `${syl.n_lessons} 节课覆盖高考主题全集`, "按命题频次分配 — 用最少的课覆盖最大的考查权重; 每节一个考点焦点 + 可溯源的辽宁真题作业。")}
      <div class="caveat-banner"><span class="cb-tag">进度</span><span><b>讲义制作中</b> — 每节已定考点焦点与真题作业, <b>作业现在就能做</b>; 可背诵正文上线前不占位不伪造。</span></div>
      <div class="sc-takeaway">
        <div class="sc-tk-h">覆盖证明 · 用最少的课覆盖最大考查权重</div>
        ${covOk ? _covProof(cov) : `<p class="sc-tk-body">${_esc(_covLine(syl.coverage_proof || {}) || "覆盖数据加载失败。")}</p>`}
        <p class="sc-tk-caveat">实色段 = 课程教的高产出考点; 空心段 = 低频长尾, 明确标出不假装全覆盖。为什么主攻高中新增词? ${!isErr(stg) ? GZ.stageMiniBand(stg) : ""}考查词大头初中前已学 — 详见<a href="#/zhenti">真题特点</a>。</p>
      </div>
      <p class="ks-map-cap">课程地图 · ${syl.n_lessons} 节按主题群分段, 段宽 = 节数 · 点击跳到该章</p>
      ${_courseMap(gs)}
      ${gs.map((g, i) => _chapter(g, i, sumTtw, theme)).join("")}
      <div class="ks-foot">
        <p class="ks-foot-link">做作业遇到生词? 去 <a href="#/jichu">基础库</a> 查词和课本出处。</p>
        <details class="ks-how"><summary>数据怎么来的?</summary>
          <ul>
            <li>作业 = 历年辽宁卷真题原题, 每道都标年份和题号, 可查回原卷 — 不是生成题, 不是押题。</li>
            <li>考点焦点 = 按真题命题频次把 ${syl.n_lessons} 节课分给各主题群: 考得多的主题, 分到的课就多。</li>
            <li>覆盖 = 课程教的考点占考试考查权重的比例; 低频长尾考点明确标出, 不假装全覆盖。</li>
          </ul>
        </details>
      </div>
    </section>`;
    // 课程地图段点击 → 平滑锚滚到对应章
    CONTENT.querySelectorAll(".ks-map-seg").forEach(b => b.onclick = () => {
      const el = document.getElementById(b.dataset.ch);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });


  // ===================================================================
  // C. 题库 + 组卷
  // ===================================================================
  register("qbank", async (focusTag) => {
    // 题库浏览器: 按题型筛真题 (全 fetch /api/qb/* 单算点; 仅真题无押题)。
    // focusTag: 从"40节课程"课节带来的考点焦点(如 exam_point:theme_l2:XX), route()二级hash参数解析。
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
    CONTENT.innerHTML = `
      <h2>题库 + 组卷 <span class="muted" style="font-size:14px;font-weight:400">${totalN} 题 · 仅已核验真题 (无押题)</span></h2>
      <p class="muted" style="margin:2px 0 10px;font-size:12.5px">按题型筛选浏览; 或一键生成蓝图练习卷(题面均历年真题, 结构对齐非预测)。<span id="qb-difftext"></span>。</p>
      <div class="bk-filter" id="qb-blueprint" style="margin-bottom:10px;">
        <span class="bk-flabel">蓝图练习卷</span>
        <label style="font-size:12px;color:var(--ink-3);">题量 <input id="qb-bp-total" type="number" value="30" min="5" max="60" style="width:54px;padding:3px 6px;border:1px solid var(--line);border-radius:6px;"></label>
        <button id="qb-bp-go" class="bk-pill on">${GZ.icon("grid")} 生成蓝图练习卷</button>
        <span class="muted" style="font-size:11px;">按考纲蓝图结构从真题加权抽样 · 非预测/非押题</span>
      </div>
      <details id="qb-compose" ${focusTag ? "open" : ""} style="margin-bottom:10px;font-size:13px;"><summary style="cursor:pointer;color:var(--accent-ink);">${GZ.icon("gear")} 自定义组卷 (按题型/标签/难度/年份精确组卷, 收敛自 legacy)</summary>
        ${focusTag ? `<p class="muted" style="font-size:11.5px;margin:4px 0 0;">从"40节课程"带来的考点焦点已自动填入下方"必含标签"并组卷。</p>` : ""}
        <div class="bk-filter" style="margin-top:8px;flex-wrap:wrap;">
          <label>题型分布 <input id="qb-c-mix" value="${defMix}" style="width:280px;padding:3px 6px;border:1px solid var(--line);border-radius:6px;"></label>
          <label>必含标签 <input id="qb-c-req" value="${focusTag ? _esc(focusTag) : ""}" placeholder="如: word:abandon(必含此词) 或 unit:waiyan/bixiu_1/U1(必含此单元)" title="按词/单元/考点筛选, 格式: word:词 或 unit:册次/单元 或 exam_point:维度:标签, 多个用逗号分隔" style="width:260px;padding:3px 6px;border:1px solid var(--line);border-radius:6px;"></label>
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
    // 坑(2026-07-05 根因审计): "长/中/短"篇幅分布原只从全库 st.by_difficulty 算一次, 筛题型后不
    // 跟着更新, 但那行提示文字仍挂在筛选区上方(误导成"当前筛选口径")。改成按当前 list 现算, 并
    // 显式标注口径(全库 vs 当前筛选), 消歧义。
    const diffLine = document.querySelector("#qb-difftext");
    const renderDiffLine = (rowsForCount, scopeLabel) => {
      if (!diffLine) return;
      const cnt = { hard: 0, mid: 0, easy: 0 };
      rowsForCount.forEach(r => { if (cnt[r.difficulty] != null) cnt[r.difficulty]++; });
      diffLine.textContent = `题面篇幅(字数估·非难度, ${scopeLabel}) 长 ${cnt.hard} · 中 ${cnt.mid} · 短 ${cnt.easy}`;
    };
    renderDiffLine([], "全库口径"); // 占位, loadList 首轮会用当前筛选覆盖
    const loadList = async () => {
      const url = "/api/qb/browse?limit=80" + (qtype ? "&type=" + encodeURIComponent(qtype) : "");
      const rows = await fetchJSON(url).catch(() => []);
      const list = Array.isArray(rows) ? rows : (rows.rows || []);
      renderDiffLine(list, qtype ? `当前筛选「${qtype}」` : "全库, 未筛选");
      $("#qb-list").innerHTML = list.length ? `<div class="qb-list">${list.map(r => {
        const df = DIFF[r.difficulty] || ["", "var(--ink-3)"];
        const stem = (r.stem_preview || "").replace(/</g, "&lt;");
        return `<div class="qb-row"><span class="qb-tb">${r.question_type || ""}</span><span class="qb-stem">${GZ.isSubqPreview(stem) ? "设问: " : ""}${stem}</span><span class="qb-ans">${r.answer || ""}</span><span class="qb-diff" style="color:${df[1]}">${df[0]}</span></div>`;
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
      // 坑(2026-07-05 根因审计): 原 JSON.stringify(sf) 把大括号/引号/冒号这类内部数据结构语法直接
      // 甩进老师可读的提示段落, 改成自然语言列举。
      const sfText = hasSf
        ? (Array.isArray(sf) ? sf.join("、") : Object.entries(sf).filter(([, v]) => v > 0).map(([k, v]) => `${k} 缺${v}题`).join("、"))
        : "";
      const shortf = hasSf ? `<p class="muted" style="color:var(--warn);font-size:12px;margin:4px 0;">注 部分题型库存不足: ${esc(sfText)}（诚实披露, 不补押题）</p>` : "";
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
    if (focusTag) genCompose();   // 带考点焦点跳转过来 → 自动组一次卷, 不用老师再点一次
    await loadList();
  });



  // ===================================================================
  // F. 知识图谱 (本tab: stats概览 + 高频考点词入口; 力导向SVG探索仍在 /legacy, 见 needs_user_decision UI收敛)
  // ===================================================================
  // 渲染考点共现网络 — 复用 GZ.renderCooccurNetwork 单一口径。
  // (坑 2026-07-05 数据可视化审计: 原注释称"与「讲课调取」C' 同源同配色", jiangke.js 已在
  // 2026-07-02 教师工具下线 commit 8fffd70 整体删除, 现渲染函数唯一调用方就是本 tab — 文档漂移已清)
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

  // N6 (用户: "没看明白有啥关联性"): 结论先行 — top3 共现对句子化成"命题套路"结论, 图退为证据;
  // 精确读数走可见降序列表 (sr-only 表转正)。纯渲染层排序 (common.js:281 先例, 零后端)。
  const _DIM_CN = { genre: "题材", theme_context: "主题", theme_l2: "主题群", cognitive_skill: "设问思维" };
  function _coChips(pairs) {
    const top = [...pairs].sort((x, y) => y.co_n - x.co_n).slice(0, 3);
    // 坑(2026-07-05 教师视角审计): chip 原只报"一起考了 N 次", 没有分母, 老师看不出这是
    // 该类目大部分场合都这么配(真规律)还是小样本巧合。用同一份 pairs 数据算该 a_label
    // 参与的全部已收录共现次数之和作分母(不发新请求, 复用已有响应), 诚实披露占比。
    const totalFor = label => pairs.reduce((s, p) => s + ((p.a_label === label || p.b_label === label) ? p.co_n : 0), 0);
    return top.map(p => {
      const hint = p.a_dim === "genre" ? ` — 见「${_esc(p.a_label)}」先想「${_esc(p.b_label)}」` : "";
      const denom = totalFor(p.a_label);
      const denomNote = denom > p.co_n ? ` (占「${_esc(p.a_label)}」已收录共现的 ${p.co_n}/${denom})` : "";
      return `<div class="kg-chip"><b>${_esc(p.a_label)} × ${_esc(p.b_label)}</b><span class="kg-chip-n">同一道题里一起考了 ${p.co_n} 次${denomNote}</span>${hint ? `<span class="kg-chip-h">${hint}</span>` : ""}</div>`;
    }).join("");
  }
  function _coList(pairs) {
    const sorted = [...pairs].sort((x, y) => y.co_n - x.co_n);
    const max = sorted.length ? sorted[0].co_n : 1;
    return sorted.map(p =>
      `<div class="kg-row"><span class="kg-row-l">${_esc(p.a_label)} <span class="kg-x">×</span> ${_esc(p.b_label)}</span>
        <span class="kg-row-bar"><span style="width:${Math.round(100 * p.co_n / max)}%"></span></span>
        <span class="kg-row-n">同题 ${p.co_n} 次</span></div>`).join("");
  }

  // 全景图谱骨架 (2026-07-04 用户提议: 词/教材年级/短语句型/语法 跟课标考纲的全量关系可视化).
  // 与上面"共现网络"是两回事: 共现网络=21个考点间的命题套路证据; 这里=全库 word/question/grammar/
  // unit/phrase/exam_point/theme 等实体的全量关系骨架(judge panel方案B: 分层Top-N+点击展开)。
  async function _renderAtlas() {
    const box = document.getElementById("atlas-viz");
    if (!box) return;
    box.innerHTML = '<div class="loading-state"><span class="ls-dot"></span>载入全景图谱…</div>';
    let data;
    try { data = await fetchJSON("/api/graph/atlas"); }
    catch (e) { box.innerHTML = `<div class="error-state" style="margin:0"><div class="es-title">全景图谱载入失败</div><div class="es-msg">${e.message}</div></div>`; return; }
    if (!data.nodes || !data.nodes.length) { box.innerHTML = '<p class="muted" style="padding:16px">暂无图谱数据</p>'; return; }
    if (!(await GZ.ensureECharts())) { GZ.chartLoadError(box); return; }
    box.innerHTML = '<div id="atlas-viz-c" style="height:560px"></div>';
    if (window.__gAtlasInst) { try { window.__gAtlasInst.dispose(); } catch (e) { /* 已游离 */ } }
    window.__gAtlasInst = GZ.renderAtlasGraph(document.getElementById("atlas-viz-c"), data);
    if (!window.__rzAtlas) { window.__rzAtlas = 1; window.addEventListener("resize", () => window.__gAtlasInst && window.__gAtlasInst.resize()); }
    const tm = document.getElementById("atlas-meta");
    if (tm) {
      // 坑(2026-07-05 数据可视化审计): 原写死 !=="stage" && !=="cefr_level", 与 common.js
      // renderAtlasGraph 内部的排除集合各自维护一份硬编码, 现改读 API 单点回传的
      // attribute_only_node_types(与图表内部排除逻辑同一份真相源, 防止两处计数将来悄悄分叉)。
      const attrOnly = new Set(data.attribute_only_node_types || []);
      const drawn = data.nodes.filter(n => !attrOnly.has(n.node_type)).length;
      // 坑(2026-07-05 教师视角审计): 原一次性展示16项"类型:展示数/总数"流水账, 读起来像工程
      // 审计日志。改一句人话结论常显 + 明细收进折叠details(默认收起, 想看再展开)。
      const rows = Object.entries(data.type_meta || {})
        .sort((a, b) => b[1].total - a[1].total)
        .map(([t, m]) => `${t}${m.capped ? ` 取Top${m.shown}/${m.total}` : ` 全展示${m.total}`}`).join(" · ");
      tm.innerHTML = `图上是连接最多的词/句子; 其余类型全部展示。共 ${drawn} 节点 / ${data.edges.length} 条关系边`
        + `(另 学段+课标级别 ${data.nodes.length - drawn} 个仅作词条属性不画点)。`
        + `<details style="display:inline;margin-left:4px;"><summary style="display:inline;cursor:pointer;">按类型展开明细</summary><div style="margin-top:4px;">${rows}</div></details>`;
    }
  }

  // 坑(2026-07-06 数据关联设计审查): "某语法点历年怎么考"这条链在导航内完全查不到——考点关联页
  // 两块图(共现网络/全景图谱)都不能回答, tests_grammar 边从不参与共现网络的计算, 全景图谱也没有
  // "历年"时间维度; 真正的语法频次数据在 /api/grammar/stats(已就绪, 零后端改动), 只是没接到这页。
  // 轻量摘要(非重复真题特点页的完整语法卡), 只回答"这条链查得到吗", 详情跳转真题特点。
  function _grammarLinkSection(ge) {
    if (!ge) return "";
    const eras = ge.eras_covered || [];
    if (!eras.length) return '<p class="muted" style="font-size:12px;">语法考查数据暂无(诚实标, 非0)。</p>';
    const eraRows = eras.map(era => {
      const block = (ge.by_era || {})[era] || {};
      const top = (block.by_category || []).slice(0, 4);
      const items = top.map(c => `<span class="tk-tchip">${_esc(c.category)} <b>${c.pct}%</b></span>`).join("");
      return `<div style="margin:4px 0;"><b style="font-size:12px;">${_esc(era.replace(/^[\d.+-]+_/, ""))}</b> (n=${block.n_questions || 0}题): ${items || '<span class="muted">无数据</span>'}</div>`;
    }).join("");
    const missing = (ge.eras_missing || []).length
      ? `<p class="muted" style="font-size:11px;margin-top:4px;">${(ge.eras_missing || []).map(e => e.replace(/^[\d.+-]+_/, "")).join("、")} 暂无 tests_grammar 边覆盖(诚实标缺口, 非估算)。</p>` : "";
    return `${eraRows}${missing}<p style="margin:6px 0 0;"><a href="#/zhenti" class="bk-vlink" style="font-size:12px;">完整语法考点卡(时态/从句/句型/词法) → 真题特点</a></p>`;
  }

  register("graph", async () => {
    CONTENT.innerHTML = '<div class="loading-state"><span class="ls-dot"></span>载入知识图谱…</div>';
    const [co, gram] = await Promise.all([
      fetchJSON("/api/exam_point/cooccurrence"),   // 主数据, 失败必抛 → route() 错误态
      fetchSafe("/api/grammar/stats"),             // 语法关联小节 (零后端改动, 已有端点)
    ]);
    const eraPairs = ((co.by_era || {})["2021+_新高考II"] || {}).pairs || [];

    CONTENT.innerHTML = `
      ${GZ.pageHead("高中 · 考点关联", "哪些考点总是一起考", "共现 = 同一道真题里同时考到。高频组合就是命题套路: 先看下面的结论, 网络图是它的证据。")}

      <div class="sc-takeaway">
        <div class="sc-tk-h">命题套路 · 这些考点常绑着出题</div>
        <div id="kg-chips" class="kg-chips">${_coChips(eraPairs)}</div>
        <p class="sc-tk-caveat">口径: 2021+ 新高考II 卷实测计数, 共现 ≠ 因果; 题材/主题为 AI 标注 · 方向参考。</p>
      </div>

      <section class="bk-card" style="margin-bottom:14px">
        <div class="bk-h"><span>共现网络 · 证据图 <small id="graph-center" style="color:var(--accent-ink)">新高考II 2021+</small></span>
          <span class="bk-src">/api/exam_point/cooccurrence</span></div>
        <div style="margin:2px 0 8px;font-size:12px;color:var(--ink-3)">卷制:
          <button class="bk-pill gz-era on" data-era="2021+_新高考II" data-label="新高考II 2021+">2021+ 新高考II</button>
          <button class="bk-pill gz-era" data-era="2015-2020_旧课标II" data-label="旧课标II 2015–20">2015–2020 旧课标II</button>
        </div>
        <p class="kg-legend">怎么读: <b>点越大</b> = 这个考点考得越多 · <b>线越粗</b> = 两个考点在同一道题里一起出现越多 · <b>点任意点</b>弹出它的真题</p>
        <div id="graph-viz" style="min-height:520px"></div>
        <div id="graph-sr" class="sr-only"></div>
      </section>

      <section class="bk-card">
        <div class="bk-h"><span>全部共现组合 · 精确读数</span><small class="muted" id="kg-list-era">新高考II 2021+</small></div>
        <div id="kg-list">${_coList(eraPairs)}</div>
        <p class="muted" style="font-size:11.5px;margin:8px 0 0">按同题次数降序全量列出 (不截断); 次数小的组合只说明"出现过", 别过度解读。</p>
      </section>

      <section class="bk-card" style="margin-top:14px">
        <div class="bk-h"><span>语法关联 · 历年怎么考</span><span class="bk-src">/api/grammar/stats</span></div>
        <p class="kg-legend">上面两张图只覆盖 genre/theme/cognitive_skill 等考点维度, 不含语法点 — 语法频次单独在这里查, 按课标第二级子类分卷制展示。</p>
        <div id="graph-grammar">${_grammarLinkSection((!isErr(gram)) ? gram.grammar_exam : null)}</div>
      </section>

      <p class="zt-nextlink">这些套路已编进课程 → <a href="#/teaching">40 节课程</a></p>

      <section class="bk-card" style="margin-top:14px">
        <div class="bk-h"><span>全景图谱 · 全库浏览</span><span class="bk-src">/api/graph/atlas</span></div>
        <p class="kg-legend">这是全库骨架 — 单词/真题/语法点/短语句型/教材单元/考点/主题/题型 之间的真实关系(不是上面那张考点共现图)。
          <b>数量少的类型全展示, 单词/真题这类数量大的类型只显示连接最多的头部</b>, 点节点可下钻真题/详情; 图例可点选只看某一类。
          学段/课标级别(义务教育/必修/选必等)不单独画点, 放在词条 hover 里看。</p>
        <div id="atlas-viz" style="min-height:560px"></div>
        <p class="muted" id="atlas-meta" style="font-size:11px;margin:6px 0 0"></p>
      </section>`;

    CONTENT.querySelectorAll(".gz-era").forEach(b => b.onclick = () => {
      CONTENT.querySelectorAll(".gz-era").forEach(x => x.classList.remove("on"));
      b.classList.add("on");
      _renderCooccur(b.dataset.era, b.dataset.label);
      // 结论 chips + 精确列表随 era 联动 (同一数据源, 单 fetch)
      const ps = ((co.by_era || {})[b.dataset.era] || {}).pairs || [];
      const chips = document.getElementById("kg-chips"); if (chips) chips.innerHTML = _coChips(ps);
      const list = document.getElementById("kg-list"); if (list) list.innerHTML = _coList(ps);
      const le = document.getElementById("kg-list-era"); if (le) le.textContent = b.dataset.label;
    });
    _renderCooccur("2021+_新高考II", "新高考II 2021+");
    _renderAtlas();
  });

})();
