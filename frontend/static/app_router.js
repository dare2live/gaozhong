/* SPA hash router — 7 tab (第五阶段 5.1).
   每 tab 一个 mount() 函数, 注册到 ROUTES dict. (M2 插件式 dispatch) */

(function () {
  const { $, $$, fetchJSON, fetchSafe, isErr, errorBox, mdToHtml } = window.GZ;
  const CONTENT = $("#content");

  // 多租户: /api/students/* 路由强制要求 teacher_id (域B 隔离); 缺则 {error} 致 students tab 崩 (A1修)。
  // pilot 单租户: 取第一个老师作默认; helper 自动附 teacher_id 到 students 调用。鉴权(登录派生teacher_id)=B1后补。
  let _tid = null;
  async function stuFetch(path) {
    if (_tid === null) {
      const t = await fetchJSON("/api/students/teachers").catch(() => ({ teachers: [] }));
      _tid = (t.teachers && t.teachers[0] && t.teachers[0].teacher_id) || "";
    }
    const sep = path.includes("?") ? "&" : "?";
    return fetchJSON(path + sep + "teacher_id=" + encodeURIComponent(_tid));
  }

  // 侧栏从 nav-config.js 数据渲染 (IA = 配置驱动, 非 hardcode HTML; 用户 no-hardcode 硬约束)
  function renderSidebar() {
    const nav = $(".tabnav");
    if (!nav || !window.GZ_NAV) return;
    nav.innerHTML = window.GZ_NAV.map(g =>
      `<div class="navgroup">${g.group}${g.tag ? `<span class="gtag">${g.tag}</span>` : ""}<span class="gline"></span></div>` +
      g.tabs.map(t =>
        `<a href="#/${t.id}" data-tab="${t.id}"><svg class="ic" viewBox="0 0 24 24" stroke="currentColor">${t.icon}</svg> ${t.label}${t.count ? `<span class="cnt" id="nav-cnt-${t.id}"></span>` : ""}</a>`
      ).join("")
    ).join("");
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
      ax.textContent = (fail || warn) ? `${fail} FAIL · ${warn} WARN` : `0 FAIL audit`;
      ax.style.color = fail ? "var(--accent-ink)" : (warn ? "var(--warn)" : "");
    }
  }

  // -- 注册表 (M2)
  const TABS = {};
  function register(name, mount) { TABS[name] = mount; }
  window.GZ.registerTab = register;   // 暴露给独立视图模块 (beike.js 等), 不在本god-file堆新tab

  // a11y (RC1#6): 模态 role=dialog 已加; 此处补 Esc 关闭 + 打开后焦点入模态(键盘/读屏不被遮罩困住)。全局一次绑定。
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    const m = document.querySelector("#handout-modal.open, #student-modal.open");
    if (m) m.classList.remove("open");
  });
  function _focusModal(id) {
    const btn = document.querySelector("#" + id + " .close-btn");
    if (btn) setTimeout(() => btn.focus(), 30);
  }

  // -- router
  function route() {
    const hash = (location.hash || "#/beike").slice(2);  // strip "#/" (备课驾驶舱=默认落地页)
    const name = (hash.split("/")[0] || "beike").toLowerCase();
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
    bar.innerHTML = `<span>旧版「${label}」功能已并入此统一入口（备课/组卷/教材/图谱/词典各 tab）。请更新书签到本页。</span>` +
      `<button class="gz-iconbtn" aria-label="关闭" title="关闭" style="padding:0 6px;">${GZ.icon("close")}</button>`;
    bar.querySelector("button").onclick = () => bar.remove();
    document.body.insertBefore(bar, document.body.firstChild);
  }

  window.addEventListener("DOMContentLoaded", () => { renderSidebar(); movedBanner(); if (!location.hash) location.hash = "#/beike"; route(); populateNavCounts(); });

  // ===================================================================
  // A. 工作台
  // ===================================================================
  register("workbench", async () => {
    // 今日态落地页: 全 fetch service 单一计算点(零硬编码派生数字); 命题研判头条前置(核心竞争力)。
    const [stats, cs, dict, cog, classes, audit] = await Promise.all([
      fetchJSON("/api/stats"),  // RC1/D0: 工作台主数据, 失败必抛 → route() 错误态
      fetchJSON("/api/course/stats").catch(() => ({})),
      fetchJSON("/api/exam_dictionary?prefix=zz&limit=1").catch(() => ({})),
      fetchJSON("/api/exam_point/cognitive_skill").catch(() => ({ by_era: {} })),
      stuFetch("/api/students/classes").catch(() => ({ count: 0, classes: [] })),
      fetchJSON("/api/audit/findings").catch(() => []),
    ]);
    const findings = Array.isArray(audit) ? audit : (audit.findings || []);
    const fail = findings.filter(f => f.severity === "FAIL").length;
    const warn = findings.filter(f => f.severity === "WARN").length;
    const ok = fail === 0 && warn === 0;
    const stu = (classes.classes || []).reduce((a, c) => a + (c.n_students || 0), 0);
    // 命题研判头条 — 从 cognitive_skill 取推断跨era迁移
    const inferPct = k => { const e = (cog.by_era || {}); for (const era in e) if (era.startsWith(k)) { const p = e[era].find(x => x.label === "推断"); if (p) return p.pct; } return null; };
    const oldI = inferPct("2015-2020"), newI = inferPct("2021");
    // RC1#9: 新高考II era n=15(<30) distribution_reliable=false → 头条不得渲成加粗确信结论(与beike口径一致, 防内部不一致/违D0)
    const relNew = (cog.reliability || {})["2021+_新高考II"] || {};
    const newReliable = relNew.distribution_reliable !== false;
    const metric = (v, u, k, href, demo) => `<div class="wb-metric">${href ? `<a href="${href}">` : ""}<div class="v">${v == null ? "-" : Number(v).toLocaleString()}${u ? `<span class="u">${u}</span>` : ""}</div><div class="k${demo ? " demo" : ""}">${k}</div>${href ? "</a>" : ""}</div>`;
    CONTENT.innerHTML = `
      <div class="wb-head">
        <h2>工作台 · 今日态</h2>
        <span class="wb-health ${ok ? "ok" : "bad"}">${ok ? "数据健康 · 三门全绿" : fail + " FAIL · " + warn + " WARN"}</span>
      </div>
      <p class="wb-sub">辽宁卷锚定 · 数据全来自 service 单一计算点 (D0=100% 准) · 命题真值可对外, 学情为示例</p>

      ${oldI != null && newI != null ? `<div class="wb-headline">
        <div class="ey">本周期命题研判${newReliable ? "" : " · 方向性参考"}</div>
        <div class="big">新高考重高阶推断: 推断占比 ${newReliable ? `<b>${oldI}% → ${newI}%</b>` : `${oldI}% → ${newI}%`} (旧课标II → 新高考II)</div>
        <div class="sub">教研解析显式题型真值 (explicit_label); 细节理解相应下行。${newReliable ? "" : `<b style="color:var(--warn)">注 新高考II n=${relNew.n || "<30"} 样本不足, 占比作方向性参考非精确分布。</b> `}<a href="#/beike">查考点驾驶舱 →</a></div>
      </div>` : ""}

      <div class="wb-metrics">
        ${metric(stats.exam_questions, "题", "历年真题 (辽宁卷研判)", "#/beike")}
        ${metric(dict.total, "词", "考试词典金矿", "#/dict")}
        ${metric(stats.question_bank, "题", "题库 (真题)", "#/qbank")}
        ${metric(cs.total_courses, "节", "分层课程", "#/teaching")}
        ${metric(stats.nodes, "", "知识图谱节点", "#/graph")}
        ${metric(stats.cefr_vocab, "词", "课标词汇", "#/dict")}
        ${metric(stats.textbooks, "册", "教材 (外研/人教)", "#/data")}
        ${metric(stu, "", "学生 / " + (classes.count || 0) + " 班", "#/students", true)}
      </div>

      <div class="wb-aud">
        ${findings.filter(f => f.severity !== "OK").slice(0, 5).map(f =>
          `<div class="row"><span class="sev ${f.severity}">${f.severity}</span><code>${f.audit_kind}</code><span class="muted" style="flex:1">${f.target || ""}: ${(f.actual || "").slice(0, 90)}</span></div>`
        ).join("") || `<div class="row"><span class="sev WARN" style="background:#EAF3EC;color:var(--good)">OK</span><span class="muted">${findings.length} 项审计全部通过, 无异常</span></div>`}
      </div>`;
  });

  // ===================================================================
  // B. 教学 — 40 节按 layer 分组 + 点击查讲义
  // ===================================================================
  register("teaching", async () => {
    CONTENT.innerHTML = `<h2>分层教学</h2><p class="muted">载入中...</p>`;
    const data = await fetchJSON("/api/course/list");
    const groups = { G1: [], G2: [], G3: [], G_FINAL: [] };
    for (const c of data.courses) groups[c.layer]?.push(c);
    const layerMeta = {
      G1: "高一系统课 · ~1200 词",
      G2: "高二系统课 · ~2200 词",
      G3: "高三上学期 · ~3000 词",
      G_FINAL: "高考前突击 · ~3500 词 · 真题密集",
    };
    let html = `<h2>分层教学 <span class="muted" style="font-size:14px;font-weight:400">${data.courses.length} 节 · 按 layer 分组</span></h2>`;
    for (const layer of ["G1", "G2", "G3", "G_FINAL"]) {
      const items = groups[layer];
      html += `<section class="layer-section">
        <h3>${layer} <span class="layer-meta">${layerMeta[layer]} · ${items.length} 节</span></h3>
        <div class="course-grid">`;
      for (const c of items) {
        html += `<div class="course-card ${c.layer}" role="button" tabindex="0" onclick="window._openHandout(${c.course_id})">
          <span class="cid">#${c.course_id}</span>
          <span class="layer-badge">${c.block_kind}</span>
          <div><strong>${c.title.replace(/^[GFINAL\d_·]+·/, "")}</strong></div>
          <div class="block">主题: ${c.themes_main || "(待补)"}</div>
        </div>`;
      }
      html += `</div></section>`;
    }
    html += `<div id="handout-modal" role="dialog" aria-modal="true" aria-label="课节内容" onclick="if(event.target===this)this.classList.remove('open')">
      <div class="modal-body">
        <button class="gz-iconbtn close-btn" aria-label="关闭" onclick="document.getElementById('handout-modal').classList.remove('open')">${GZ.icon("close")}</button>
        <button class="print-btn" onclick="window.GZ.printWithCharts()">打印 / PDF</button>
        <div id="handout-md">载入中 ...</div>
      </div>
    </div>`;
    CONTENT.innerHTML = html;
  });

  // -- 讲义分段元数据 (Phase 7.1)
  const SEG_META = [
    { key: "header",    icon: "", label: "" },
    { key: "hook",      icon: "", label: "开场 hook", match: "hook" },
    { key: "review",    icon: "", label: "上节复习",  match: "复习" },
    { key: "core",      icon: "", label: "核心教学",  match: "核心" },
    { key: "relations", icon: "", label: "关联拓展",  match: "关联" },
    { key: "exam",      icon: "", label: "真题溯源",  match: "真题" },
    { key: "practice",  icon: "", label: "场景练习",  match: "场景" },
    { key: "homework",  icon: "", label: "课后作业",  match: "作业" },
    { key: "summary",   icon: "", label: "总结收束",  match: "总结" },
  ];

  function _classifySegment(text) {
    const first = text.split("\n").find(l => l.trim()) || "";
    for (let i = 1; i < SEG_META.length; i++) {
      if (first.includes(SEG_META[i].match)) return SEG_META[i];
    }
    return SEG_META[0];
  }

  function _renderSegments(raw) {
    const parts = raw.split(/\n---\n/);
    if (parts.length < 2) return mdToHtml(raw);
    let html = '<div class="handout-segments">';
    for (const part of parts) {
      const trimmed = part.trim();
      if (!trimmed) continue;
      const meta = _classifySegment(trimmed);
      const segLabel = meta.label || trimmed.split("\n")[0].replace(/^#+\s*/, "");
      html += `<div class="handout-seg seg-${meta.key}">`;
      html += `<div class="handout-seg-head"><span class="seg-icon">${meta.icon}</span> ${segLabel}</div>`;
      html += `<div class="handout-seg-body">${mdToHtml(trimmed)}</div>`;
      html += `</div>`;
    }
    html += '</div>';
    html += _renderPrinciples();
    return html;
  }

  function _renderPrinciples() {
    return `<div style="text-align:right">
      <span class="principles-toggle" role="button" tabindex="0" onclick="this.nextElementSibling.classList.toggle('open')">
        生成规则 (R2/R5/D0)
      </span>
      <div class="principles-body">
        <dl>
          <dt>R2 · 不拷教材</dt><dd>10-gram 不与教材原文重叠 — 用自己语言重述</dd>
          <dt>R5 · 词汇层约束</dt><dd>所有英语词 ⊆ 对应年级词表 (G1 ~1200 / G2 ~2200 / G3 ~3000 / G_FINAL ~3500)</dd>
          <dt>R1 · 关联 ≥3</dt><dd>每节核心知识点至少 3 个关联 (语义网络 / 词族 / 搭配)</dd>
          <dt>R4 · 作业对齐</dt><dd>作业 tag 100% ⊆ 本节知识点</dd>
          <dt>D0 · 准确率 100%</dt><dd>任何数据 + 关联准确率必须 100%, 18 章 audit 全绿</dd>
        </dl>
      </div>
    </div>`;
  }

  // 全局: 打开课节 modal — #8: 渲染本节真值 materials(/api/course/session)。
  // materials 按 reason 分 3 层(诚实分层, 非按 kind 平铺): yaml核心(教研设计选定) / 真题命中(homework_tags) / 图谱关联(R1邻接)。
  // 纯结构节点 stage/cefr_level 是图谱管道(每节都有, 零教学价值), 不渲成"本节内容"(死亡红线: 管道≠内容)。
  // 讲义范文生成层仍下线(2026-06-15 回滚, 依据不完整教材的范文不可信), 但 materials 本身是真值矿口, 40节课不再空壳。
  const _KIND_LABEL = { word: "词汇", grammar: "语法", exam_question: "真题", question: "关联题", unit: "教材单元", word_sense: "词义" };
  const _SKIP_KIND = { stage: 1, cefr_level: 1 };  // 纯图谱结构节点, 非教学内容
  const _matTier = (reason) => {
    if (reason === "yaml core_item") return "core";
    if (reason && reason.indexOf("homework_tags") >= 0) return "exam";
    return "rel";
  };
  const _renderMatItem = (m) => {
    const ref = m.ref_id || "";
    const bare = ref.replace(/^(word|grammar|exam_question|question|unit|word_sense):/, "");
    let label;
    if (m.kind === "word" && ref.startsWith("word:")) label = GZ.conceptLink(ref, bare);
    else if (m.kind === "grammar") label = `<span>${(m.textbook_position || bare).replace(/</g, "&lt;")}</span>`;  // 语法用人话标签(可数名词单复数…)非 ref 码
    else label = `<span style="font-family:var(--mono,monospace);font-size:12px;">${bare.replace(/</g, "&lt;")}</span>`;
    const pos = (m.kind !== "grammar" && m.textbook_position) ? ` <span class="muted" style="font-size:11px;">[${m.textbook_position}]</span>` : "";
    return `<span style="display:inline-block;margin:2px 8px 2px 0;">${label}${pos}</span>`;
  };
  const _renderTier = (mats, title, hint) => {
    const shown = mats.filter(m => !_SKIP_KIND[m.kind]);
    if (!shown.length) return "";
    const byKind = {};
    for (const m of shown) (byKind[m.kind] = byKind[m.kind] || []).push(m);
    const body = Object.keys(byKind).map(k =>
      `<div style="margin:4px 0;"><span class="muted" style="font-size:12px;">${_KIND_LABEL[k] || k} (${byKind[k].length})</span><div style="font-size:13px;line-height:1.9;">${byKind[k].map(_renderMatItem).join("")}</div></div>`
    ).join("");
    return `<div style="margin:8px 0;"><strong>${title}</strong>${hint ? ` <span class="muted" style="font-size:11px;">${hint}</span>` : ""}${body}</div>`;
  };
  window._openHandout = async (cid) => {
    const modal = $("#handout-modal");
    const md = $("#handout-md");
    modal.classList.add("open");
    _focusModal("handout-modal");
    md.innerHTML = '<p class="muted">载入本节内容…</p>';
    const d = await fetchJSON("/api/course/session?id=" + cid).catch(() => null);
    const mats = (d && d.materials) || [];
    const co = (d && d.course) || {};
    let html = `<h3 style="margin:0 0 2px;">${(co.title || "课节 #" + cid).replace(/</g, "&lt;")}</h3>`;
    const sub = [co.layer, co.block_kind, co.duration_min ? co.duration_min + "分钟" : "", co.listening_required ? "含听力" : ""].filter(Boolean).join(" · ");
    if (sub) html += `<div class="muted" style="font-size:12px;margin-bottom:8px;">${sub}</div>`;
    if (mats.length) {
      const tiers = { core: [], exam: [], rel: [] };
      for (const m of mats) tiers[_matTier(m.reason)].push(m);
      html += _renderTier(tiers.core, "本节核心", "教研设计选定 (课标·义教)");
      html += _renderTier(tiers.exam, "配套真题", "命中本节 homework 考点");
      html += _renderTier(tiers.rel, "图谱关联", "知识图谱 R1 邻接, 拓展参考非本节核心");
    } else {
      html += '<p class="muted">本节暂无 materials 数据</p>';
    }
    html += '<p class="muted" style="font-size:12px;border-top:1px solid var(--line-soft);padding-top:8px;margin-top:10px;line-height:1.6;">以上为本节真值 materials(词/语法/真题, 带教材位置+入选依据)。讲义范文生成层 2026-06-15 已下线(依据不完整教材的范文不可信), 待基石完善后重建。下方测验基于已核验真题。</p>';
    md.innerHTML = html + _renderQuizButton(cid);
  };

  function _renderQuizButton(cid) {
    return `<div style="text-align:center;margin:1.5rem 0">
      <button class="gz-quiz-btn" onclick="window._startQuiz(${cid})">课后测验</button>
    </div><div id="quiz-area"></div>`;
  }

  window._startQuiz = async (cid) => {
    const area = document.getElementById("quiz-area");
    if (!area) return;
    area.innerHTML = "<p>载入题目...</p>";
    try {
      const data = await fetchJSON("/api/course/quiz?id=" + cid);
      if (data.error) {
        area.innerHTML = `<p style="color:var(--accent)">课后测验加载失败: ${data.error}</p>`;
        return;
      }
      const questions = Array.isArray(data.questions) ? data.questions : [];
      if (questions.length === 0) {
        area.innerHTML = "<p style='color:var(--ink-3)'>本节暂无测验题</p>";
        return;
      }
      const totalCount = typeof data.count === "number" ? data.count : questions.length;
      let html = `<div class="gz-quiz"><h3>课后测验 · ${data.title || "未命名课程"} (${totalCount} 题)</h3>`;
      questions.forEach((q, i) => {
        html += `<div class="gz-quiz-q" data-qid="${q.qb_id}" data-answer="${(q.answer||'').trim()}">
          <p><strong>${i+1}.</strong> <span class="gz-quiz-type">${q.question_type}</span>
             <span class="gz-quiz-diff">${q.difficulty}</span></p>
          <div class="gz-quiz-stem">${(q.stem||'').replace(/\n/g,'<br>')}</div>`;
        const opts = _parseOptions(q.options_json, q.stem);
        if (opts.length) {
          html += `<ul class="gz-quiz-opts">`;
          opts.forEach(o => {
            html += `<li data-label="${o.label}" role="button" tabindex="0" onclick="window._selectOpt(this)">${o.label}. ${o.text}</li>`;
          });
          html += `</ul>`;
        } else {
          html += `<input type="text" class="gz-quiz-input" placeholder="输入答案" data-qid="${q.qb_id}">`;
        }
        html += `<div class="gz-quiz-feedback" style="display:none"></div></div>`;
      });
      html += `<div style="text-align:center;margin:1rem 0">
        <button class="gz-quiz-btn" onclick="window._submitQuiz()">提交批改</button>
      </div><div id="quiz-result"></div></div>`;
      area.innerHTML = html;
      area._quizData = Object.assign({}, data, { questions });
    } catch (err) {
      area.innerHTML = `<p style="color:var(--accent)">载入失败: ${err.message}</p>`;
    }
  };

  function _parseOptions(optJson, stem) {
    if (optJson) {
      try {
        const parsed = JSON.parse(optJson);
        if (Array.isArray(parsed)) return parsed;
        if (parsed && typeof parsed === "object") {
          return Object.entries(parsed).map(([label, text]) => ({ label: String(label), text: String(text || "").trim() })).filter(x => x.label && x.text);
        }
      } catch (_) {}
    }
    const m = (stem||'').match(/([A-D])\.\s*(.+?)(?=\s+[A-D]\.|$)/gs);
    if (!m) return [];
    return m.map(s => { const p = s.match(/([A-D])\.\s*(.*)/s); return p ? {label:p[1],text:p[2].trim()} : null; }).filter(Boolean);
  }

  window._selectOpt = (li) => {
    const q = li.closest(".gz-quiz-q");
    q.querySelectorAll(".gz-quiz-opts li").forEach(x => x.classList.remove("selected"));
    li.classList.add("selected");
  };

  window._submitQuiz = () => {
    const area = document.getElementById("quiz-area");
    if (!area || !area._quizData) return;
    let correct = 0, total = 0;
    area.querySelectorAll(".gz-quiz-q").forEach(qEl => {
      total++;
      const expected = (qEl.dataset.answer || "").toUpperCase();
      const selLi = qEl.querySelector(".gz-quiz-opts li.selected");
      const inputEl = qEl.querySelector(".gz-quiz-input");
      const given = selLi ? selLi.dataset.label.toUpperCase() : (inputEl ? inputEl.value.trim().toUpperCase() : "");
      const fb = qEl.querySelector(".gz-quiz-feedback");
      fb.style.display = "block";
      if (given === expected) {
        correct++;
        fb.innerHTML = `<span style="color:var(--good)">正确</span>`;
        fb.className = "gz-quiz-feedback correct";
      } else {
        fb.innerHTML = `<span style="color:var(--accent)">正确答案: ${expected}</span>`;
        fb.className = "gz-quiz-feedback wrong";
      }
      const qData = (area._quizData.questions||[]).find(q => q.qb_id === +qEl.dataset.qid);
      if (qData && qData.analysis) {
        fb.innerHTML += `<div class="gz-quiz-analysis">${qData.analysis}</div>`;
      }
    });
    const pct = total > 0 ? (correct / total * 100).toFixed(0) : 0;
    document.getElementById("quiz-result").innerHTML =
      `<div class="gz-quiz-result"><strong>得分: ${correct}/${total} (${pct}%)</strong></div>`;
  };

  // ===================================================================
  // C. 题库 + 组卷
  // ===================================================================
  register("qbank", async () => {
    // 题库浏览器: 按题型筛真题 (全 fetch /api/qb/* 单算点; 仅真题无押题)。
    CONTENT.innerHTML = `<h2>题库 + 组卷</h2><p class="muted">载入中...</p>`;
    const st = await fetchJSON("/api/qb/stats").catch(() => ({ by_type: {}, by_difficulty: {} }));
    const DIFF = { hard: ["难", "var(--accent-ink)"], mid: ["中", "var(--warn)"], easy: ["易", "var(--good)"] };
    const types = Object.entries(st.by_type || {});
    const totalN = st.total || types.reduce((a, [, n]) => a + n, 0);
    // #6: 默认 type_mix 用库内真实题型动态生成 (去掉 legacy 硬编码的库内不存在题型; 阅读多, 其余各2)
    const defMix = types.slice(0, 4).map(([k]) => `${k}:${k.includes("阅读") ? 4 : 2}`).join(",") || "阅读理解:4";
    let qtype = null;
    const d = st.by_difficulty || {};
    CONTENT.innerHTML = `
      <h2>题库 + 组卷 <span class="muted" style="font-size:14px;font-weight:400">${totalN} 题 · 仅已核验真题 (无押题)</span></h2>
      <p class="muted" style="margin:2px 0 10px;font-size:12.5px">按题型筛选浏览; 或一键生成蓝图练习卷(题面均历年真题, 结构对齐非预测)。难度 难 ${d.hard || 0} · 中 ${d.mid || 0} · 易 ${d.easy || 0}。</p>
      <div class="bk-filter" id="qb-blueprint" style="margin-bottom:10px;">
        <span class="bk-flabel">蓝图练习卷</span>
        <label style="font-size:12px;color:var(--ink-3);">题量 <input id="qb-bp-total" type="number" value="30" min="5" max="60" style="width:54px;padding:3px 6px;border:1px solid #d8d5cc;border-radius:6px;"></label>
        <button id="qb-bp-go" class="bk-pill on">${GZ.icon("grid")} 生成蓝图练习卷</button>
        <span class="muted" style="font-size:11px;">按考纲蓝图结构从真题加权抽样 · 非预测/非押题</span>
      </div>
      <details id="qb-compose" style="margin-bottom:10px;font-size:13px;"><summary style="cursor:pointer;color:var(--accent-ink);">${GZ.icon("gear")} 自定义组卷 (按题型/标签/难度/年份精确组卷, 收敛自 legacy)</summary>
        <div class="bk-filter" style="margin-top:8px;flex-wrap:wrap;">
          <label>题型分布 <input id="qb-c-mix" value="${defMix}" style="width:280px;padding:3px 6px;border:1px solid #d8d5cc;border-radius:6px;"></label>
          <label>必含标签 <input id="qb-c-req" placeholder="word:abandon,unit:waiyan/bixiu_1/U1" style="width:200px;padding:3px 6px;border:1px solid #d8d5cc;border-radius:6px;"></label>
          <label>难度 <select id="qb-c-diff" style="padding:3px;border:1px solid #d8d5cc;border-radius:6px;"><option value="">混合</option><option>easy</option><option>mid</option><option>hard</option></select></label>
          <label>年份 <input id="qb-c-year" placeholder="2021,2022,2023" style="width:120px;padding:3px 6px;border:1px solid #d8d5cc;border-radius:6px;"></label>
          <label>种子 <input id="qb-c-seed" type="number" value="42" style="width:60px;padding:3px 6px;border:1px solid #d8d5cc;border-radius:6px;"></label>
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
  // D. 数据管理
  // ===================================================================
  register("data", async () => {
    CONTENT.innerHTML = `<h2>D. 数据管理</h2><p>载入中...</p>`;
    const [stats, audit, cst] = await Promise.all([
      fetchJSON("/api/stats"),
      fetchJSON("/api/audit/findings").catch(() => null),
      fetchJSON("/api/constitution/list").catch(() => ({rules: [], by_type: {}})),
    ]);
    // RC1#4: /api/audit/findings 返回裸数组 → 原 audit.findings 恒 undefined → fail/warn 恒0 冒充"全部通过"(违D0红线)
    const auditErr = audit === null;
    const f = Array.isArray(audit) ? audit : ((audit && audit.findings) || []);
    const fail = f.filter(x => x.severity === "FAIL").length;
    const warn = f.filter(x => x.severity === "WARN").length;
    const rules = cst.rules || [];
    const principles = rules.filter(r => r.rule_type === "principle");
    const ironLaws = rules.filter(r => r.rule_type === "iron_law");
    const violations = rules.filter(r => r.rule_type === "violation");

    CONTENT.innerHTML = `
      <h2>D. 数据管理 + 设计宪法</h2>
      <div class="course-grid">
        <div class="course-card ${auditErr || fail > 0 ? 'G_FINAL' : warn > 0 ? 'G2' : 'G1'}">
          <strong>审计概览</strong>
          <div class="block">${auditErr ? '<span style="color:var(--accent-ink)">接口失败 · 无法确认 (非"全部通过")</span>' : `FAIL: ${fail} / WARN: ${warn}`}</div>
        </div>
        <div class="course-card">
          <strong>知识图谱</strong>
          <div class="block">${stats.nodes ?? "-"} nodes / ${stats.edges ?? "-"} edges</div>
        </div>
        <div class="course-card">
          <strong>教材 + 课标</strong>
          <div class="block">${stats.textbooks ?? "-"} 教材 / ${stats.cefr_vocab ?? "-"} 课标词</div>
        </div>
        <div class="course-card">
          <strong>题库 + 课程</strong>
          <div class="block">${stats.question_bank ?? "-"} 题 / ${stats.courses ?? "-"} 课 / ${stats.course_materials ?? "-"} 关联</div>
        </div>
      </div>

      <section class="layer-section" style="margin-top:1.5rem">
        <h3>设计宪法 <span class="layer-meta">${rules.length} 条 (${principles.length} 原则 + ${ironLaws.length} 铁律 + ${violations.length} 禁止)</span></h3>
        <p style="color:var(--ink-3);font-size:0.85em">模型驱动内容生成最高原则 — 任何题目/教案/教程必须遵守. 入库强制执行.</p>

        <h4 style="color:var(--down);margin-top:1rem">六大原则</h4>
        <div class="course-grid">${principles.map(r => `
          <div class="course-card" style="border-left-color:var(--down)">
            <strong>${r.rule_id}: ${r.title}</strong>
            <div class="block">${r.description}</div>
            ${r.enforcement ? `<div class="block" style="color:var(--good)">执行: ${r.enforcement}</div>` : ""}
          </div>`).join("")}
        </div>

        <h4 style="color:var(--accent);margin-top:1rem">正向铁律 (P1-P15)</h4>
        <div class="course-grid">${ironLaws.map(r => `
          <div class="course-card G_FINAL">
            <strong>${r.rule_id}: ${r.title}</strong>
            <div class="block">${r.description}</div>
          </div>`).join("")}
        </div>

        <h4 style="color:var(--ink-3);margin-top:1rem">违宪清单 (V1-V8)</h4>
        <ul style="background:var(--card);padding:0.5rem 2rem;border-radius:var(--r);font-size:0.9em">
          ${violations.map(r => `<li><strong style="color:var(--accent)">${r.rule_id}</strong> ${r.title} → <em>${r.description}</em></li>`).join("")}
        </ul>
      </section>`;
  });

  // ===================================================================
  // E. 学生档案 (#39 真接入)
  // ===================================================================
  register("students", async () => {
    CONTENT.innerHTML = `<h2>E. 学生档案</h2><p>载入中...</p>`;
    const [list, classes] = await Promise.all([
      stuFetch("/api/students/list").catch(() => ({ count: 0, students: [] })),
      stuFetch("/api/students/classes").catch(() => ({ count: 0, classes: [] })),
    ]);
    let html = `<h2>E. 学生档案 (${list.count} 学生 · ${classes.count} 班)</h2>

      <section class="layer-section">
        <h3>新学生入测 · 摸底测验</h3>
        <p style="color:var(--ink-3);font-size:0.9em">巧妙 9-11 题快速摸清水平 → 自动推送对应 layer 课节 + 弱点</p>
        <div style="display:flex;gap:0.5rem;margin:0.5rem 0">
          <button onclick="window._startPlacement('G1')" style="padding:0.4rem 1rem;background:var(--good);color:var(--card);border:0;border-radius:var(--r-sm);cursor:pointer">G1 入测 (9 题)</button>
          <button onclick="window._startPlacement('G2')" style="padding:0.4rem 1rem;background:var(--down);color:var(--card);border:0;border-radius:var(--r-sm);cursor:pointer">G2 入测 (10 题)</button>
          <button onclick="window._startPlacement('G3')" style="padding:0.4rem 1rem;background:var(--accent);color:var(--card);border:0;border-radius:var(--r-sm);cursor:pointer">G3 入测 (11 题)</button>
        </div>
      </section>

      <section class="layer-section">
        <h3>班级 <span class="layer-meta">${classes.count}</span></h3>
        <div class="course-grid">`;
    for (const c of classes.classes) {
      html += `<div class="course-card">
        <strong>${c.name}</strong>
        <div class="block">${c.school} · ${c.grade}</div>
        <div class="block">学生: ${c.n_students}</div>
      </div>`;
    }
    html += `${classes.classes.length ? "" : '<p class="muted" style="padding:6px 4px;">暂无班级 — 先建班并导入学生名单 (教研室单用户内网)</p>'}</div></section>
      <section class="layer-section">
        <h3>学生列表 <span class="layer-meta">点击查弱点 + 推送课节</span></h3>
        <div class="course-grid">`;
    for (const s of list.students) {
      html += `<div class="course-card" role="button" tabindex="0" onclick="window._openStudent('${s.student_id}')">
        <strong>${s.name}</strong> <span class="layer-badge">${s.grade}</span>
        <div class="block">学号: ${s.student_id}</div>
        <div class="block">${s.school} · ${s.city}</div>
      </div>`;
    }
    html += `${list.students.length ? "" : '<p class="muted" style="padding:6px 4px;">暂无学生 — 新学生先做上方“摸底入测”自动建档</p>'}</div></section>
      <div id="student-modal" role="dialog" aria-modal="true" aria-label="学生档案" onclick="if(event.target===this)this.classList.remove('open')">
        <div class="modal-body">
          <button class="gz-iconbtn close-btn" aria-label="关闭" onclick="document.getElementById('student-modal').classList.remove('open')">${GZ.icon("close")}</button>
          <div id="student-content">载入中...</div>
        </div>
      </div>`;
    CONTENT.innerHTML = html;
  });

  // 摸底测验流程 — D2 用户 2026-05-25
  window._startPlacement = async (grade) => {
    CONTENT.innerHTML = `<h2>${grade} 摸底测验</h2><p>载入题目 ...</p>`;
    try {
      const paper = await fetchJSON("/api/placement/generate?grade=" + grade);
      let html = `<h2>${grade} 摸底测验 (${paper.total_actual} 题)</h2>
        <p style="color:var(--ink-3)">答完点"提交"自动评分 + 推送对应课节. 不会的题留空.</p>
        <form id="placement-form" style="background:var(--card);padding:1rem;border-radius:4px;max-width:700px">`;
      let i = 0;
      for (const blk of paper.blocks) {
        html += `<h3 style="border-bottom:1px solid var(--line)">${blk.kind} (${blk.type}) — ${blk.n_actual} 题</h3>`;
        for (const q of blk.questions) {
          i++;
          html += `<div style="margin:0.7rem 0;padding:0.5rem;background:var(--sunken);border-left:3px solid var(--line)">
            <strong>${i}.</strong> <small style="color:var(--ink-3)">[#${q.qb_id}, ${q.difficulty}]</small>
            <div style="margin:0.3rem 0">${(q.stem || "").slice(0, 200)}</div>
            <input type="text" name="ans_${q.qb_id}" placeholder="答案 (eg A/B/C/D 或文本)" style="width:300px;padding:0.3rem">
          </div>`;
        }
      }
      html += `<button type="submit" style="background:var(--accent);color:var(--card);border:0;padding:0.6rem 1.5rem;border-radius:3px;cursor:pointer">提交评分</button>
        <button type="button" onclick="window.location.hash='#/students'" style="margin-left:0.5rem;padding:0.6rem 1rem">取消</button>
        </form>
        <div id="placement-result" style="margin-top:1rem"></div>`;
      CONTENT.innerHTML = html;

      document.getElementById("placement-form").onsubmit = async (ev) => {
        ev.preventDefault();
        const form = ev.target;
        const answers = {};
        for (const blk of paper.blocks) for (const q of blk.questions) {
          const v = form[`ans_${q.qb_id}`].value.trim();
          if (v) answers[q.qb_id] = v;
        }
        const resp = await fetch("/api/placement/score?grade=" + grade, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ answers }),
        });
        const result = await resp.json();
        const rd = document.getElementById("placement-result");
        const verdict = (result.layer_recommendation || {}).verdict;
        if (verdict === "consolidate" || verdict === "below") {
          await _runFollowup(rd, result, paper, grade);
        } else {
          _showFinalResult(rd, result);
        }
      };
    } catch (err) {
      CONTENT.innerHTML = `<h2>载入失败</h2><p style="color:var(--accent)">${err.message}</p>`;
    }
  };

  function _showFinalResult(rd, result) {
    rd.innerHTML = `<div style="background:var(--card);padding:1rem;border-left:4px solid var(--accent);border-radius:4px">
      <h3>评分结果</h3>
      <p><strong>正确率: ${((result.combined_accuracy || result.accuracy) * 100).toFixed(1)}%</strong>
        ${result.phase1_accuracy != null ? `(一阶段 ${(result.phase1_accuracy * 100).toFixed(1)}% + 二阶段 ${(result.phase2_accuracy * 100).toFixed(1)}%)` : `(${result.n_correct}/${result.n_total})`}</p>
      <p><strong>${result.layer_recommendation.msg}</strong></p>
      <h4>弱点 (${result.weak_concepts.length})</h4>
      <ul>${result.weak_concepts.slice(0, 8).map(w => `<li>${GZ.conceptLink(w.concept_id, w.label || w.concept_id.split(":").pop())}</li>`).join("")}</ul>
      <h4>推送课节 (${result.recommended_courses.length})</h4>
      <ul>${result.recommended_courses.map(c => `<li><a href="#" onclick="window._openHandout(${c.course_id});return false">#${c.course_id} [${c.layer}] ${c.title}</a> &larr; ${c.weak_concept}</li>`).join("")}</ul>
    </div>`;
  }

  async function _runFollowup(rd, firstResult, paper, grade) {
    const allQids = [];
    const wrongQids = [];
    const form = document.getElementById("placement-form");
    for (const blk of paper.blocks) for (const q of blk.questions) {
      allQids.push(q.qb_id);
      const studentAns = (form[`ans_${q.qb_id}`] ? form[`ans_${q.qb_id}`].value.trim().toUpperCase() : "");
      const correctAns = (q.answer || "").trim().toUpperCase();
      if (!studentAns || studentAns !== correctAns) wrongQids.push(q.qb_id);
    }
    rd.innerHTML = `<div style="background:var(--sunken);padding:1rem;border-left:4px solid var(--warn);border-radius:4px">
      <h3>一阶段结果: ${(firstResult.accuracy * 100).toFixed(1)}% — ${firstResult.layer_recommendation.msg}</h3>
      <p>正在加载追问题 (3-5 题深挖弱点) ...</p>
    </div>`;
    try {
      const fuResp = await fetch("/api/placement/followup", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ wrong_qids: wrongQids, all_qids: allQids, grade }),
      });
      const fuData = await fuResp.json();
      if (!fuData.questions || fuData.questions.length === 0) {
        _showFinalResult(rd, firstResult);
        return;
      }
      let html = `<div style="background:var(--sunken);padding:1rem;border-left:4px solid var(--warn);border-radius:4px;margin-bottom:1rem">
        <h3>一阶段: ${(firstResult.accuracy * 100).toFixed(1)}% — 需追问确认</h3>
        <p>针对弱点 ${fuData.weak_tags_targeted.slice(0,3).join(", ")} 追问 ${fuData.n_questions} 题</p>
      </div>
      <form id="followup-form" style="background:var(--card);padding:1rem;border-radius:4px;max-width:700px">`;
      fuData.questions.forEach((q, i) => {
        html += `<div style="margin:0.7rem 0;padding:0.5rem;background:var(--sunken);border-left:3px solid var(--warn)">
          <strong>追${i+1}.</strong> <small style="color:var(--ink-3)">[#${q.qb_id}, ${q.difficulty}]</small>
          <div style="margin:0.3rem 0">${(q.stem || "").slice(0, 200)}</div>
          <input type="text" name="fu_${q.qb_id}" placeholder="答案" style="width:300px;padding:0.3rem">
        </div>`;
      });
      html += `<button type="submit" style="background:var(--accent);color:var(--card);border:0;padding:0.6rem 1.5rem;border-radius:3px;cursor:pointer">提交追问</button>
        </form><div id="followup-result"></div>`;
      rd.innerHTML = html;
      document.getElementById("followup-form").onsubmit = async (ev2) => {
        ev2.preventDefault();
        const f2 = ev2.target;
        const fuAnswers = {};
        for (const q of fuData.questions) {
          const v = f2[`fu_${q.qb_id}`].value.trim();
          if (v) fuAnswers[q.qb_id] = v;
        }
        const finalResp = await fetch("/api/placement/final_score", {
          method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({ first_result: firstResult, followup_answers: fuAnswers, followup_questions: fuData.questions }),
        });
        const finalResult = await finalResp.json();
        _showFinalResult(document.getElementById("followup-result"), finalResult);
      };
    } catch (err) {
      rd.innerHTML += `<p style="color:var(--accent)">追问载入失败: ${err.message}</p>`;
      _showFinalResult(rd, firstResult);
    }
  }

  window._openStudent = async (sid) => {
    const modal = document.getElementById("student-modal");
    const cont = document.getElementById("student-content");
    modal.classList.add("open");
    _focusModal("student-modal");
    cont.innerHTML = "载入中...";
    try {
      const [info, weak, rec] = await Promise.all([
        stuFetch("/api/students/get?id=" + sid),
        stuFetch("/api/students/weakness?id=" + sid),
        stuFetch("/api/students/recommend?id=" + sid),
      ]);
      if (info.error) throw new Error(info.error);
      const weakRows = weak.error ? [] : (weak.weakness || []);
      const recRows = rec.error ? [] : (rec.recommendations || []);
      let h = `<h2 style="margin:0">${info.student.name} (${sid})</h2>`;
      // 坑4 诚实(A5): 全平台 student_answers 100% demo 合成(0真实作答), 单生模态须标 demo 不在零真作答上呈伪造置信度
      if (((info.student && info.student.source) || "demo") === "demo" || (info.answers && info.answers.source === "demo"))
        h += `<p style="background:#FAECE7;color:var(--accent-ink);padding:6px 10px;border-radius:6px;font-size:13px;margin:6px 0;">注 示例数据(demo 合成作答, 非真实学情) — 答题/弱点为演示用, 待导入真实答题卡后才是该生真实分析。</p>`;
      h += `<p>${info.student.school} · ${info.student.grade} · 答题 ${info.answers.total} 题 (正确 ${info.answers.correct})</p>`;
      h += `<h3>弱点 (${weakRows.length})</h3><ul>`;
      for (const w of weakRows) {
        h += `<li>[${w.kind}] <strong>${w.concept_id}</strong> — 弱化度 ${w.score} (样本 ${w.sample_n})</li>`;
      }
      h += `</ul><h3>推送课节 (${recRows.length})</h3><ul>`;
      for (const r of recRows) {
        h += `<li><a href="#" onclick="window._openHandout(${r.course_id});return false">#${r.course_id} [${r.layer}] ${r.title}</a> ← ${r.weak_concept}</li>`;
      }
      h += `</ul>`;
      if (weak.error) h += `<p style="color:#a66">弱点服务异常: ${weak.error}</p>`;
      if (rec.error) h += `<p style="color:#a66">推荐服务异常: ${rec.error}</p>`;
      cont.innerHTML = h;
    } catch (err) {
      cont.innerHTML = "载入失败: " + err.message;
    }
  };

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
      <h2 style="margin:0 0 2px">知识图谱 · 考点关联网络</h2>
      <p class="muted" style="margin:0 0 12px;font-size:13px">考点共现网络 = 同一道真题里共同出现的 <b>题材 / 主题 / 设问思维</b> · 边粗=同题共现次数(实测) · 题材/主题维度为<b>双模型推断标注</b>(非真值) · 共现=同题出现, <b>非因果</b> · <b>点任一考点</b>看其真题 · 拖拽/滚轮缩放</p>

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
        </section>
      </div>`;

    CONTENT.querySelectorAll(".gz-era").forEach(b => b.onclick = () => {
      CONTENT.querySelectorAll(".gz-era").forEach(x => x.classList.remove("on"));
      b.classList.add("on");
      _renderCooccur(b.dataset.era, b.dataset.label);
    });
    _renderCooccur("2021+_新高考II", "新高考II 2021+");
  });

  // ===================================================================
  // G. 扫描 OCR (占位 4.7.C)
  // ===================================================================
  register("scan", async () => {
    CONTENT.innerHTML = `<h2>G. 扫描 OCR</h2><p>载入中 ...</p>`;
    const [list, students] = await Promise.all([
      fetchJSON("/api/scan/list").catch(() => []),
      stuFetch("/api/students/list").catch(() => ({ students: [] })),
    ]);
    const rows = Array.isArray(list) ? list : (list.rows || []);
    const studentOpts = (students.students || [])
      .map(s => `<option value="${s.student_id}">${s.name} (${s.student_id})</option>`).join("");
    CONTENT.innerHTML = `
      <h2>G. 扫描 OCR · 学生卷面上传</h2>
      <p style="color:var(--ink-3)">PDF: 自动 pypdf 抽文字 / 图片: 留 PaddleOCR 后续.</p>

      <section class="layer-section">
        <h3>上传新扫描</h3>
        <form id="scan-form" style="background:var(--card);padding:1rem;border:1px solid var(--line);border-radius:var(--r);max-width:500px">
          <div style="margin:0.5rem 0">
            <label>学生 (可选):
              <select name="student_id" style="width:100%">
                <option value="">--- 未关联 ---</option>
                ${studentOpts}
              </select>
            </label>
          </div>
          <div style="margin:0.5rem 0">
            <label>类型:
              <select name="kind" style="width:100%">
                <option value="answer_sheet">答题卡</option>
                <option value="homework">作业</option>
                <option value="essay">作文</option>
              </select>
            </label>
          </div>
          <div style="margin:0.5rem 0">
            <label>文件 (PDF 优先):
              <input type="file" name="file" accept=".pdf,.jpg,.jpeg,.png" required>
            </label>
          </div>
          <button type="submit" style="background:var(--accent);color:var(--card);border:0;padding:0.5rem 1rem;border-radius:var(--r-sm);cursor:pointer">上传</button>
          <div id="scan-result" aria-live="polite" style="margin-top:0.7rem;color:var(--good)"></div>
        </form>
      </section>

      <section class="layer-section">
        <h3>已上传 (${rows.length})</h3>
        <table style="width:100%;background:var(--card);border-collapse:collapse">
          <thead><tr style="background:var(--ink);color:var(--surface)">
            <th style="padding:0.4rem;text-align:left">upload_id</th>
            <th style="padding:0.4rem">学生</th>
            <th style="padding:0.4rem">类型</th>
            <th style="padding:0.4rem">OCR 状态</th>
            <th style="padding:0.4rem">时间</th>
          </tr></thead>
          <tbody>
            ${rows.length ? rows.map(r => `<tr style="border-bottom:1px solid var(--line-soft)">
              <td style="padding:0.3rem"><code>${r.upload_id || r[0]}</code></td>
              <td style="padding:0.3rem">${r.student_id || r[1] || "-"}</td>
              <td style="padding:0.3rem">${r.upload_kind || r[3] || "-"}</td>
              <td style="padding:0.3rem"><span style="color:${(r.ocr_status||r[5])==='done'?'var(--good)':'var(--warn)'}">${r.ocr_status || r[5] || "-"}</span></td>
              <td style="padding:0.3rem"><small>${(r.uploaded_at || r[4] || "").slice(0,19).replace('T',' ')}</small></td>
            </tr>`).join("") : `<tr><td colspan="5" style="padding:1rem;color:var(--ink-3);text-align:center">无上传记录</td></tr>`}
          </tbody>
        </table>
      </section>`;

    document.getElementById("scan-form").onsubmit = async (ev) => {
      ev.preventDefault();
      const form = ev.target;
      const file = form.file.files[0];
      const resultDiv = document.getElementById("scan-result");
      if (!file) { resultDiv.innerHTML = `<span style="color:var(--accent)">请选文件</span>`; return; }
      resultDiv.textContent = "上传中 ...";
      const params = new URLSearchParams({
        student_id: form.student_id.value,
        kind:       form.kind.value,
        filename:   file.name,
      });
      try {
        const resp = await fetch("/api/scan/upload?" + params, {
          method: "POST",
          headers: { "Content-Type": "application/octet-stream" },
          body: file,
        });
        const data = await resp.json();
        if (resp.ok) {
          resultDiv.innerHTML = `上传成功 <code>${data.upload_id}</code>; sha=${data.sha256}; OCR 状态=${data.ocr_status} (${data.text_chars} 字符)`;
          setTimeout(() => route(), 1500);  // 刷新清单
        } else {
          resultDiv.innerHTML = `<span style="color:var(--accent)">${data.error || resp.statusText}</span>`;
        }
      } catch (err) {
        resultDiv.innerHTML = `<span style="color:var(--accent)">${err.message}</span>`;
      }
    };
  });
})();
