/* 教材浏览 · STEP1 地基 (#13 教研室收口) — 外研/人教 + 册 + 单元选择器 + 段类型子标签.
 *
 * 铁律1: 全 fetch /api/units + /api/textbooks + /api/recommend/* 的 service 单算点产物, 前端只渲染。
 * 交互: 对齐初中 jr_jichu — 不再「全册平铺 + details/查内容」; 版本→册→单元, 单元内按 kind 切页.
 * 排版: GZ.formatPassageText (common.js 与 jr_jichu 共用) — 练习选项分行, 散文 reflow.
 * 诚实: 跨版本对照宁缺毋滥(标题核心词无交集=不推); 城市→版本 = liaoning_city_textbook_choice 真值。
 */
(function () {
  const G = window.GZ;
  if (!G || !G.registerTab) return;
  const { fetchJSON, fetchSafe, isErr, registerTab, pageHead, loadingHTML } = G;
  const _esc = s => String(s == null ? "" : s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

  const VER_META = {
    waiyan: { label: "外研社", short: "外研", color: "var(--accent-ink)" },
    renjiao: { label: "人教版", short: "人教", color: "var(--down)" },
  };
  const VER_ORDER = ["waiyan", "renjiao"];
  const VOL_ORDER = ["bixiu_1", "bixiu_2", "bixiu_3", "xuanze_1", "xuanze_2", "xuanze_3", "xuanze_4"];
  const VOL_LABEL = {
    bixiu_1: "必修1", bixiu_2: "必修2", bixiu_3: "必修3",
    xuanze_1: "选修1", xuanze_2: "选修2", xuanze_3: "选修3", xuanze_4: "选修4",
  };
  const KIND_LABEL = {
    Intro: "导入", Reading: "阅读", Listening: "听力", Vocabulary: "词汇",
    Grammar: "语法", Speaking: "口语", Writing: "写作", Project: "项目",
    Review: "复习", Assessment: "测评", Comprehension: "理解练习",
  };
  const KIND_ORDER = ["Intro", "Reading", "Listening", "Vocabulary", "Grammar",
    "Speaking", "Writing", "Project", "Review", "Assessment", "Comprehension"];

  const state = {
    city: null, ver: null, vol: null, unit: null, tab: "knowledge",
    cache: {}, unitsByKey: {}, books: [], cityList: [],
  };

  function shell() {
    return `${pageHead("基础库 · 教材库", "课本里有什么",
      "外研社 (辽宁 10 市) + 人教 (4 市) — 先选版本与册、再选单元, 按「知识点 / 阅读 / 语法…」分段看; 练习选项与正文分行。")}
<section class="bk-card jrjc-nav">
  <div class="bk-h"><span>地市 → 版本</span><span class="bk-src">/api/recommend/city_curriculum</span></div>
  <div class="tb-cityrow">
    <label class="jrjc-ulab" for="tb-city">地市</label>
    <select id="tb-city" class="jrjc-usel tb-citysel" aria-label="选择辽宁地市以查看对应教材版本"></select>
    <span id="tb-city-info" class="kb-dim" aria-live="polite"></span>
  </div>
  <div class="bk-h" style="margin-top:12px;"><span>版本 · 册</span><span class="bk-src">/api/textbooks · /api/units</span></div>
  <div id="tb-vers" class="jrjc-chips" role="tablist" aria-label="选择版本"></div>
  <div id="tb-vols" class="jrjc-chips" role="tablist" aria-label="选择册" style="margin-top:8px;"></div>
  <div class="jrjc-unitrow">
    <label class="jrjc-ulab" for="tb-unit-sel">单元</label>
    <select id="tb-unit-sel" class="jrjc-usel" aria-label="选择单元"></select>
    <div id="tb-unit-chips" class="jrjc-uchips" aria-label="单元快捷"></div>
  </div>
</section>
<div id="tb-workspace" class="jrjc-workspace"><p class="kb-dim">选择版本、册与单元后显示内容。</p></div>
<div id="tb-xver" class="tb-xver-panel" hidden></div>`;
  }

  function _kgroup(title, n, inner) {
    return n ? `<div class="tb-kg"><span class="tb-kg-h">${title} <b>${n}</b></span>${inner}</div>` : "";
  }

  function _knowledgeHTML(k) {
    const words = (k.vocab || []).map(v => {
      const hit = v.gaokao_hit_ln || 0;
      const badge = hit > 0 ? `<sup class="tb-hit" title="辽宁高考命中 ${hit} 次(真题真值, 点词查看)">${hit}</sup>` : "";
      const content = `${_esc(v.word)}${v.pos ? `<i>${_esc(v.pos)}</i>` : ""}${badge}${v.in_curriculum ? "" : '<sup class="tb-extra" title="校本超纲(非课标)">超</sup>'}`;
      return `<a class="gz-concept tb-word${hit > 0 ? " tb-word-tested" : ""}" data-concept="word:${_esc(v.word)}" title="${_esc(v.zh_def)}">${content}</a>`;
    }).join("");
    const chips = arr => (arr || []).map(x => `<span class="tb-chip">${_esc(x)}</span>`).join("");
    const exprs = (k.expression || []).map(e =>
      `<span class="tb-chip">${_esc(e.text)}${e.intent ? `<i>${_esc(e.intent)}</i>` : ""}</span>`).join("");
    const gram = (k.grammar || []).map(g => {
      const pct = g.category_pct, isHist = !!g.category_pct_era;
      const badge = pct != null
        ? `<span class="tb-gram-pct${isHist ? " tb-gram-pct-hist" : ""}" title="「${_esc(g.category)}」类辽宁卷考查占比${isHist ? "(" + _esc(g.category_pct_era) + ")" : "(真值)"}">${_esc(g.category)} · 辽宁 ${pct}%${isHist ? " (历史)" : ""}</span>`
        : `<span class="tb-gram-pct tb-gram-pct-none" title="该类目辽宁卷(含历史卷制)暂无考查真题边(诚实标, 非0)">暂无考查数据</span>`;
      const label = g.grammar_item_id
        ? G.conceptLink("grammar:" + g.grammar_item_id, g.label || "?")
        : `<span class="tb-gram-l">${_esc(g.label || "?")}</span>`;
      return `<div class="tb-gram-row"><span class="tb-gram-l">${label}</span>${badge}${g.example ? `<span class="tb-gram-ex">e.g. ${_esc(g.example)}</span>` : ""}</div>`;
    }).join("");
    const phraseNote = k.phrase_note ? `<p class="tb-phrase-note">${_esc(k.phrase_note)}</p>` : "";
    const hasPhrases = (k.collocation || []).length || (k.sentence_pattern || []).length || (k.expression || []).length;
    const parts = [
      _kgroup("单词", k.vocab_n, `<div class="tb-words">${words}</div><p class="tb-legend">右上角数字 = 该词辽宁高考命中次数(真题真值)</p>`),
      _kgroup("固定搭配", (k.collocation || []).length, `<div class="tb-chips">${chips(k.collocation)}</div>`),
      _kgroup("句型", (k.sentence_pattern || []).length, `<div class="tb-chips">${chips(k.sentence_pattern)}</div>`),
      _kgroup("语法", (k.grammar || []).length, `<div>${gram}</div>`),
      _kgroup("表达方式", (k.expression || []).length, `<div class="tb-chips">${exprs}</div>`),
    ].filter(Boolean).join("") + (hasPhrases ? phraseNote : "");
    return parts || '<p class="kb-dim">本单元暂无结构化知识点</p>';
  }

  function _kindTag(p) {
    if (p.is_narrative) return "语篇";
    if (p.is_applied) return "应用文";
    if (p.is_listening) return "听力";
    return KIND_LABEL[p.kind] || p.kind || "段";
  }

  function _passageCard(p) {
    const label = KIND_LABEL[p.kind] || p.kind || "段";
    return `<article class="jr-passage">
      <header class="jr-passage-h">
        <h3>${_esc(p.title || label)}</h3>
        <span class="tb-passage-tag">${_esc(_kindTag(p))}</span>
      </header>
      <div class="jr-passage-body">${G.formatPassageText(p.text, p.title)}</div>
    </article>`;
  }

  function _tabsHTML(passages) {
    const kinds = [];
    const seen = new Set();
    KIND_ORDER.forEach(k => {
      if (passages.some(p => p.kind === k) && !seen.has(k)) { seen.add(k); kinds.push(k); }
    });
    passages.forEach(p => {
      if (p.kind && !seen.has(p.kind)) { seen.add(p.kind); kinds.push(p.kind); }
    });
    const chips = [
      `<button type="button" class="jrjc-tab${state.tab === "knowledge" ? " is-on" : ""}" data-tab="knowledge">知识点</button>`,
      ...kinds.map(k =>
        `<button type="button" class="jrjc-tab${state.tab === k ? " is-on" : ""}" data-tab="${_esc(k)}">${_esc(KIND_LABEL[k] || k)}</button>`
      ),
      `<button type="button" class="jrjc-tab${state.tab === "all" ? " is-on" : ""}" data-tab="all">全部课文</button>`,
    ];
    return `<div class="jrjc-tabs" role="tablist">${chips.join("")}</div>`;
  }

  function _panelHTML(d) {
    const passages = d.passages || [];
    let body = "";
    if (state.tab === "knowledge") {
      body = `<div class="jr-panel">${_knowledgeHTML(d.knowledge || {})}</div>`;
    } else if (state.tab === "all") {
      body = `<div class="jr-panel gz-stack-sm">${passages.map(_passageCard).join("") || '<p class="kb-dim">本单元正文未入库</p>'}</div>`;
    } else {
      const subset = passages.filter(p => p.kind === state.tab);
      body = `<div class="jr-panel gz-stack-sm">${subset.map(_passageCard).join("") || '<p class="kb-dim">该类型本单元无段</p>'}</div>`;
    }
    return `${_tabsHTML(passages)}${body}
      <p class="kb-dim jrjc-foot">${_esc(d.note || "")} · 共 ${d.passages_n || passages.length} 段</p>`;
  }

  function unitsFor(ver, vol) {
    return state.unitsByKey[`${ver}/${vol}`] || [];
  }

  function volKeysFor(ver) {
    return VOL_ORDER.filter(v => unitsFor(ver, v).length);
  }

  function renderVerChips() {
    G.$("#tb-vers").innerHTML = VER_ORDER.map(v => {
      const m = VER_META[v];
      const n = volKeysFor(v).reduce((s, vol) => s + unitsFor(v, vol).length, 0);
      if (!n) return "";
      return `<button type="button" class="jrjc-chip${v === state.ver ? " is-on" : ""}" data-ver="${v}" role="tab" aria-selected="${v === state.ver}" style="${v === state.ver ? `border-color:${m.color};color:${m.color}` : ""}">${m.short} <span class="kb-dim">${n}单元</span></button>`;
    }).join("");
  }

  function renderVolChips() {
    const vols = volKeysFor(state.ver);
    G.$("#tb-vols").innerHTML = vols.map(v =>
      `<button type="button" class="jrjc-chip${v === state.vol ? " is-on" : ""}" data-vol="${v}" role="tab" aria-selected="${v === state.vol}">${VOL_LABEL[v] || v}</button>`
    ).join("") || '<span class="kb-dim">该版本暂无册数据</span>';
  }

  function renderUnitControls() {
    const units = unitsFor(state.ver, state.vol);
    const sel = G.$("#tb-unit-sel");
    sel.innerHTML = units.length
      ? units.map(u =>
        `<option value="${u.unit_number}"${Number(u.unit_number) === Number(state.unit) ? " selected" : ""}>U${u.unit_number} · ${_esc(u.title_en || "（无标题）")}</option>`
      ).join("")
      : '<option value="">（无单元）</option>';
    G.$("#tb-unit-chips").innerHTML = units.map(u =>
      `<button type="button" class="jrjc-uchip${Number(u.unit_number) === Number(state.unit) ? " is-on" : ""}" data-unit="${u.unit_number}">U${u.unit_number}</button>`
    ).join("");
  }

  function unitCid() {
    return `unit:${state.ver}/${state.vol}/U${state.unit}`;
  }

  async function loadUnit() {
    const box = G.$("#tb-workspace");
    const xver = G.$("#tb-xver");
    if (xver) { xver.hidden = true; xver.innerHTML = ""; }
    if (!state.ver || !state.vol || state.unit == null || state.unit === "") {
      box.innerHTML = '<p class="kb-dim">请选择单元。</p>';
      return;
    }
    const key = `${state.ver}/${state.vol}:${state.unit}`;
    const volLab = VOL_LABEL[state.vol] || state.vol;
    const verLab = (VER_META[state.ver] || {}).short || state.ver;
    box.innerHTML = (loadingHTML && loadingHTML(`载入 ${verLab} ${volLab} U${state.unit}…`))
      || '<div class="loading-state"><span class="ls-dot"></span>载入…</div>';
    if (!state.cache[key]) {
      const q = `version=${encodeURIComponent(state.ver)}&volume=${encodeURIComponent(state.vol)}&unit=${state.unit}`;
      const d = await fetchSafe("/api/unit/content?" + q);
      if (isErr(d) || d.error) {
        box.innerHTML = '<div class="error-state"><div class="es-title">内容加载失败</div><div class="es-msg">接口错误</div></div>';
        return;
      }
      state.cache[key] = d;
    }
    const d = state.cache[key];
    const kinds = new Set((d.passages || []).map(p => p.kind));
    if (state.tab !== "knowledge" && state.tab !== "all" && !kinds.has(state.tab)) {
      state.tab = "knowledge";
    }
    const u = unitsFor(state.ver, state.vol).find(x => Number(x.unit_number) === Number(state.unit));
    const cid = unitCid();
    box.innerHTML = `<section class="bk-card jrjc-main">
      <div class="jrjc-main-h tb-main-h">
        <div>
          <div class="sc-badge">${_esc(verLab)} · ${_esc(volLab)}</div>
          <h2 class="jrjc-utitle">U${state.unit} · ${_esc((u && u.title_en) || "")}</h2>
        </div>
        <button type="button" class="bk-export tb-xver-btn" data-unit="${_esc(cid)}">跨版本对照</button>
      </div>
      ${_panelHTML(d)}
    </section>`;
    box.querySelectorAll(".jrjc-tab").forEach(btn => {
      btn.addEventListener("click", () => {
        state.tab = btn.dataset.tab;
        loadUnit();
      });
    });
    const xbtn = box.querySelector(".tb-xver-btn");
    if (xbtn) xbtn.addEventListener("click", () => showCrossVersion(xbtn.dataset.unit));
  }

  async function showCrossVersion(cid) {
    const panel = G.$("#tb-xver");
    if (!panel) return;
    if (panel.dataset.open === "1" && panel.dataset.cid === cid) {
      panel.hidden = true; panel.innerHTML = ""; panel.dataset.open = "0";
      return;
    }
    panel.hidden = false;
    panel.dataset.open = "1";
    panel.dataset.cid = cid;
    panel.innerHTML = '<div class="bk-card"><p class="kb-dim">查同主题对照…</p></div>';
    // RC1#19: 接口失败 ≠ "无对照"(宁缺毋滥是因果断言), 须区分, 不把 500 伪装成"正好没有"
    const res = await fetchSafe("/api/recommend/cross_version_units?unit=" + encodeURIComponent(cid));
    if (isErr(res)) {
      panel.innerHTML = '<div class="bk-card"><div class="error-state"><div class="es-title">对照查询失败</div><div class="es-msg">接口错误, 非无对照</div></div></div>';
      return;
    }
    if (!res || !res.length) {
      panel.innerHTML = `<div class="bk-card"><p class="kb-dim">无同主题对照单元（标题核心词无交集 = 宁缺毋滥不强推, 非全部单元都有跨版本同主题对应）</p></div>`;
      return;
    }
    panel.innerHTML = `<div class="bk-card">
      <div class="bk-h"><span>跨版本同主题对照</span><span class="bk-src">/api/recommend/cross_version_units</span></div>
      ${res.map(x => `<div class="tb-xver-row">↔ <b>${_esc(x.label || "")}</b>
        <span class="kb-dim">共享主题词 [${(x.shared_core_tokens || []).map(_esc).join(", ")}] · jaccard ${x.jaccard}</span></div>`).join("")}
      <p class="kb-dim" style="margin-top:8px;">基于标题核心名词交集(去停用词+lemma归一)+共享level1主题, 100%准目标</p>
    </div>`;
  }

  function selectVer(ver) {
    state.ver = ver;
    const vols = volKeysFor(ver);
    state.vol = vols.includes(state.vol) ? state.vol : (vols[0] || null);
    const units = unitsFor(state.ver, state.vol);
    state.unit = units.length ? units[0].unit_number : null;
    state.tab = "knowledge";
    renderVerChips();
    renderVolChips();
    renderUnitControls();
    loadUnit();
  }

  function selectVol(vol) {
    state.vol = vol;
    const units = unitsFor(state.ver, state.vol);
    state.unit = units.length ? units[0].unit_number : null;
    state.tab = "knowledge";
    renderVolChips();
    renderUnitControls();
    loadUnit();
  }

  function selectUnit(n) {
    state.unit = Number(n);
    state.tab = "knowledge";
    renderUnitControls();
    loadUnit();
  }

  async function loadCity(city) {
    state.city = city;
    const info = G.$("#tb-city-info");
    const cc = await fetchSafe("/api/recommend/city_curriculum?city=" + encodeURIComponent(city));
    if (isErr(cc) || !cc || cc.error) {
      info.innerHTML = '<span style="color:var(--warn)">查询失败 (接口错误)</span>';
      return;
    }
    const m = VER_META[cc.version_key] || {};
    info.innerHTML = `<span style="color:${m.color || "var(--ink-3)"};font-weight:600;">${_esc(cc.publisher)}</span> · ${cc.units.length} 单元 · 累计已学词随册递增(末单元 ${cc.units.length ? cc.units[cc.units.length - 1].cumulative_words_learned : 0} 词)`;
    selectVer(cc.version_key || "waiyan");
  }

  registerTab("textbook", async () => {
    G.$("#content").innerHTML = `<section class="scaffold gz-stack">${shell()}</section>`;
    const [units, books, cityList] = await Promise.all([
      fetchJSON("/api/units"),  // RC1/D0: 教材主数据, 失败必抛 → route() 错误态
      fetchJSON("/api/textbooks").catch(() => []),
      fetchJSON("/api/recommend/cities").catch(() => []),
    ]);
    state.unitsByKey = {};
    state.cache = {};
    (units || []).forEach(u => {
      if (u.version_key !== "waiyan" && u.version_key !== "renjiao") return;  // 高中页不混入初中沪教
      const k = `${u.version_key}/${u.volume_key}`;
      (state.unitsByKey[k] = state.unitsByKey[k] || []).push(u);
    });
    Object.keys(state.unitsByKey).forEach(k =>
      state.unitsByKey[k].sort((a, b) => a.unit_number - b.unit_number)
    );
    state.books = books || [];
    state.cityList = cityList || [];

    G.$("#tb-vers").addEventListener("click", e => {
      const b = e.target.closest("[data-ver]");
      if (b) selectVer(b.dataset.ver);
    });
    G.$("#tb-vols").addEventListener("click", e => {
      const b = e.target.closest("[data-vol]");
      if (b) selectVol(b.dataset.vol);
    });
    G.$("#tb-unit-sel").addEventListener("change", e => selectUnit(e.target.value));
    G.$("#tb-unit-chips").addEventListener("click", e => {
      const b = e.target.closest("[data-unit]");
      if (b) selectUnit(b.dataset.unit);
    });

    const sel = G.$("#tb-city");
    const list = (state.cityList.length) ? state.cityList : [{ city: "沈阳" }];
    const def = list.some(c => c.city === "沈阳") ? "沈阳" : list[0].city;
    sel.innerHTML = list.map(c => `<option${c.city === def ? " selected" : ""}>${_esc(c.city)}</option>`).join("");
    sel.onchange = () => loadCity(sel.value);
    await loadCity(def);
  });
})();
