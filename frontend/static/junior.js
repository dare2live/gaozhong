/* 初中(中考)命题研判 + 真题特点 (Phase F, 2026-07-08 用户拍板"中考自成体系, 颗粒度对标高考,
 * 不复刻设问思维, 样本不够不做趋势只做分布"). 复用 /api/zhongkao/* 已有产物, 前端只渲染(铁律1)。
 *
 * jr_beike (命题研判) = 结论先行, 3行结论(genre/语法K12衔接/高频词), 样式复用 beike.js 的 bk-verdict 系。
 * jr_zhenti (真题特点) = 题型分布 + genre/theme分布 + 语法考查重点 + 高频实词 + 语篇填空逐空考点。
 */
(function () {
  const G = window.GZ;
  if (!G || !G.registerTab) return;
  const { fetchJSON, registerTab, pageHead } = G;
  let chType = null, chGenre = null, chTheme = null;

  function _splitKaodian(txt) {
    const m = /^([^一-龥]+?)\s*([一-龥].*)$/.exec(txt || "");
    return m ? { ans: m[1].trim(), cat: m[2].trim() } : { ans: "", cat: txt || "" };
  }

  // ── jr_beike: 结论先行 (复用 beike.js 的 bk-verdict 系样式, 3维度非高考6维, 不含cognitive_skill) ──
  function renderJrVerdict(dist, focus) {
    const el = G.$("#jrbk-verdict"); if (!el) return;
    const items = [];
    const genres = (focus.genre_分布 || []).slice().sort((a, b) => b.n - a.n);
    if (genres.length) {
      const top = genres[0];
      const total = genres.reduce((s, g) => s + g.n, 0);
      items.push({
        text: `题材以 <strong>${top.label}</strong> 为主 (${top.n}/${total} 题, 11篇双独立视角一致文章) → 精读练习优先选此体裁`,
        link: `<a class="bk-vlink" href="#/jr_zhenti">看证据 ↗ 真题特点</a>`,
        weak: total < 30,
      });
    }
    const byType = (dist.by_question_type || []).slice().sort((a, b) => b.n - a.n);
    if (byType.length) {
      const top = byType[0];
      items.push({ text: `题型以 <strong>${top.type}</strong> 分值占比最高 (${top.n}/90 题, 2024+2025 省统一) → 优先保题型分`,
        link: `<a class="bk-vlink" href="#/jr_zhenti">看证据 ↗ 真题特点</a>` });
    }
    items.push({
      text: `语篇填空10个语法考点 = 高考语法填空考点<strong>全集</strong>(N=2省统一卷实证) → 初中学牢这10点即打通高考语法填空`,
      link: `<a class="bk-vlink" href="#/k12">看证据 ↗ K12衔接</a>`,
    });
    if (!items.length) { el.style.display = "none"; return; }
    el.innerHTML = `<div class="bk-verdict-h">研判结论 · 沈阳/辽宁中考英语</div>`
      + `<ul class="bk-verdict-list">` + items.map(i => `<li${i.weak ? ' class="bk-verdict-weak"' : ""}>${i.text} ${i.link}</li>`).join("") + `</ul>`
      + `<p class="bk-verdict-foot">题材由双独立视角AI一致标注才入库(方向性参考, 非官方真值); 仅2024/2025两年数据, 只做静态分布, 不做逐年趋势结论。</p>`;
  }

  registerTab("jr_beike", async () => {
    G.$("#content").innerHTML = pageHead("初中 · 沈阳中考", "命题研判", "结论先行 — 中考实际考什么、怎么考, 数据全部取自真实90题(2024+2025省统一卷)")
      + `<div id="jrbk-verdict" class="bk-verdict" aria-live="polite"></div>
      <div class="bk-grid">
        <section class="bk-card"><div class="bk-h"><span>命题结构一览</span><span class="bk-src">/api/zhongkao/distribution</span></div>
          <p class="muted" style="font-size:12px;">完整题型分布/题材分布/语法考查/高频词 → <a class="bk-vlink" href="#/jr_zhenti">真题特点页</a></p></section>
        <section class="bk-card"><div class="bk-h"><span>K12 语法衔接</span><span class="bk-src">/api/k12/blueprint</span></div>
          <p class="muted" style="font-size:12px;">初中71个语法点 → 高中同名深化, 逐一衔接边 → <a class="bk-vlink" href="#/k12">K12衔接页</a></p></section>
      </div>`;
    const [dist, focus] = await Promise.all([
      fetchJSON("/api/zhongkao/distribution").catch(() => ({ by_question_type: [] })),
      fetchJSON("/api/zhongkao/exam_focus").catch(() => ({ genre_分布: [] })),
    ]);
    renderJrVerdict(dist, focus);
  });

  // ── jr_zhenti: 真题特点 (题型/题材/主题分布 + 语法考查重点 + 高频实词 + 语篇填空逐空考点) ──
  function shellZhenti() {
    return pageHead("初中 · 沈阳中考", "真题特点", "2024+2025辽宁省统一卷(90题)静态分布 — 仅2年数据不支持逐年趋势, 只报分布") + `
<div class="bk-grid">
  <section class="bk-card"><div class="bk-h"><span>A 题型分布</span><span class="bk-src">/api/zhongkao/distribution</span></div><div id="jrzt-type" role="img" style="height:280px;"></div><div id="jrzt-type-sr" class="sr-only"></div></section>
  <section class="bk-card"><div class="bk-h"><span>B 题材(genre)分布 <small>48/90题</small></span><span class="bk-src">/api/zhongkao/exam_focus</span></div><div id="jrzt-genre" role="img" style="height:280px;"></div><div id="jrzt-genre-sr" class="sr-only"></div></section>
</div>
<div class="bk-grid" style="margin-top:14px;">
  <section class="bk-card"><div class="bk-h"><span>C 主题群(theme_l2)分布 <small>义务教育课标2022官方10群</small></span><span class="bk-src">/api/zhongkao/exam_focus</span></div><div id="jrzt-theme" role="img" style="height:280px;"></div><div id="jrzt-theme-sr" class="sr-only"></div></section>
  <section class="bk-card"><div class="bk-h"><span>D 语法考查重点 <small>20题语篇填空样本</small></span><span class="bk-src">/api/zhongkao/exam_focus</span></div><div id="jrzt-grammar"></div></section>
</div>
<section class="bk-card" style="margin-top:14px;"><div class="bk-h"><span>E 高频实词 <small>90题全覆盖, 已排除功能词</small></span><span class="bk-src">/api/zhongkao/exam_focus</span></div>
  <div id="jrzt-vocab" style="display:flex;flex-wrap:wrap;gap:6px;"></div></section>
<section class="bk-card" style="margin-top:14px;"><div class="bk-h"><span>F 语篇填空逐空考点 <small>每年10空</small></span><span class="bk-src">/api/zhongkao/distribution</span></div>
  <p class="muted" style="font-size:11px;margin:0 0 8px;">辽宁中考语篇填空固定10空(31-40), 每空1语法考点 · 与高考语法填空考点全集重合(见K12衔接页)</p>
  <div id="jrzt-pivot"></div></section>`;
  }

  function renderBar(elId, srId, rows, labelKey, color, ariaPrefix) {
    const el = G.$(elId);
    if (!rows || !rows.length) { if (el) el.innerHTML = '<p class="muted" style="padding:12px">暂无数据</p>'; return; }
    const ch = G.initChart(el);
    const rv = rows.slice().reverse();
    ch.setOption({
      grid: { left: 4, right: 30, top: 8, bottom: 8, containLabel: true },
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
      xAxis: { type: "value", splitLine: { lineStyle: { color: "rgba(128,128,128,0.12)" } } },
      yAxis: { type: "category", data: rv.map(r => r[labelKey]), axisTick: { show: false }, axisLine: { show: false }, axisLabel: { fontSize: 10 } },
      series: [{ type: "bar", data: rv.map(r => r.n), barWidth: "60%", itemStyle: { color, borderRadius: [0, 4, 4, 0] }, label: { show: true, position: "right", fontSize: 11 } }],
    });
    if (el) el.setAttribute("aria-label", `${ariaPrefix}: ` + rows.map(r => `${r[labelKey]} ${r.n}`).join("; "));
    const sr = G.$(srId);
    if (sr) sr.innerHTML = `<table><caption>${ariaPrefix}</caption><thead><tr><th>项</th><th>题数</th></tr></thead><tbody>`
      + rows.map(r => `<tr><td>${r[labelKey]}</td><td>${r.n}</td></tr>`).join("") + `</tbody></table>`;
    return ch;
  }

  function renderGrammarFocus(rows) {
    const el = G.$("#jrzt-grammar");
    if (!rows || !rows.length) { el.innerHTML = '<p class="muted" style="padding:12px">暂无数据</p>'; return; }
    el.innerHTML = `<div style="display:flex;flex-direction:column;gap:6px;">` + rows.map(r =>
      `<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 10px;background:var(--sunken);border-radius:6px;font-size:13px;">
        <span>${r.grammar_item}</span><span style="font-family:var(--num);color:var(--ink-3);">${r.n} 次</span></div>`).join("") + `</div>`;
  }

  function renderVocabFocus(rows) {
    const el = G.$("#jrzt-vocab");
    if (!rows || !rows.length) { el.innerHTML = '<p class="muted" style="padding:12px">暂无数据</p>'; return; }
    const max = Math.max(...rows.map(r => r.n), 1);
    el.innerHTML = rows.map(r => {
      const size = 12 + Math.round(10 * r.n / max);
      return `<span style="font-size:${size}px;padding:3px 9px;background:var(--sunken);border-radius:12px;color:var(--ink);" title="${r.n}次">${r.word} <span style="font-size:10px;color:var(--ink-3);font-family:var(--num);">${r.n}</span></span>`;
    }).join("");
  }

  function renderPivot(d) {
    const p = d["语篇填空_pivot"];
    const el = G.$("#jrzt-pivot");
    if (!el) return;
    if (!p || !p.rows || !p.rows.length) { el.innerHTML = '<p class="muted" style="font-size:12px;">暂无数据</p>'; return; }
    const yrs = p.years || [];
    const cell = (txt) => {
      if (!txt) return '<span class="muted">—</span>';
      const s = _splitKaodian(txt);
      return `${s.ans ? `<span style="font-family:var(--num);">${s.ans}</span> ` : ""}<span style="background:#EAF0F6;color:var(--down);padding:1px 6px;border-radius:4px;font-size:11px;">${s.cat}</span>`;
    };
    el.innerHTML = `<table style="width:100%;border-collapse:collapse;font-size:13px;">
      <thead><tr style="text-align:left;border-bottom:2px solid var(--line);"><th style="padding:5px 8px;width:64px;">空号</th>${yrs.map(y => `<th style="padding:5px 8px;">${y}</th>`).join("")}</tr></thead>
      <tbody>${p.rows.map(r => `<tr style="border-bottom:1px solid var(--line-soft);"><td style="padding:5px 8px;color:var(--ink-3);">第${r.blank}空</td>${yrs.map(y => `<td style="padding:5px 8px;">${cell(r["考点"][y])}</td>`).join("")}</tr>`).join("")}</tbody>
    </table>`;
  }

  registerTab("jr_zhenti", async () => {
    G.$("#content").innerHTML = shellZhenti();
    const echartsOk = await G.ensureECharts();
    const [dist, focus] = await Promise.all([
      fetchJSON("/api/zhongkao/distribution").catch(() => ({ by_question_type: [] })),
      fetchJSON("/api/zhongkao/exam_focus").catch(() => ({})),
    ]);
    if (echartsOk) {
      chType = renderBar("#jrzt-type", "#jrzt-type-sr", dist.by_question_type, "type", "#BE3A2B", "中考题型分布");
      chGenre = renderBar("#jrzt-genre", "#jrzt-genre-sr", focus.genre_分布, "label", "#2E7D54", "题材(genre)分布");
      chTheme = renderBar("#jrzt-theme", "#jrzt-theme-sr", focus.theme_l2_分布, "label", "#378ADD", "主题群(theme_l2)分布");
    } else { G.chartLoadError(G.$("#jrzt-type")); }
    renderGrammarFocus(focus.语法考查重点);
    renderVocabFocus(focus.高频实词);
    renderPivot(dist);
    if (!window.__rzJrZt) { window.__rzJrZt = 1; window.addEventListener("resize", () => { chType && chType.resize(); chGenre && chGenre.resize(); chTheme && chTheme.resize(); }); }
  });
})();
