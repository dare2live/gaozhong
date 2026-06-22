/* 析生工作流 — 多租户班级学情 (第七阶段 7.4, inc6; 域B teacher_id 隔离).
 *
 * 铁律1: fetch /api/students/* 单算点 (weakness 派生下沉 service)。
 * 多租户: 选老师 → 其班级(teacher_id作用域) → 班级 × 真考点弱点热力。
 * 诚实(坑4): 当前 demo seed → 红条 banner "示例数据·待真实答题量", 不伪装满看板。
 */
(function () {
  const G = window.GZ;
  if (!G || !G.registerTab) return;
  const { fetchJSON, registerTab } = G;
  let chart = null, state = { teacher: null, cls: null };

  function shell() {
    return `
<h2 style="margin:0 0 2px;">分析学生 · 班级学情</h2>
<p class="muted" style="margin:0 0 12px;font-size:13px;">多租户: 老师只见自己班级学生 (teacher_id 隔离) · 错题 → 真考点弱点聚合</p>
<div class="bk-filter"><span class="bk-flabel">老师</span><span id="xs-teachers"></span>
  <span class="bk-flabel" style="margin-left:8px;">班级</span><span id="xs-classes"></span></div>
<div id="xs-banner"></div>
<section class="bk-card"><div class="bk-h"><span>班级薄弱真考点 <small>错题聚合, avg 弱点分</small></span><span class="bk-src">/api/students/class_weakness</span></div>
  <div id="xs-heat" style="height:340px;"></div></section>`;
  }

  function pill(id, label, on, attr) {
    return `<button class="bk-pill ${on ? "on" : ""}" data-${attr}="${id}">${label}</button>`;
  }

  async function loadClasses() {
    const d = await fetchJSON(`/api/students/classes?teacher_id=${encodeURIComponent(state.teacher)}`).catch(() => ({ classes: [] }));
    const cls = d.classes || [];
    G.$("#xs-classes").innerHTML = cls.map(c => pill(c.class_id, `${c.name} (${c.n_students}人)`, c.class_id === state.cls, "cls")).join("") || '<span class="muted" style="font-size:12px;">无班级</span>';
    G.$$("#xs-classes [data-cls]").forEach(b => b.onclick = () => { state.cls = b.dataset.cls; loadClasses(); loadWeakness(); });
    if (cls.length && !cls.some(c => c.class_id === state.cls)) { state.cls = cls[0].class_id; loadWeakness(); }
  }

  async function loadWeakness() {
    if (!state.cls || !state.teacher) return;
    // teacher_id 必传: 路由 owns_class 多租户校验 (缺则 MISSING → 热力图空白死链, 已修)
    const d = await fetchJSON(`/api/students/class_weakness?class_id=${encodeURIComponent(state.cls)}&teacher_id=${encodeURIComponent(state.teacher)}`).catch(() => ({ weakness: [] }));
    if (d.error) { G.$("#xs-banner").innerHTML = `<span style="color:#c1272d">学情加载失败: ${d.error}</span>`; return; }
    G.$("#xs-banner").innerHTML = d.data_status
      ? `<div style="display:flex;align-items:center;gap:8px;padding:8px 12px;background:#FCEBEB;border:1px solid #F09595;border-radius:6px;margin-bottom:12px;font-size:12px;color:#791F1F;"><b style="font-weight:500;">${d.data_status}</b></div>` : "";
    const rows = (d.weakness || []).slice(0, 12).reverse();
    if (!window.echarts || !rows.length) { G.$("#xs-heat").innerHTML = '<p class="muted">无弱点数据</p>'; return; }
    chart = chart || echarts.init(G.$("#xs-heat"));
    chart.setOption({
      grid: { left: 4, right: 50, top: 8, bottom: 8, containLabel: true },
      tooltip: { trigger: "axis", formatter: p => `${p[0].name}<br/>弱点 ${(p[0].value * 100).toFixed(0)}% · ${rows[p[0].dataIndex].n_weak_students}生 · n=${rows[p[0].dataIndex].total_sample}` },
      xAxis: { type: "value", max: 1, axisLabel: { formatter: v => Math.round(v * 100) + "%" }, splitLine: { lineStyle: { color: "rgba(128,128,128,0.12)" } } },
      yAxis: { type: "category", data: rows.map(r => r.label), axisTick: { show: false }, axisLine: { show: false }, axisLabel: { fontSize: 10 } },
      visualMap: { show: false, min: 0, max: 1, inRange: { color: ["#FCEBEB", "#E24B4A", "#A32D2D"] } },
      series: [{ type: "bar", data: rows.map(r => r.avg_score), barWidth: "62%", itemStyle: { borderRadius: [0, 4, 4, 0] }, label: { show: true, position: "right", formatter: p => Math.round(p.value * 100) + "%", fontSize: 11, color: "#888" } }],
    });
    chart.off("click");
    chart.on("click", p => G.sendPrompt && G.sendPrompt(`为班级薄弱考点「${rows[p.dataIndex].label}」推荐分层复习课`));
  }

  registerTab("xisheng", async () => {
    G.$("#content").innerHTML = shell();
    const t = await fetchJSON("/api/students/teachers").catch(() => ({ teachers: [] }));
    const teachers = t.teachers || [];
    if (!teachers.length) { G.$("#xs-teachers").innerHTML = '<span class="muted" style="font-size:12px;">无老师数据</span>'; return; }
    state.teacher = teachers[0].teacher_id;
    G.$("#xs-teachers").innerHTML = teachers.map(x => pill(x.teacher_id, `${x.name} (${x.n_classes}班)`, x.teacher_id === state.teacher, "tch")).join("");
    G.$$("#xs-teachers [data-tch]").forEach(b => b.onclick = () => { state.teacher = b.dataset.tch; state.cls = null; G.$$("#xs-teachers .bk-pill").forEach(p => p.classList.toggle("on", p.dataset.tch === state.teacher)); loadClasses(); });
    if (!window.echarts) await new Promise(r => setTimeout(r, 300));
    await loadClasses();
    window.addEventListener("resize", () => chart && chart.resize());
  });
})();
