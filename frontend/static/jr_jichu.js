/* 初中(沪教牛津hujiao)基础库 — 按单元浏览 (Phase E4后续, 2026-07-08).
 *
 * 铁律1: 全 fetch /api/units?version=hujiao + /api/course/junior/unit_content 的
 * service 单算点产物(course.junior_knowledge), 前端只渲染。
 * 复用高中 textbook.js 的视觉语言(.tb-* 系 class 已在 app.css 定义, 不发明新样式):
 * 单词/短语/语法/正文的渲染结构与高中"教材库"一致, 差异点(初中特有字段)见 _knowledgeHTML 注释。
 * 简化(与高中 textbook.js 的差异, 均标注理由):
 *   - 无城市选择器: 初中沪教版全省统一(非按市分版本, 调研已确认), 只需册选择器。
 *   - 无跨版本对照: 初中只有一个教材版本(hujiao), "跨版本"这个概念不存在。
 *   - 无 PDF sha256 溯源卡: 初中 textbooks 表未收录 hujiao 元数据行(与高中不同数据完整度),
 *     不为了"看起来一致"而展示缺失字段, 只展示册/单元真实存在的数据。
 */
(function () {
  const G = window.GZ;
  if (!G || !G.registerTab) return;
  const { fetchJSON, fetchSafe, isErr, registerTab, pageHead } = G;
  const _esc = s => String(s == null ? "" : s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

  const VOL_LABEL = { "7a": "七年级上", "7b": "七年级下", "8a": "八年级上", "8b": "八年级下", "9a": "九年级上", "9b": "九年级下" };
  const VOL_ORDER = ["7a", "7b", "8a", "8b", "9a", "9b"];

  function shell() {
    return `
${pageHead("初中 · 基础库", "课本里有什么", "沪教牛津版(辽宁义务教育统一版本) 6册46单元 — 每单元的单词 / 短语 / 语法 / 课文直接看。")}
<div class="bk-card" style="margin-bottom:12px;">
  <div class="bk-h"><span>选择册</span><span class="bk-src">/api/units?version=hujiao</span></div>
  <div id="jrjc-vols" style="display:flex;gap:8px;flex-wrap:wrap;margin:6px 0;"></div>
</div>
<div id="jrjc-units"></div>`;
  }

  function _kgroup(title, n, inner) { return n ? `<div class="tb-kg"><span class="tb-kg-h">${title} <b>${n}</b></span>${inner}</div>` : ""; }

  // 知识点渲染 — 与高中 textbook.js _knowledgeHTML 同结构, 字段名按初中真实API调整:
  //   词: stage(学段归属, 高中必修/选修=超纲) 取代高中的 gaokao_hit_ln(辽宁高考命中);
  //       zhongkao_exposure_count(中考真题曝光次数)标注在角标(有则显示, 无则不显示, 0不是"未验证");
  //   语法: senior_exam_status(该语法点在高中侧的考查状态) + zhongkao_verified_questions(中考验证题号列表)
  //       取代高中的 category_pct(课标类目考查占比) — 初中无同构占比统计, 不硬凑(坑30);
  //   短语: recurs_in_senior_textbook(是否在高中教材复现) 取代高中的"出现非考查"caveat徽章。
  function _knowledgeHTML(k, scopeNote) {
    const STAGE_TAG = { "高中必修": "超", "高中选修": "超", "校本超纲": "超" };
    const words = (k.vocab || []).map(v => {
      const isOver = !!STAGE_TAG[v.stage];
      const zk = v.zhongkao_exposure_count || 0;
      const badge = zk > 0 ? `<sup class="tb-hit" title="中考真题曝光 ${zk} 次(真值, 点词查看)">${zk}</sup>` : "";
      const content = `${_esc(v.word)}${v.pos ? `<i>${_esc(v.pos)}</i>` : ""}${badge}${isOver ? `<sup class="tb-extra" title="${_esc(v.stage)}(超出初中课标)">超</sup>` : ""}`;
      return `<a class="gz-concept tb-word${zk > 0 ? " tb-word-tested" : ""}" data-concept="word:${_esc(v.word)}" title="${_esc(v.zh_def)}${v.stage ? " · 学段: " + _esc(v.stage) : ""}">${content}</a>`;
    }).join("");
    const chips = arr => (arr || []).map(x => `<span class="tb-chip">${_esc(x)}</span>`).join("");
    const gram = (k.grammar || []).map(g => {
      const zk = g.zhongkao_verified_questions || [];
      const badge = zk.length
        ? `<span class="tb-gram-pct" title="中考真题验证: ${zk.map(_esc).join(', ')}">中考验证 ${zk.length} 题</span>`
        : `<span class="tb-gram-pct tb-gram-pct-none" title="该语法点暂无中考真题验证边(诚实标, 非未教)">暂无中考验证</span>`;
      const senior = g.senior_exam_status
        ? `<span class="tb-chip" title="该语法点在高中阶段的考查定位(deepens衔接)">高中: ${_esc(g.senior_exam_status)}</span>` : "";
      const label = g.grammar_item_id ? G.conceptLink("grammar:jr:" + g.grammar_item_id, g.label || "?") : `<span class="tb-gram-l">${_esc(g.label || "?")}</span>`;
      return `<div class="tb-gram-row"><span class="tb-gram-l">${label}</span>${badge}${senior}</div>`;
    }).join("");
    const phrases = (k.phrases || []).map(p =>
      `<span class="tb-chip" title="${p.recurs_in_senior_textbook ? '高中教材复现' : '仅初中阶段'}">${_esc(p.canonical)}${p.recurs_in_senior_textbook ? '<i>→高中复现</i>' : ''}</span>`).join("");
    const parts = [
      _kgroup("单词", (k.vocab || []).length, `<div class="tb-words">${words}</div><p class="tb-legend">右上角数字 = 该词中考真题曝光次数(真值); "超"= 超出初中课标学段</p>`),
      _kgroup("语法", (k.grammar || []).length, `<div>${gram}</div>`),
      _kgroup("短语/句型/表达", (k.phrases || []).length, `<div class="tb-chips">${phrases}</div>`),
    ].filter(Boolean).join("");
    return (parts || '<span class="muted" style="font-size:12px;">本单元暂无结构化知识点</span>')
      + (scopeNote ? `<p class="tb-phrase-note">${_esc(scopeNote)}</p>` : "");
  }

  // 正文渲染 — 与高中 textbook.js _reflowPassage 同逻辑(PDF硬换行合并成段落流, N7)
  function _reflowPassage(text, title) {
    const lines = String(text || "").split("\n").map(l => l.trim());
    const paras = []; let cur = [];
    const flush = () => { if (cur.length) { paras.push(cur.join(" ")); cur = []; } };
    lines.forEach((l, i) => {
      if (!l) { flush(); return; }
      if (i === 0 && title && l.toLowerCase() === String(title).trim().toLowerCase()) return;
      if (/^\d+\s/.test(l)) flush();
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

  async function showUnitContent(btn, slot) {
    if (slot.dataset.open === "1") { slot.innerHTML = ""; slot.dataset.open = "0"; return; }
    slot.dataset.open = "1";
    slot.innerHTML = '<div class="muted" style="font-size:12px;padding:4px 40px;">载入单元内容…</div>';
    const q = `volume=${encodeURIComponent(btn.dataset.vol)}&unit=${btn.dataset.unit}`;
    const d = await fetchSafe("/api/course/junior/unit_content?" + q);
    if (isErr(d) || d.error) { slot.innerHTML = '<div style="font-size:12px;padding:4px 40px;color:var(--warn);">内容加载失败 (接口错误)</div>'; return; }
    slot.innerHTML = `<div class="tb-content-body">
      <div class="tb-half"><div class="tb-half-h">知识点 (上)</div>${_knowledgeHTML(d.knowledge || {}, d.scope_note)}</div>
      <div class="tb-half"><div class="tb-half-h">教材正文 (下) · ${d.passages_n} 段</div>${_passagesHTML(d.passages)}</div>
      <p class="kb-dim" style="margin:6px 0 0;">${_esc(d.note || "")}</p>
    </div>`;
  }

  function unitRow(u) {
    const dataAttr = `data-vol="${u.volume_key}" data-unit="${u.unit_number}"`;
    const cid = `jrunit:${u.volume_key}/U${u.unit_number}`;
    return `<div class="tb-unit" style="display:flex;align-items:center;gap:8px;font-size:13px;padding:4px 6px;border-bottom:1px solid var(--line-soft);">
      <span style="min-width:34px;color:var(--ink-3);">U${u.unit_number}</span>
      <span style="flex:1;font-weight:500;">${_esc(u.title_en) || '<span class="muted">(无标题)</span>'}</span>
      <button class="tb-content bk-export" ${dataAttr} data-cid="${cid}" style="font-size:11px;padding:1px 7px;">查内容</button>
    </div><div class="tb-content-slot" data-for="${cid}"></div>`;
  }

  function volCard(vol, units) {
    return `<section class="bk-card" style="margin-bottom:10px;">
      <details${vol === "7a" ? " open" : ""}>
        <summary style="cursor:pointer;list-style:none;display:flex;align-items:baseline;justify-content:space-between;gap:10px;">
          <span style="font-weight:600;"><span style="color:var(--accent-ink);">●</span> ${VOL_LABEL[vol] || vol} <small style="color:var(--ink-3);font-weight:400;">${units.length} 单元</small></span>
          <span class="bk-src">已解析入库 · 内容直出 DB</span>
        </summary>
        <div style="margin-top:8px;">${units.map(unitRow).join("") || '<p class="muted" style="font-size:12px;padding:6px;">该册无单元数据</p>'}</div>
      </details>
    </section>`;
  }

  let _unitsByVol = {};
  function renderVol(vol) {
    const shown = vol === "all" ? VOL_ORDER : [vol];
    G.$("#jrjc-units").innerHTML = shown
      .filter(v => _unitsByVol[v] && _unitsByVol[v].length)
      .map(v => volCard(v, _unitsByVol[v])).join("");
  }

  function wireUnits() {
    G.$("#jrjc-units").addEventListener("click", (e) => {
      const btn = e.target.closest(".tb-content");
      if (!btn) return;
      const slot = G.$(`.tb-content-slot[data-for="${CSS.escape(btn.dataset.cid)}"]`);
      if (slot) showUnitContent(btn, slot);
    });
  }

  registerTab("jr_jichu", async () => {
    G.$("#content").innerHTML = shell();
    const units = await fetchJSON("/api/units?version=hujiao");  // D0: 教材主数据, 失败必抛
    _unitsByVol = {};
    (units || []).forEach(u => (_unitsByVol[u.volume_key] = _unitsByVol[u.volume_key] || []).push(u));
    const presentVols = VOL_ORDER.filter(v => _unitsByVol[v] && _unitsByVol[v].length);
    G.$("#jrjc-vols").innerHTML = presentVols.map((v, i) =>
      `<button type="button" class="jrjc-vbtn${i === 0 ? " active" : ""}" data-vol="${v}" style="padding:5px 12px;border:1px solid var(--line);border-radius:6px;font-size:13px;background:${i === 0 ? "var(--accent-wash)" : "var(--card)"};cursor:pointer;">${VOL_LABEL[v] || v}</button>`
    ).join("");
    G.$("#jrjc-vols").addEventListener("click", (e) => {
      const b = e.target.closest(".jrjc-vbtn");
      if (!b) return;
      G.$$(".jrjc-vbtn").forEach(x => x.style.background = "var(--card)");
      b.style.background = "var(--accent-wash)";
      renderVol(b.dataset.vol);
    });
    wireUnits();
    renderVol(presentVols[0] || "7a");
  });
})();
