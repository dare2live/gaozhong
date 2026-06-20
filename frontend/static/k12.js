/* K12 衔接工作流 — stage阶梯分布 + 10维语法蓝图 + 中考题型 (第七阶段 7.3, inc5).
 *
 * 铁律1: 全 fetch /api/k12/* + /api/zhongkao/* 的 service 单算点产物, 前端只渲染。
 * 诚实: 蓝图标 N=2 省统一卷实证(非趋势); stage 分布是 at_stage 边真值。
 */
(function () {
  const G = window.GZ;
  if (!G || !G.registerTab) return;
  const { fetchJSON, registerTab } = G;
  const STAGE_C = { "小学": "#9FE1CB", "初中": "#1D9E75", "义务教育": "#85B7EB", "高中必修": "#378ADD", "高中选修": "#185FA5" };
  let chS = null, chZ = null;

  function shell() {
    return `
<h2 style="margin:0 0 2px;">🔗 K12 衔接 · 初中 → 高中</h2>
<p class="muted" style="margin:0 0 14px;font-size:13px;">沈阳/辽宁 小学→初中→高中 单库 stage 维 · 中考语篇填空 10 维语法 = 高考语法填空考点全集 (最高优先级地基)</p>
<div class="bk-grid">
  <section class="bk-card"><div class="bk-h"><span>A stage 阶梯分布 <small>各阶段知识点数</small></span><span class="bk-src">/api/k12/stage_distribution</span></div><div id="k12-stage" style="height:300px;"></div></section>
  <section class="bk-card"><div class="bk-h"><span>C 中考题型分布 <small>2024+2025 省统一</small></span><span class="bk-src">/api/zhongkao/distribution</span></div><div id="k12-zk" style="height:300px;"></div></section>
</div>
<section class="bk-card" style="margin-top:14px;"><div class="bk-h"><span>B 10维语法蓝图 <small>中考语篇填空 ∩ 高考语法填空 (deepens 衔接边)</small></span><span class="bk-src">/api/k12/blueprint</span></div>
  <p class="muted" style="font-size:11px;margin:0 0 8px;">N=2 省统一卷实证(非趋势) · 初中学牢 → 高中深化 · 点对查关联</p>
  <div id="k12-bp"></div></section>`;
  }

  function renderStage(d) {
    const stages = Object.keys(d.by_stage || {});
    const words = stages.map(s => (d.by_stage[s].word || 0));
    const grams = stages.map(s => (d.by_stage[s].grammar || 0));
    chS = chS || echarts.init(G.$("#k12-stage"));
    chS.setOption({
      legend: { data: ["词", "语法"], bottom: 0, textStyle: { fontSize: 11 } },
      grid: { left: 4, right: 40, top: 8, bottom: 28, containLabel: true },
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
      xAxis: { type: "value", splitLine: { lineStyle: { color: "rgba(128,128,128,0.12)" } } },
      yAxis: { type: "category", data: stages, axisTick: { show: false }, axisLine: { show: false } },
      series: [
        { name: "词", type: "bar", stack: "t", data: words.map((v, i) => ({ value: v, itemStyle: { color: STAGE_C[stages[i]] || "#888" } })), label: { show: true, position: "insideRight", fontSize: 10, color: "#fff" } },
        { name: "语法", type: "bar", stack: "t", data: grams, itemStyle: { color: "#BA7517" }, label: { show: true, fontSize: 10 } },
      ],
    });
  }

  function renderZk(d) {
    const rows = (d.by_question_type || []).slice().reverse();
    chZ = chZ || echarts.init(G.$("#k12-zk"));
    chZ.setOption({
      grid: { left: 4, right: 30, top: 8, bottom: 8, containLabel: true },
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
      xAxis: { type: "value", splitLine: { lineStyle: { color: "rgba(128,128,128,0.12)" } } },
      yAxis: { type: "category", data: rows.map(r => r.type), axisTick: { show: false }, axisLine: { show: false }, axisLabel: { fontSize: 10 } },
      series: [{ type: "bar", data: rows.map(r => r.n), barWidth: "60%", itemStyle: { color: "#c1272d", borderRadius: [0, 4, 4, 0] }, label: { show: true, position: "right", fontSize: 11 } }],
    });
  }

  function renderBlueprint(d) {
    const pairs = d.pairs || [];
    G.$("#k12-bp").innerHTML = `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:6px;">` +
      pairs.map(p => `<div style="display:flex;align-items:center;gap:7px;font-size:12px;padding:5px 8px;background:var(--color-background-secondary,#f7f7f4);border-radius:6px;">
        <span style="background:#E1F5EE;color:#085041;padding:2px 7px;border-radius:5px;">初中 ${p.junior}</span>
        <span style="color:#888;">→</span>
        <span style="background:#E6F1FB;color:#0C447C;padding:2px 7px;border-radius:5px;">高中</span></div>`).join("") +
      `</div><p class="muted" style="font-size:11px;margin:8px 0 0;">共 ${d.n} 对衔接 · ${d.basis}</p>`;
  }

  registerTab("k12", async () => {
    G.$("#content").innerHTML = shell();
    if (!window.echarts) { await new Promise(r => setTimeout(r, 300)); }
    const [st, bp, zk] = await Promise.all([
      fetchJSON("/api/k12/stage_distribution").catch(() => ({ by_stage: {} })),
      fetchJSON("/api/k12/blueprint").catch(() => ({ pairs: [], n: 0 })),
      fetchJSON("/api/zhongkao/distribution").catch(() => ({ by_question_type: [] })),
    ]);
    if (window.echarts) { renderStage(st); renderZk(zk); }
    renderBlueprint(bp);
    window.addEventListener("resize", () => { chS && chS.resize(); chZ && chZ.resize(); });
  });
})();
