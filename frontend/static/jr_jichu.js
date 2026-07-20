/* 初中(沪教牛津)基础库 — 册→单元选择器 + 段类型子标签 (2026-07-17 UI 重排).
 *
 * 铁律1: fetch /api/units?version=hujiao + /api/course/junior/unit_content, 前端只渲染.
 * 交互: 不再「全册平铺 + details 折叠」; 单册内选单元, 单元内按段类型(阅读/理解练习/…)切页.
 * 排版: 练习题(a/b/c/d、题号)按行结构渲染, 禁止把选项并进同一段落.
 */
(function () {
  const G = window.GZ;
  if (!G || !G.registerTab) return;
  const { fetchJSON, fetchSafe, isErr, registerTab, pageHead, loadingHTML } = G;
  const _esc = s => String(s == null ? "" : s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

  const VOL_LABEL = { "7a": "七年级上", "7b": "七年级下", "8a": "八年级上", "8b": "八年级下", "9a": "九年级上", "9b": "九年级下" };
  const VOL_ORDER = ["7a", "7b", "8a", "8b", "9a", "9b"];
  const KIND_LABEL = {
    Reading: "阅读", Vocabulary: "词汇", Comprehension: "理解练习", Listening: "听力",
    Grammar: "语法", Speaking: "口语", Writing: "写作", MorePractice: "更多练习",
    StudySkills: "学习技巧", CultureCorner: "文化角",
  };
  const KIND_ORDER = ["Reading", "Vocabulary", "Comprehension", "Listening", "Grammar",
    "Speaking", "Writing", "MorePractice", "StudySkills", "CultureCorner"];

  const state = { vol: null, unit: null, tab: "knowledge", cache: {}, unitsByVol: {} };

  function shell() {
    return `${pageHead("初中 · 基础库", "课本里有什么",
      "沪教牛津版(辽宁义务教育统一) · 先选册与单元, 再按「知识点 / 阅读 / 理解练习…」分段看 — 练习选项与正文分行显示。")}
<section class="bk-card jrjc-nav">
  <div class="bk-h"><span>册</span><span class="bk-src">/api/units?version=hujiao</span></div>
  <div id="jrjc-vols" class="jrjc-chips" role="tablist" aria-label="选择册"></div>
  <div class="jrjc-unitrow">
    <label class="jrjc-ulab" for="jrjc-unit-sel">单元</label>
    <select id="jrjc-unit-sel" class="jrjc-usel" aria-label="选择单元"></select>
    <div id="jrjc-unit-chips" class="jrjc-uchips" aria-label="单元快捷"></div>
  </div>
</section>
<div id="jrjc-workspace" class="jrjc-workspace"><p class="kb-dim">选择册与单元后显示内容。</p></div>`;
  }

  function _kgroup(title, n, inner) {
    return n ? `<div class="tb-kg"><span class="tb-kg-h">${title} <b>${n}</b></span>${inner}</div>` : "";
  }

  function _knowledgeHTML(k, scopeNote) {
    const STAGE_TAG = { "高中必修": "超", "高中选修": "超", "校本超纲": "超" };
    const words = (k.vocab || []).map(v => {
      const isOver = !!STAGE_TAG[v.stage];
      const zk = v.zhongkao_exposure_count || 0;
      const badge = zk > 0 ? `<sup class="tb-hit" title="中考真题曝光 ${zk} 次">${zk}</sup>` : "";
      const content = `${_esc(v.word)}${v.pos ? `<i>${_esc(v.pos)}</i>` : ""}${badge}${isOver ? `<sup class="tb-extra" title="${_esc(v.stage)}">超</sup>` : ""}`;
      return `<a class="gz-concept tb-word${zk > 0 ? " tb-word-tested" : ""}" data-concept="word:${_esc(v.word)}" title="${_esc(v.zh_def)}${v.stage ? " · " + _esc(v.stage) : ""}">${content}</a>`;
    }).join("");
    const gram = (k.grammar || []).map(g => {
      const zk = g.zhongkao_verified_questions || [];
      const badge = zk.length
        ? `<span class="tb-gram-pct" title="中考真题验证: ${zk.map(_esc).join(", ")}">中考验证 ${zk.length} 题</span>`
        : `<span class="tb-gram-pct tb-gram-pct-none">暂无中考验证</span>`;
      const senior = g.senior_exam_status
        ? `<span class="tb-chip" title="高中考查定位">高中: ${_esc(g.senior_exam_status)}</span>` : "";
      const label = g.grammar_item_id
        ? G.conceptLink("grammar:jr:" + g.grammar_item_id, g.label || "?")
        : `<span class="tb-gram-l">${_esc(g.label || "?")}</span>`;
      return `<div class="tb-gram-row"><span class="tb-gram-l">${label}</span>${badge}${senior}</div>`;
    }).join("");
    const phrases = (k.phrases || []).map(p =>
      `<span class="tb-chip" title="${p.recurs_in_senior_textbook ? "高中教材复现" : "仅初中"}">${_esc(p.canonical)}${p.recurs_in_senior_textbook ? "<i>→高中复现</i>" : ""}</span>`
    ).join("");
    const parts = [
      _kgroup("单词", (k.vocab || []).length, `<div class="tb-words">${words}</div><p class="tb-legend">角标数字 = 中考曝光次数; 「超」= 超出初中课标学段</p>`),
      _kgroup("语法", (k.grammar || []).length, `<div>${gram}</div>`),
      _kgroup("短语/句型/表达", (k.phrases || []).length, `<div class="tb-chips">${phrases}</div>`),
    ].filter(Boolean).join("");
    return (parts || '<p class="kb-dim">本单元暂无结构化知识点</p>')
      + (scopeNote ? `<p class="tb-phrase-note">${_esc(scopeNote)}</p>` : "");
  }

  // 正文/练习排版 → GZ.formatPassageText (common.js, 与高中 textbook 共用)

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
      body = `<div class="jr-panel">${_knowledgeHTML(d.knowledge || {}, d.scope_note)}</div>`;
    } else if (state.tab === "all") {
      body = `<div class="jr-panel gz-stack-sm">${passages.map(_passageCard).join("") || '<p class="kb-dim">本单元正文未入库</p>'}</div>`;
    } else {
      const subset = passages.filter(p => p.kind === state.tab);
      body = `<div class="jr-panel gz-stack-sm">${subset.map(_passageCard).join("") || '<p class="kb-dim">该类型本单元无段</p>'}</div>`;
    }
    return `${_tabsHTML(passages)}${body}
      <p class="kb-dim jrjc-foot">${_esc(d.note || "")} · 共 ${d.passages_n || passages.length} 段</p>`;
  }

  function renderVolChips(present) {
    G.$("#jrjc-vols").innerHTML = present.map(v =>
      `<button type="button" class="jrjc-chip${v === state.vol ? " is-on" : ""}" data-vol="${v}" role="tab" aria-selected="${v === state.vol}">${VOL_LABEL[v] || v}</button>`
    ).join("");
  }

  function renderUnitControls() {
    const units = state.unitsByVol[state.vol] || [];
    const sel = G.$("#jrjc-unit-sel");
    sel.innerHTML = units.map(u =>
      `<option value="${u.unit_number}"${Number(u.unit_number) === Number(state.unit) ? " selected" : ""}>U${u.unit_number} · ${_esc(u.title_en || "（无标题）")}</option>`
    ).join("");
    G.$("#jrjc-unit-chips").innerHTML = units.map(u =>
      `<button type="button" class="jrjc-uchip${Number(u.unit_number) === Number(state.unit) ? " is-on" : ""}" data-unit="${u.unit_number}">U${u.unit_number}</button>`
    ).join("");
  }

  async function loadUnit() {
    const box = G.$("#jrjc-workspace");
    if (!state.vol || !state.unit) {
      box.innerHTML = '<p class="kb-dim">请选择单元。</p>';
      return;
    }
    const key = `${state.vol}:${state.unit}`;
    box.innerHTML = (loadingHTML && loadingHTML(`载入 ${VOL_LABEL[state.vol]} U${state.unit}…`))
      || '<div class="loading-state"><span class="ls-dot"></span>载入…</div>';
    if (!state.cache[key]) {
      const d = await fetchSafe(`/api/course/junior/unit_content?volume=${encodeURIComponent(state.vol)}&unit=${state.unit}`);
      if (isErr(d) || d.error) {
        box.innerHTML = '<div class="error-state"><div class="es-title">内容加载失败</div><div class="es-msg">接口错误</div></div>';
        return;
      }
      state.cache[key] = d;
    }
    // default tab: knowledge; if switching unit keep tab if still valid
    const d = state.cache[key];
    const kinds = new Set((d.passages || []).map(p => p.kind));
    if (state.tab !== "knowledge" && state.tab !== "all" && !kinds.has(state.tab)) {
      state.tab = "knowledge";
    }
    const u = (state.unitsByVol[state.vol] || []).find(x => Number(x.unit_number) === Number(state.unit));
    box.innerHTML = `<section class="bk-card jrjc-main">
      <div class="jrjc-main-h">
        <div>
          <div class="sc-badge">${_esc(VOL_LABEL[state.vol] || state.vol)}</div>
          <h2 class="jrjc-utitle">U${state.unit} · ${_esc((u && u.title_en) || "")}</h2>
        </div>
      </div>
      ${_panelHTML(d)}
    </section>`;
    box.querySelectorAll(".jrjc-tab").forEach(btn => {
      btn.addEventListener("click", () => {
        state.tab = btn.dataset.tab;
        loadUnit();
      });
    });
  }

  function selectVol(vol) {
    state.vol = vol;
    const units = state.unitsByVol[vol] || [];
    state.unit = units.length ? units[0].unit_number : null;
    state.tab = "knowledge";
    renderVolChips(VOL_ORDER.filter(v => state.unitsByVol[v] && state.unitsByVol[v].length));
    renderUnitControls();
    loadUnit();
  }

  function selectUnit(n) {
    state.unit = Number(n);
    state.tab = "knowledge";
    renderUnitControls();
    loadUnit();
  }

  registerTab("jr_jichu", async () => {
    G.$("#content").innerHTML = `<section class="scaffold gz-stack">${shell()}</section>`;
    const units = await fetchJSON("/api/units?version=hujiao");
    state.unitsByVol = {};
    state.cache = {};
    (units || []).forEach(u => (state.unitsByVol[u.volume_key] = state.unitsByVol[u.volume_key] || []).push(u));
    Object.keys(state.unitsByVol).forEach(v =>
      state.unitsByVol[v].sort((a, b) => a.unit_number - b.unit_number)
    );
    const present = VOL_ORDER.filter(v => state.unitsByVol[v] && state.unitsByVol[v].length);

    G.$("#jrjc-vols").addEventListener("click", e => {
      const b = e.target.closest("[data-vol]");
      if (b) selectVol(b.dataset.vol);
    });
    G.$("#jrjc-unit-sel").addEventListener("change", e => selectUnit(e.target.value));
    G.$("#jrjc-unit-chips").addEventListener("click", e => {
      const b = e.target.closest("[data-unit]");
      if (b) selectUnit(b.dataset.unit);
    });

    if (present.length) selectVol(present.includes("8a") ? "8a" : present[0]);
  });
})();
