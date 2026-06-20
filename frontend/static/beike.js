/* 备课工作流「考点驾驶舱」— A考点分布 / B命题迁移 / C命题趋势 / E词汇热力 (第七阶段 viz 7.1).
 *
 * 铁律1 单一计算点: 全部 fetch /api/* service 产物, 前端**只渲染**; 迁移(B)是对两 era 已算 pct
 *   的展示层做差, 非重写 JOIN/agg。绝不在前端聚合 edges/exam_questions。
 * 分层非平均: 按卷制 era 分段看, 不混历史均值。
 * 样本量诚实: 趋势读 service 的 reliable 旗, 不可信→灰显虚线 + "样本不足" banner, 不画实斜率。
 * 词频≠考点: 词汇热力标题写"词频热力"(坑12 澄清)。
 * ECharts 仅渲染层 (CDN), 数据仍 service 单算。
 */
(function () {
  const G = window.GZ;
  if (!G || !G.registerTab) return;
  const { fetchJSON, registerTab } = G;

  const ERA_NEW = "2021+_新高考II";
  const ERA_OLD = "2015-2020_旧课标II";
  const DIM_LABEL = { genre: "体裁", theme_context: "主题语境", theme_l2: "主题群·课标10群", theme_l3: "子主题" };
  const C = { blue: "#185FA5", blueL: "#85B7EB", up: "#993C1D", upBg: "#FAECE7", down: "#185FA5", downBg: "#E6F1FB", grey: "#B4B2A9" };
  const STATUS = { core: ["核心", "#185FA5"], standard: ["标准", "#1D9E75"], HV_extra: ["高频超纲", "#BA7517"], LV_extra: ["低频超纲", "#B4B2A9"] };

  let state = { era: ERA_NEW, dim: "theme_l2", dist: null };
  const charts = {};

  function shell() {
    return `
<h2 style="margin:0 0 2px;">🎯 备课 · 考点驾驶舱</h2>
<p class="muted" style="margin:0 0 14px;font-size:13px;">辽宁卷锚定 · 按卷制 era 分层(非历史平均) · 数据全来自 service 单一计算点, 前端不重算</p>
<div id="bk-filter" class="bk-filter"></div>
<div class="bk-grid">
  <section class="bk-card"><div class="bk-h"><span>A 考点分布 <small id="bk-dimname">主题群</small></span><span class="bk-src">/api/exam_point/distribution</span></div><div id="bk-dist" style="height:300px;"></div></section>
  <section class="bk-card"><div class="bk-h"><span>B 命题迁移 <small>2015–20 → 2021+</small></span><span class="bk-src">展示层做差 · era 内对齐</span></div><div id="bk-shift"></div></section>
  <section class="bk-card"><div class="bk-h"><span>C 命题趋势 · 题型逐年</span><span id="bk-relbadge"></span></div><div id="bk-trend" style="height:240px;"></div><p id="bk-trendnote" class="muted" style="font-size:12px;margin:8px 0 0;"></p></section>
  <section class="bk-card"><div class="bk-h"><span>E 词汇热力 <small>词频非考点</small></span><span class="bk-src">/api/heatmap/vocab</span></div><div id="bk-heat" style="height:300px;"></div></section>
</div>`;
  }

  function filterBar() {
    const eraPill = (id, label) => `<button class="bk-pill ${state.era === id ? "on" : ""}" data-era="${id}">${label}</button>`;
    const dimOpt = Object.keys(DIM_LABEL).map(k => `<option value="${k}" ${state.dim === k ? "selected" : ""}>${DIM_LABEL[k]}</option>`).join("");
    const eras = state.dist ? state.dist.eras : [ERA_NEW, ERA_OLD];
    const n = eras.includes(state.era) && state.dist ? (state.dist.distribution[state.era].genre || []).reduce((a, x) => a + x.n, 0) : 0;
    const ok = n >= 30;
    return `
<span class="bk-flabel">卷制</span>${eraPill(ERA_NEW, "2021+ 新高考II")}${eraPill(ERA_OLD, "2015–2020")}
<span class="bk-lock">🔒 辽宁卷·锁定</span>
<span class="bk-flabel" style="margin-left:8px;">维度</span><select id="bk-dim">${dimOpt}</select>
<span class="bk-suff ${ok ? "ok" : "warn"}">${ok ? "分布可用 · " + n + "题" : "样本不足 · " + n + "题"}</span>`;
  }

  function renderDist() {
    const rows = (state.dist.distribution[state.era][state.dim] || []).slice().reverse();
    G.$("#bk-dimname").textContent = DIM_LABEL[state.dim];
    charts.dist = charts.dist || echarts.init(G.$("#bk-dist"));
    charts.dist.setOption({
      grid: { left: 4, right: 44, top: 8, bottom: 8, containLabel: true },
      xAxis: { type: "value", max: Math.max(...rows.map(r => r.pct)) * 1.15, axisLabel: { formatter: "{value}%" }, splitLine: { lineStyle: { color: "rgba(128,128,128,0.12)" } } },
      yAxis: { type: "category", data: rows.map(r => r.label), axisTick: { show: false }, axisLine: { show: false } },
      tooltip: { trigger: "axis", formatter: p => `${p[0].name}<br/>${p[0].value}% · n=${rows[p[0].dataIndex].n}` },
      series: [{
        type: "bar", data: rows.map(r => r.pct), barWidth: "62%",
        itemStyle: { color: C.blue, borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: "right", formatter: p => `${p.value}% · n=${rows[p.dataIndex].n}`, fontSize: 11, color: "#888" },
      }],
    });
    charts.dist.off("click");
    charts.dist.on("click", p => G.sendPrompt ? G.sendPrompt(`下钻 ${state.era} 辽宁卷 ${DIM_LABEL[state.dim]}「${p.name}」的真题清单`) : null);
  }

  function renderShift() {
    const nw = state.dist.distribution[ERA_NEW][state.dim] || [];
    const od = state.dist.distribution[ERA_OLD][state.dim] || [];
    const oldMap = Object.fromEntries(od.map(x => [x.label, x.pct]));
    const rows = nw.map(x => ({ label: x.label, now: x.pct, then: oldMap[x.label] ?? 0 }))
      .map(r => ({ ...r, d: Math.round((r.now - r.then) * 10) / 10 }))
      .sort((a, b) => Math.abs(b.d) - Math.abs(a.d)).slice(0, 6);
    G.$("#bk-shift").innerHTML = rows.map(r => {
      const up = r.d >= 0, col = up ? C.up : C.down, bg = up ? C.upBg : C.downBg;
      return `<div class="bk-shift-row"><span class="bk-shift-k">${r.label}</span>
        <span class="bk-shift-v">${r.then}% → <b>${r.now}%</b></span>
        <span class="bk-delta" style="color:${col};background:${bg};">${up ? "↑" : "↓"} ${Math.abs(r.d)}pt</span></div>`;
    }).join("");
  }

  function renderTrend(qt) {
    const list = (Array.isArray(qt) ? qt : []).filter(x => x.avg_share >= 0.03).slice(0, 8);
    const anyReliable = list.some(x => x.reliable);
    G.$("#bk-relbadge").innerHTML = anyReliable
      ? `<span class="bk-suff ok">趋势可信</span>`
      : `<span class="bk-suff warn">⚠ 趋势样本不足</span>`;
    charts.trend = charts.trend || echarts.init(G.$("#bk-trend"));
    charts.trend.setOption({
      grid: { left: 4, right: 12, top: 12, bottom: 8, containLabel: true },
      xAxis: { type: "category", data: list.map(x => x.question_type), axisLabel: { interval: 0, fontSize: 10, rotate: 20 } },
      yAxis: { type: "value", axisLabel: { formatter: v => Math.round(v * 100) + "%" }, splitLine: { lineStyle: { color: "rgba(128,128,128,0.12)" } } },
      tooltip: { trigger: "axis", formatter: p => `${p[0].name}<br/>占比 ${(p[0].value * 100).toFixed(1)}% · ${list[p[0].dataIndex].trend}` },
      series: [{ type: "bar", data: list.map(x => x.avg_share), barWidth: "52%", itemStyle: { color: anyReliable ? C.blue : C.grey, borderRadius: [4, 4, 0, 0] } }],
    });
    G.$("#bk-trendnote").innerHTML = anyReliable ? "题型逐年走向可信。"
      : `辽宁 post-2021 仅 5 年(2023=6 / 2025=9 题 &lt;10)→ <code>reliable=false</code>, 灰显占比快照<b>不画斜率</b>(坑12 谄媚死防线); 看上方 <b>A 分布</b>(可用)定重点。`;
  }

  function renderHeat(heat) {
    const sts = ["core", "standard", "HV_extra", "LV_extra"];
    const data = [];
    heat.letters.forEach((L, xi) => sts.forEach((s, yi) => data.push([xi, yi, (heat.cells[L] || {})[s] || 0])));
    const maxv = Math.max(...data.map(d => d[2]));
    charts.heat = charts.heat || echarts.init(G.$("#bk-heat"));
    charts.heat.setOption({
      grid: { left: 60, right: 8, top: 8, bottom: 40, containLabel: false },
      xAxis: { type: "category", data: heat.letters, splitArea: { show: true }, axisLabel: { fontSize: 9 } },
      yAxis: { type: "category", data: sts.map(s => STATUS[s][0]), splitArea: { show: true } },
      visualMap: { min: 0, max: maxv, calculable: true, orient: "horizontal", left: "center", bottom: 0, inRange: { color: ["#F1EFE8", "#85B7EB", "#185FA5"] }, textStyle: { fontSize: 10 } },
      tooltip: { formatter: p => `${heat.letters[p.data[0]]} · ${STATUS[sts[p.data[1]]][0]}<br/>${p.data[2]} 词` },
      series: [{ type: "heatmap", data, label: { show: false }, itemStyle: { borderColor: "rgba(255,255,255,0.4)", borderWidth: 1 } }],
    });
    charts.heat.off("click");
    charts.heat.on("click", p => G.sendPrompt ? G.sendPrompt(`列出 ${STATUS[sts[p.data[1]]][0]} 类 ${heat.letters[p.data[0]]} 开头的词`) : null);
  }

  function wire() {
    G.$("#bk-filter").innerHTML = filterBar();
    G.$$("#bk-filter [data-era]").forEach(b => b.onclick = () => { state.era = b.dataset.era; G.$("#bk-filter").innerHTML = filterBar(); wire(); renderDist(); renderShift(); });
    const sel = G.$("#bk-dim");
    if (sel) sel.onchange = () => { state.dim = sel.value; renderDist(); renderShift(); };
  }

  registerTab("beike", async () => {
    G.$("#content").innerHTML = shell();
    if (!window.echarts) { G.$("#bk-dist").innerHTML = '<p class="muted">ECharts 载入中…</p>'; await new Promise(r => setTimeout(r, 300)); }
    const [dist, qt, heat] = await Promise.all([
      fetchJSON("/api/exam_point/distribution"),
      fetchJSON("/api/trend/question_type_trend").catch(() => []),
      fetchJSON("/api/heatmap/vocab").catch(() => ({ letters: [], cells: {} })),
    ]);
    state.dist = dist;
    wire();
    if (window.echarts) { renderDist(); renderTrend(qt); renderHeat(heat); }
    renderShift();
    window.addEventListener("resize", () => Object.values(charts).forEach(c => c && c.resize()));
  });
})();
