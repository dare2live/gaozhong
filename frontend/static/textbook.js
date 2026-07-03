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
${G.pageHead("基础库 · 教材库", "课本里有什么", "外研社 (辽宁 10 市) + 人教 (4 市) 全册 — 每单元的单词 / 短语 / 语法 / 课文直接看, 不用翻 PDF。")}
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

  const _esc = s => String(s == null ? "" : s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  // 知识点小节 (有则渲, 无则跳)
  function _kgroup(title, n, inner) { return n ? `<div class="tb-kg"><span class="tb-kg-h">${title} <b>${n}</b></span>${inner}</div>` : ""; }
  function _knowledgeHTML(k) {
    const words = (k.vocab || []).map(v =>
      `<span class="tb-word" title="${_esc(v.zh_def)}">${_esc(v.word)}${v.pos ? `<i>${_esc(v.pos)}</i>` : ""}${v.in_curriculum ? "" : '<sup class="tb-extra" title="校本超纲(非课标)">超</sup>'}</span>`).join("");
    const chips = arr => (arr || []).map(x => `<span class="tb-chip">${_esc(x)}</span>`).join("");
    const exprs = (k.expression || []).map(e => `<span class="tb-chip">${_esc(e.text)}${e.intent ? `<i>${_esc(e.intent)}</i>` : ""}</span>`).join("");
    const gram = (k.grammar || []).map(g =>
      `<div class="tb-gram-row"><span class="tb-gram-l">${_esc(g.label || "?")}</span>${g.example ? `<span class="tb-gram-ex">e.g. ${_esc(g.example)}</span>` : ""}</div>`).join("");
    const parts = [
      _kgroup("单词", k.vocab_n, `<div class="tb-words">${words}</div>`),
      _kgroup("固定搭配", (k.collocation || []).length, `<div class="tb-chips">${chips(k.collocation)}</div>`),
      _kgroup("句型", (k.sentence_pattern || []).length, `<div class="tb-chips">${chips(k.sentence_pattern)}</div>`),
      _kgroup("语法", (k.grammar || []).length, `<div>${gram}</div>`),
      _kgroup("表达方式", (k.expression || []).length, `<div class="tb-chips">${exprs}</div>`),
    ].filter(Boolean).join("");
    return parts || '<span class="muted" style="font-size:12px;">本单元暂无结构化知识点</span>';
  }
  // PDF 提取文本的硬换行是排版工件非语义 (N7): 渲染层合并成段落流, 数据 raw_text 原样不动。
  // 段界 = 空行 或 行首编号 (教材段号/活动指令号); 首行与标题重复则跳过。
  function _reflowPassage(text, title) {
    const lines = String(text || "").split("\n").map(l => l.trim());
    const paras = [];
    let cur = [];
    const flush = () => { if (cur.length) { paras.push(cur.join(" ")); cur = []; } };
    lines.forEach((l, i) => {
      if (!l) { flush(); return; }
      if (i === 0 && title && l.toLowerCase() === String(title).trim().toLowerCase()) return;  // 标题行已在卡头
      if (/^\d+\s/.test(l)) flush();          // 行首编号 = 新段 (课文段号/活动指令号)
      cur.push(l);
    });
    flush();
    return paras.map(t => `<p>${_esc(t)}</p>`).join("");
  }
  function _passagesHTML(passages) {
    if (!passages || !passages.length) return '<span class="muted" style="font-size:12px;">本单元正文未入库</span>';
    return passages.map(p => {
      const tag = p.is_narrative ? "语篇" : (p.is_applied ? "应用文" : (p.is_listening ? "听力" : (p.kind || "段")));
      return `<div class="tb-passage"><div class="tb-passage-h">${_esc(p.title || p.kind || "段")} <span class="tb-passage-tag">${tag}</span></div><div class="tb-passage-t">${_reflowPassage(p.text, p.title)}</div></div>`;
    }).join("");
  }
  // 单元内容直出 DB: 上半知识点(词/短语/句型/语法/表达) + 下半教材正文 (用户: 直接显示内容)
  async function showUnitContent(btn, slot) {
    if (slot.dataset.open === "1") { slot.innerHTML = ""; slot.dataset.open = "0"; return; }
    slot.dataset.open = "1";
    slot.innerHTML = '<div class="muted" style="font-size:12px;padding:4px 40px;">载入单元内容…</div>';
    const q = `version=${encodeURIComponent(btn.dataset.ver)}&volume=${encodeURIComponent(btn.dataset.vol)}&unit=${btn.dataset.unit}`;
    const d = await G.fetchSafe("/api/unit/content?" + q);
    if (G.isErr(d) || d.error) { slot.innerHTML = '<div style="font-size:12px;padding:4px 40px;color:var(--warn);">内容加载失败 (接口错误)</div>'; return; }
    slot.innerHTML = `<div class="tb-content-body">
      <div class="tb-half"><div class="tb-half-h">知识点 (上)</div>${_knowledgeHTML(d.knowledge || {})}</div>
      <div class="tb-half"><div class="tb-half-h">教材正文 (下) · ${d.passages_n} 段</div>${_passagesHTML(d.passages)}</div>
      <p class="kb-dim" style="margin:6px 0 0;">${d.note || ""}</p>
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

  let _books = [], _unitsByVol = {};
  // 按版本渲染册卡 (verKey 指定版本=只显该版本; 默认按所选地市版本, 沈阳=外研)
  function renderBooksForVersion(verKey) {
    const shown = verKey ? _books.filter(b => b.version_key === verKey) : _books;
    G.$("#tb-books").innerHTML = shown.map(bk =>
      bookCard(bk, _unitsByVol[`${bk.version_key}/${bk.volume_key}`] || [])).join("")
      || '<p class="muted" style="font-size:12px;padding:8px;">该版本暂无册数据</p>';
  }
  // 点击委托一次性绑 (#tb-books 容器, survive innerHTML 重绘): 查内容(DB) + 跨版本对照
  function wireBooks() {
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
    renderBooksForVersion(cc.version_key);  // 只显该地市版本的册 (沈阳→外研); 切城市自动换版本
  }

  registerTab("textbook", async () => {
    G.$("#content").innerHTML = shell();
    const [units, books, cityList] = await Promise.all([
      fetchJSON("/api/units"),  // RC1/D0: 教材主数据, 失败必抛 → route() 错误态
      fetchJSON("/api/textbooks").catch(() => []),
      fetchJSON("/api/recommend/cities").catch(() => []),   // 14地市真值, 不前端hardcode
    ]);
    _unitsByVol = {};
    (units || []).forEach(u => {
      const k = `${u.version_key}/${u.volume_key}`;
      (_unitsByVol[k] = _unitsByVol[k] || []).push(u);
    });
    _books = books || [];
    wireBooks();  // 一次性绑委托; 册卡由 loadCity 按版本渲染
    // 城市选择器 — 从 /api/recommend/cities 真值(liaoning_city_textbook_choice); 默认沈阳 (用户)
    const sel = G.$("#tb-city");
    const list = (cityList && cityList.length) ? cityList : [{ city: "沈阳" }];
    const def = list.some(c => c.city === "沈阳") ? "沈阳" : list[0].city;
    sel.innerHTML = list.map(c => `<option${c.city === def ? " selected" : ""}>${c.city}</option>`).join("");
    sel.onchange = () => loadCity(sel.value);
    await loadCity(def);  // 默认沈阳 → 外研版册
  });
})();
