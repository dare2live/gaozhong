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

  // 出版社短名 → 色 (canonical 版本两类: 外研10市 / 人教4市)
  const VER_C = { waiyan: "#1D6FB8", renjiao: "#1D9E75" };

  function shell() {
    return `
<h2 style="margin:0 0 2px;">教材浏览 · STEP1 地基</h2>
<p class="muted" style="margin:0 0 12px;font-size:13px;">辽宁14地市只用2版本(外研10市 / 人教4市) · 78单元全册 · 教材PDF 真扫描原版(sha256锚定) · 跨版本同主题对照(宁缺毋滥) · service 单算点</p>
<div class="bk-card" style="margin-bottom:12px;">
  <div class="bk-h"><span>辽宁地市 → 教材版本</span><span class="bk-src">/api/recommend/city_curriculum</span></div>
  <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:6px 0;">
    <select id="tb-city" style="padding:6px 10px;border:1px solid #d8d6cd;border-radius:6px;font-size:14px;"></select>
    <span id="tb-city-info" class="muted" style="font-size:13px;"></span>
  </div>
</div>
<div id="tb-books"></div>`;
  }

  // 一个册卡: publisher + volume + pages + 开PDF + 单元列表(可展)
  function bookCard(bk, units) {
    const c = VER_C[bk.version_key] || "#888";
    const pdfUrl = `/api/textbooks/${bk.version_key}/${bk.volume_key}/pdf`;
    const uList = units.map(u => {
      const cid = `unit:${u.version_key}/${u.volume_key}/U${u.unit_number}`;
      const pg = (u.page_start != null) ? `${u.page_start}-${u.page_end}` : "—";
      return `<div class="tb-unit" style="display:flex;align-items:center;gap:8px;font-size:13px;padding:4px 6px;border-bottom:1px solid #f0eee6;">
        <span style="min-width:34px;color:#999;">U${u.unit_number}</span>
        <span style="flex:1;font-weight:500;">${(u.title_en || "").replace(/</g, "&lt;") || '<span class="muted">(无标题)</span>'}</span>
        <span class="muted" style="font-size:11px;">p.${pg}</span>
        <a href="${pdfUrl}#page=${u.page_start || 1}" target="_blank" rel="noopener" style="font-size:11px;color:#1D6FB8;">开PDF</a>
        <button class="tb-xver bk-export" data-unit="${cid}" style="font-size:11px;padding:1px 7px;">跨版本对照</button>
      </div><div class="tb-xver-slot" data-for="${cid}"></div>`;
    }).join("");
    return `<section class="bk-card" style="margin-bottom:10px;">
      <div class="bk-h">
        <span><span style="color:${c};">●</span> ${bk.publisher_label || bk.version_key} <small>${bk.volume_key}</small></span>
        <span class="bk-src">${bk.pdf_pages || "?"}页 · <a href="${pdfUrl}" target="_blank" rel="noopener" style="color:#1D6FB8;">开整册PDF</a></span>
      </div>
      <div>${uList || '<p class="muted" style="font-size:12px;padding:6px;">该册无单元数据</p>'}</div>
    </section>`;
  }

  async function showCrossVersion(cid, slot) {
    if (slot.dataset.open === "1") { slot.innerHTML = ""; slot.dataset.open = "0"; return; }
    slot.dataset.open = "1";
    slot.innerHTML = '<div class="muted" style="font-size:12px;padding:4px 40px;">查同主题对照…</div>';
    const res = await fetchJSON("/api/recommend/cross_version_units?unit=" + encodeURIComponent(cid)).catch(() => []);
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
    // 跨版本对照 委托(survive 重绘)
    G.$("#tb-books").addEventListener("click", (e) => {
      const btn = e.target.closest(".tb-xver");
      if (!btn) return;
      const cid = btn.getAttribute("data-unit");
      const slot = G.$(`.tb-xver-slot[data-for="${CSS.escape(cid)}"]`);
      if (slot) showCrossVersion(cid, slot);
    });
  }

  async function loadCity(city) {
    const info = G.$("#tb-city-info");
    const cc = await fetchJSON("/api/recommend/city_curriculum?city=" + encodeURIComponent(city)).catch(() => null);
    if (!cc || cc.error) { info.textContent = (cc && cc.error) || "查询失败"; return; }
    const c = VER_C[cc.version_key] || "#888";
    info.innerHTML = `<span style="color:${c};font-weight:600;">${cc.publisher}</span> · ${cc.units.length} 单元 · 累计已学词随册递增(末单元 ${cc.units.length ? cc.units[cc.units.length - 1].cumulative_words_learned : 0} 词)`;
  }

  registerTab("textbook", async () => {
    G.$("#content").innerHTML = shell();
    const [units, books, cityList] = await Promise.all([
      fetchJSON("/api/units").catch(() => []),
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
