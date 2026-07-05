/* K12 衔接工作流 — stage阶梯分布 + 10维语法蓝图 + 中考题型 (第七阶段 7.3, inc5).
 *
 * 铁律1: 全 fetch /api/k12/* + /api/zhongkao/* 的 service 单算点产物, 前端只渲染。
 * 诚实: 蓝图标 N=2 省统一卷实证(非趋势); stage 分布是 at_stage 边真值。
 */
(function () {
  const G = window.GZ;
  if (!G || !G.registerTab) return;
  const { fetchJSON, registerTab } = G;
  const STAGE_C = (window.GZ_CAT && window.GZ_CAT.stage) || {};   // 学段色单一来源 category-config.js (no-hardcode)
  let chS = null, chZ = null;

  function shell() {
    return `
<h2 style="margin:0 0 2px;">K12 衔接 · 初中 → 高中</h2>
<p class="muted" style="margin:0 0 14px;font-size:13px;">沈阳/辽宁 小学→初中→高中 单库 stage 维 · 中考语篇填空逐空考点 = 高考语法填空考点全集 (最高优先级地基)</p>
<div class="bk-grid">
  <section class="bk-card"><div class="bk-h"><span>A stage 阶梯分布 <small>各阶段知识点数</small></span><span class="bk-src">/api/k12/stage_distribution</span></div><div id="k12-stage" role="img" style="height:300px;"></div><div id="k12-stage-sr" class="sr-only"></div><p id="k12-stage-cov" class="muted" style="font-size:11px;margin:6px 0 0;"></p></section>
  <section class="bk-card"><div class="bk-h"><span>C 中考题型分布 <small>2024+2025 省统一</small></span><span class="bk-src">/api/zhongkao/distribution</span></div><div id="k12-zk" role="img" style="height:300px;"></div><div id="k12-zk-sr" class="sr-only"></div><p id="k12-zk-honesty" class="muted" style="font-size:11px;margin:6px 0 0;color:#9a6a00;"></p></section>
</div>
<section class="bk-card" style="margin-top:14px;"><div class="bk-h"><span>B 语篇填空逐空考点 <small>每年10空 = 高考语法填空考点全集</small></span><span class="bk-src">/api/zhongkao/distribution</span></div>
  <p class="muted" style="font-size:11px;margin:0 0 8px;">辽宁中考语篇填空固定 10 空(31-40), 每空 1 语法考点 · 这 10 空 = 高考语法填空(7空)的考点母集 (N=2 省统一卷实证, 非趋势)</p>
  <div id="k12-pivot"></div></section>
<section class="bk-card" style="margin-top:14px;"><div class="bk-h"><span>D 细粒度语法点初高衔接 <small>deepens 边 (初中学牢→高中深化)</small></span><span class="bk-src">/api/k12/blueprint</span></div>
  <p class="muted" style="font-size:11px;margin:0 0 8px;">细粒度语法点逐一衔接(非10维粗分) · 初中掌握 → 高中同名深化 · N=2 实证</p>
  <div id="k12-bp"></div></section>`;
  }

  function renderStage(d) {
    const stages = Object.keys(d.by_stage || {});
    if (!stages.length) { const e = G.$("#k12-stage"); if (e) e.innerHTML = '<p class="muted" style="padding:12px">暂无 stage 分布数据</p>'; return; }   // RC1#37: 空态守卫(不渲零柱空图)
    const words = stages.map(s => (d.by_stage[s].word || 0));
    const grams = stages.map(s => (d.by_stage[s].grammar || 0));
    // 覆盖度诚实披露 (审计MEDIUM: 未分阶词不静默丢; coverage 来自 service)
    const cov = d.coverage;
    const covEl = G.$("#k12-stage-cov");
    if (covEl && cov) {
      const r = cov.unstaged_by_reason || {};
      covEl.innerHTML = `词分阶覆盖 ${cov.staged}/${cov.total_words} · 未分阶 ${cov.unstaged}（校本超纲 ${r["校本超纲"] || 0} + 课标变形 ${r["课标变形"] || 0}, 无标准阶段）`;
    }
    chS = G.initChart(G.$("#k12-stage"));
    // 坑(2026-07-05 数据可视化审计): 词(126-1409)与语法(0-71, 71 全部集中在"初中"一个 stage)
    // 量级差 1-2 个数量级且语义不同维度, 原用 stack:"t" 堆进同一根柱: 语法段在"初中"柱里只占
    // 4.8%长度(几不可见), 其余4个stage因语法=0干脆不显示棕色段, 但图例"语法"常显, 造成"语法在
    // 多数阶段可忽略"的错误整体印象, 掩盖了"初中集中承载全部语法点"这一关键结构信息。改双X轴
    // 分组柱(各自独立刻度, 不再堆叠): 语法在其自身 0-71 量级刻度下能画出真实可读的柱长。
    chS.setOption({
      legend: { data: ["词", "语法"], bottom: 0, textStyle: { fontSize: 11 } },
      grid: { left: 4, right: 40, top: 8, bottom: 28, containLabel: true },
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
      xAxis: [
        { type: "value", position: "bottom", axisLabel: { fontSize: 10 }, splitLine: { lineStyle: { color: "rgba(128,128,128,0.12)" } } },
        { type: "value", position: "top", axisLabel: { fontSize: 10, color: "#9A6A00" }, splitLine: { show: false } },
      ],
      yAxis: { type: "category", data: stages, axisTick: { show: false }, axisLine: { show: false } },
      series: [
        { name: "词", type: "bar", xAxisIndex: 0, data: words.map((v, i) => ({ value: v, itemStyle: { color: STAGE_C[stages[i]] || "#888" } })), label: { show: true, position: "right", fontSize: 10, color: "#76716A" } },
        { name: "语法", type: "bar", xAxisIndex: 1, data: grams, itemStyle: { color: "#9A6A00" }, label: { show: true, position: "right", fontSize: 10, color: "#9A6A00" } },
      ],
    });
    // a11y: 动态 aria-label + sr-only 数据表 (复用已算 stages/words/grams, 不重算)
    const stEl = G.$("#k12-stage");
    if (stEl) stEl.setAttribute("aria-label",
      "stage 阶梯分布柱状图: " + stages.map((s, i) => `${s} 词${words[i]}、语法${grams[i]}`).join("; "));
    const stSr = G.$("#k12-stage-sr");
    if (stSr) stSr.innerHTML = `<table><caption>stage 阶梯分布（各阶段词数与语法点数）</caption>`
      + `<thead><tr><th>阶段</th><th>词</th><th>语法</th></tr></thead><tbody>`
      + stages.map((s, i) => `<tr><td>${s}</td><td>${words[i]}</td><td>${grams[i]}</td></tr>`).join("")
      + `</tbody></table>`;
  }

  function renderZk(d) {
    const rows = (d.by_question_type || []).slice().reverse();
    if (!rows.length) { const e = G.$("#k12-zk"); if (e) e.innerHTML = '<p class="muted" style="padding:12px">暂无中考题型数据</p>'; return; }   // RC1#37: 空态守卫
    chZ = G.initChart(G.$("#k12-zk"));
    chZ.setOption({
      grid: { left: 4, right: 30, top: 8, bottom: 8, containLabel: true },
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
      xAxis: { type: "value", splitLine: { lineStyle: { color: "rgba(128,128,128,0.12)" } } },
      yAxis: { type: "category", data: rows.map(r => r.type), axisTick: { show: false }, axisLine: { show: false }, axisLabel: { fontSize: 10 } },
      series: [{ type: "bar", data: rows.map(r => r.n), barWidth: "60%", itemStyle: { color: "#BE3A2B", borderRadius: [0, 4, 4, 0] }, label: { show: true, position: "right", fontSize: 11 } }],
    });
    // a11y: 动态 aria-label + sr-only 数据表 (复用已算 rows, 不重算)
    const zkEl = G.$("#k12-zk");
    if (zkEl) zkEl.setAttribute("aria-label",
      "中考题型分布柱状图 (2024+2025 省统一): " + rows.map(r => `${r.type} ${r.n}`).join("; "));
    const zkSr = G.$("#k12-zk-sr");
    if (zkSr) zkSr.innerHTML = `<table><caption>中考题型分布（2024+2025 省统一卷）</caption>`
      + `<thead><tr><th>题型</th><th>题数</th></tr></thead><tbody>`
      + rows.map(r => `<tr><td>${r.type}</td><td>${r.n}</td></tr>`).join("")
      + `</tbody></table>`;
    // 内容完整性诚实 banner (审计HIGH#8: 不把空心当完整; content_status 来自 service 单算点)
    // #14: 删"完整 ${complete}"——service content_status 无 complete 键(全 walled/pending), 恒显"完整0"是误导冗余项
    const cs = d.content_status || {};
    const walled = cs.stem_walled || 0, pending = cs.answer_pending || 0;
    const el = G.$("#k12-zk-honesty");
    if (el) el.innerHTML = (walled || pending)
      ? `注 内容完整性: 题面门控 ${walled} · 答案待补 ${pending}（题型骨架完整, 题面/答案部分待补）`
      : "";
  }

  // 语篇填空逐空考点 pivot 表 (空号×年) — #9: service 单算点产物, 此前被前端 drop。
  // 考点文本如 "and连词" = 答案 + 语法类别; 展示时轻分割(纯排版, 非发明taxonomy), 不匹配则原样。
  function _splitKaodian(txt) {
    const m = /^([^一-龥]+?)\s*([一-龥].*)$/.exec(txt || "");
    return m ? { ans: m[1].trim(), cat: m[2].trim() } : { ans: "", cat: txt || "" };
  }
  function renderPivot(d) {
    const p = d["语篇填空_pivot"];
    const el = G.$("#k12-pivot");
    if (!el) return;
    if (!p || !p.rows || !p.rows.length) { el.innerHTML = '<p class="muted" style="font-size:12px;">暂无语篇填空考点数据</p>'; return; }
    const yrs = p.years || [];
    const cell = (txt) => {
      if (!txt) return '<span class="muted">—</span>';
      const s = _splitKaodian(txt);
      return `${s.ans ? `<span style="font-family:var(--num);">${s.ans}</span> ` : ""}<span style="background:#EAF0F6;color:var(--down);padding:1px 6px;border-radius:4px;font-size:11px;">${s.cat}</span>`;
    };
    el.innerHTML = `<table style="width:100%;border-collapse:collapse;font-size:13px;">
      <thead><tr style="text-align:left;border-bottom:2px solid var(--line);">
        <th style="padding:5px 8px;width:64px;">空号</th>${yrs.map(y => `<th style="padding:5px 8px;">${y} 中考考点</th>`).join("")}</tr></thead>
      <tbody>${p.rows.map(r => `<tr style="border-bottom:1px solid var(--line-soft);">
        <td style="padding:5px 8px;color:var(--ink-3);">第 ${r.blank} 空</td>${yrs.map(y => `<td style="padding:5px 8px;">${cell(r["考点"][y])}</td>`).join("")}</tr>`).join("")}</tbody>
    </table><p class="muted" style="font-size:11px;margin:8px 0 0;">${p.basis || ""}</p>`;
  }

  function renderBlueprint(d) {
    const pairs = d.pairs || [];
    if (!pairs.length) { G.$("#k12-bp").innerHTML = '<p class="muted" style="padding:12px">暂无语法衔接边数据</p>'; return; }   // RC1#21: 空态守卫(不渲空网格+"共0对"+undefined)
    // #9 修 bug: 原代码高中侧 <span>高中</span> 把 p.senior 整个 drop, 只显字面"高中"。
    G.$("#k12-bp").innerHTML = `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:6px;">` +
      pairs.map(p => `<div style="display:flex;align-items:center;gap:7px;font-size:12px;padding:5px 8px;background:var(--sunken);border-radius:6px;">
        <span style="background:#E1F5EE;color:var(--good);padding:2px 7px;border-radius:5px;">初中 ${p.junior}</span>
        <span style="color:var(--ink-3);">→</span>
        <span style="background:#E6F1FB;color:var(--down);padding:2px 7px;border-radius:5px;">高中 ${p.senior || p.junior}</span></div>`).join("") +
      `</div><p class="muted" style="font-size:11px;margin:8px 0 0;">共 ${d.n} 对细粒度衔接边(非10维粗分) · ${d.basis}</p>`;
  }

  registerTab("k12", async () => {
    G.$("#content").innerHTML = shell();
    const echartsOk = await G.ensureECharts();   // RC1: 等 echarts 就绪防静默空白
    const [st, bp, zk] = await Promise.all([
      fetchJSON("/api/k12/stage_distribution"),
      fetchJSON("/api/k12/blueprint").catch(() => ({ pairs: [], n: 0 })),
      fetchJSON("/api/zhongkao/distribution").catch(() => ({ by_question_type: [] })),
    ]);
    if (echartsOk) { renderStage(st); renderZk(zk); } else { G.chartLoadError(G.$("#k12-stage")); }
    renderPivot(zk);
    renderBlueprint(bp);
    if (!window.__rzK12) { window.__rzK12 = 1; window.addEventListener("resize", () => { chS && chS.resize(); chZ && chZ.resize(); }); }  // RC1: 只绑一次防泄漏
  });
})();
