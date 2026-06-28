/* 教材浏览 · STEP1 地基 (#13 教研室收口) — 14册77单元 + 城市→版本 + PDF + 跨版本同主题对照.
 *
 * 铁律1: 全 fetch /api/units + /api/textbooks + /api/recommend/* 的 service 单算点产物, 前端只渲染。
 * 诚实: 跨版本对照宁缺毋滥(标题核心词无交集=不推, 56/78单元无对照属正常诚实降级, 非bug);
 *       PDF = 真扫描原版(sha256 锚定); 城市→版本 = liaoning_city_textbook_choice 真值非估算。
 */
(function () {
  const G = window.GZ;
  if (!G || !G.registerTab) return;
  const { fetchJSON, registerTab } = G;

  // 出版社短名 → 身份色 (canonical 版本两类: 外研10市=红 / 人教4市=蓝; 均走令牌, 非裸 hex)
  const VER_C = { waiyan: "var(--accent-ink)", renjiao: "var(--down)" };

  function shell() {
    return `
<h2 style="margin:0 0 2px;">教材浏览 · STEP1 地基</h2>
<p class="muted" style="margin:0 0 12px;font-size:13px;">辽宁14地市只用2版本(外研10市 / 人教4市) · 78单元全册 · 教材已解析入库, 单元词表/课文直出 DB · 跨版本同主题对照(宁缺毋滥) · service 单算点</p>
<div class="bk-card" style="margin-bottom:12px;">
  <div class="bk-h"><span>辽宁地市 → 教材版本</span><span class="bk-src">/api/recommend/city_curriculum</span></div>
  <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:6px 0;">
    <select id="tb-city" aria-label="选择辽宁地市以查看对应教材版本" style="padding:6px 10px;border:1px solid var(--line);border-radius:6px;font-size:14px;"></select>
    <span id="tb-city-info" class="muted" aria-live="polite" style="font-size:13px;"></span>
  </div>
</div>
<div id="tb-books"></div>`;
  }

  // 一个册卡: publisher + volume + 单元数 + 单元列表(默认折叠); 单元内容直出 DB (词表/课文), 不链 PDF。
  function bookCard(bk, units) {
    const c = VER_C[bk.version_key] || "var(--ink-3)";
    const uList = units.map(u => {
      const cid = `unit:${u.version_key}/${u.volume_key}/U${u.unit_number}`;
      const dataAttr = `data-ver="${u.version_key}" data-vol="${u.volume_key}" data-unit="${u.unit_number}"`;
      return `<div class="tb-unit" style="display:flex;align-items:center;gap:8px;font-size:13px;padding:4px 6px;border-bottom:1px solid var(--line-soft);">
        <span style="min-width:34px;color:var(--ink-3);">U${u.unit_number}</span>
        <span style="flex:1;font-weight:500;">${(u.title_en || "").replace(/</g, "&lt;") || '<span class="muted">(无标题)</span>'}</span>
        <button class="tb-content bk-export" ${dataAttr} data-cid="${cid}" style="font-size:11px;padding:1px 7px;">查内容</button>
        <button class="tb-xver bk-export" data-unit="${cid}" style="font-size:11px;padding:1px 7px;">跨版本对照</button>
      </div><div class="tb-content-slot" data-for="${cid}"></div><div class="tb-xver-slot" data-for="${cid}"></div>`;
    }).join("");
    return `<section class="bk-card" style="margin-bottom:10px;">
      <details>
        <summary style="cursor:pointer;list-style:none;display:flex;align-items:baseline;justify-content:space-between;gap:10px;">
          <span style="font-weight:600;"><span style="color:${c};">●</span> ${bk.publisher_label || bk.version_key} <small style="color:var(--ink-3);font-weight:400;">${bk.volume_key} · ${units.length} 单元</small></span>
          <span class="bk-src">已解析入库 · 内容直出 DB</span>
        </summary>
        <div style="margin-top:8px;">${uList || '<p class="muted" style="font-size:12px;padding:6px;">该册无单元数据</p>'}</div>
      </details>
    </section>`;
  }

  // 单元内容直出 DB: 词表(unit_vocab_intro) + 课文段(sections), 不依赖 PDF (用户: 教材已入库直接排版)
  async function showUnitContent(btn, slot) {
    if (slot.dataset.open === "1") { slot.innerHTML = ""; slot.dataset.open = "0"; return; }
    slot.dataset.open = "1";
    slot.innerHTML = '<div class="muted" style="font-size:12px;padding:4px 40px;">载入单元内容…</div>';
    const q = `version=${encodeURIComponent(btn.dataset.ver)}&volume=${encodeURIComponent(btn.dataset.vol)}&unit=${btn.dataset.unit}`;
    const d = await G.fetchSafe("/api/unit/content?" + q);
    if (G.isErr(d)) { slot.innerHTML = '<div style="font-size:12px;padding:4px 40px;color:var(--warn);">内容加载失败 (接口错误)</div>'; return; }
    const esc = s => String(s == null ? "" : s).replace(/</g, "&lt;");
    const secs = (d.sections || []).map(s => {
      const tag = s.is_narrative ? "语篇" : (s.is_applied ? "应用文" : (s.is_listening ? "听力" : (s.kind || "段")));
      return `<span class="tb-sec">${esc(s.title || s.kind || "段")} <span class="muted">[${tag}]</span></span>`;
    }).join("");
    const vocab = (d.vocab || []).map(v =>
      `<span class="tb-word" title="${esc(v.zh_def)}">${esc(v.word)}${v.pos ? `<i>${esc(v.pos)}</i>` : ""}${v.in_curriculum ? "" : '<sup class="tb-extra" title="校本超纲(非课标)">超</sup>'}</span>`).join("");
    slot.innerHTML = `<div class="tb-content-body">
      <div class="tb-cg"><span class="tb-cg-h">课文段 (${d.sections_n})</span>${secs || '<span class="muted">无课文段</span>'}</div>
      <div class="tb-cg"><span class="tb-cg-h">引入词 (${d.vocab_n})</span><div class="tb-words">${vocab || '<span class="muted">无词表</span>'}</div></div>
      <p class="kb-dim" style="margin:4px 0 0;">${d.note || ""} (词带词性/中文释义 hover; "超"=校本超纲非课标)</p>
    </div>`;
  }

  async function showCrossVersion(cid, slot) {
    if (slot.dataset.open === "1") { slot.innerHTML = ""; slot.dataset.open = "0"; return; }
    slot.dataset.open = "1";
    slot.innerHTML = '<div class="muted" style="font-size:12px;padding:4px 40px;">查同主题对照…</div>';
    // RC1#19: 接口失败 ≠ "无对照"(宁缺毋滥是因果断言), 须区分, 不把 500 伪装成"正好没有"
    const res = await G.fetchSafe("/api/recommend/cross_version_units?unit=" + encodeURIComponent(cid));
    if (G.isErr(res)) { slot.innerHTML = '<div style="font-size:12px;padding:4px 40px;color:var(--warn);">对照查询失败 (接口错误, 非无对照)</div>'; return; }
    if (!res || !res.length) {
      slot.innerHTML = '<div class="muted" style="font-size:12px;padding:4px 40px;">无同主题对照单元（标题核心词无交集 = 宁缺毋滥不强推, 非全部单元都有跨版本同主题对应）</div>';
      return;
    }
    slot.innerHTML = `<div style="padding:4px 40px 8px;font-size:12px;">` +
      res.map(x => `<div style="margin:2px 0;">↔ <b>${(x.label || "").replace(/</g, "&lt;")}</b>
        <span class="muted">共享主题词 [${(x.shared_core_tokens || []).join(", ")}] · jaccard ${x.jaccard}</span></div>`).join("") +
      `<div class="muted" style="font-size:11px;margin-top:3px;">基于标题核心名词交集(去停用词+lemma归一)+共享level1主题, 100%准目标</div></div>`;
  }

  function renderBooks(books, unitsByVol) {
    G.$("#tb-books").innerHTML = books.map(bk =>
      bookCard(bk, unitsByVol[`${bk.version_key}/${bk.volume_key}`] || [])).join("");
    // 委托(survive 重绘): 查内容(DB) + 跨版本对照
    G.$("#tb-books").addEventListener("click", (e) => {
      const cbtn = e.target.closest(".tb-content");
      if (cbtn) {
        const slot = G.$(`.tb-content-slot[data-for="${CSS.escape(cbtn.dataset.cid)}"]`);
        if (slot) showUnitContent(cbtn, slot);
        return;
      }
      const btn = e.target.closest(".tb-xver");
      if (!btn) return;
      const cid = btn.getAttribute("data-unit");
      const slot = G.$(`.tb-xver-slot[data-for="${CSS.escape(cid)}"]`);
      if (slot) showCrossVersion(cid, slot);
    });
  }

  async function loadCity(city) {
    const info = G.$("#tb-city-info");
    const cc = await G.fetchSafe("/api/recommend/city_curriculum?city=" + encodeURIComponent(city));
    if (G.isErr(cc) || !cc || cc.error) { info.innerHTML = '<span style="color:var(--warn)">查询失败 (接口错误)</span>'; return; }
    const c = VER_C[cc.version_key] || "var(--ink-3)";
    info.innerHTML = `<span style="color:${c};font-weight:600;">${cc.publisher}</span> · ${cc.units.length} 单元 · 累计已学词随册递增(末单元 ${cc.units.length ? cc.units[cc.units.length - 1].cumulative_words_learned : 0} 词)`;
  }

  registerTab("textbook", async () => {
    G.$("#content").innerHTML = shell();
    const [units, books, cityList] = await Promise.all([
      fetchJSON("/api/units"),  // RC1/D0: 教材主数据, 失败必抛 → route() 错误态
      fetchJSON("/api/textbooks").catch(() => []),
      fetchJSON("/api/recommend/cities").catch(() => []),   // 14地市真值, 不前端hardcode
    ]);
    const unitsByVol = {};
    (units || []).forEach(u => {
      const k = `${u.version_key}/${u.volume_key}`;
      (unitsByVol[k] = unitsByVol[k] || []).push(u);
    });
    renderBooks(books || [], unitsByVol);
    // 城市选择器 — 从 /api/recommend/cities 真值(liaoning_city_textbook_choice), 默认首个
    const sel = G.$("#tb-city");
    const list = (cityList && cityList.length) ? cityList : [{ city: "沈阳" }];
    sel.innerHTML = list.map(c => `<option>${c.city}</option>`).join("");
    sel.onchange = () => loadCity(sel.value);
    await loadCity(list[0].city);
  });
})();
