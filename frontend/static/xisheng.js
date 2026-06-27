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

  // getting-started 引导 (坑4: 学情全 demo, 诚实化为"示例 + 如何接真实学情")
  function guide() {
    const step = (n, t, d) => `<div class="eg-step"><span class="eg-n">${n}</span><div><div class="eg-st">${t}</div><div class="eg-sd">${d}</div></div></div>`;
    return `<div class="empty-guide">
      <span class="eg-tag">示例数据</span>
      <div class="eg-title">接入真实学情 · 三步</div>
      <div class="eg-why">当前作答为示例合成 (D0 诚实: 不在零真实作答上渲染伪造置信度)。导入真实数据后, 弱点 / 热力 / 分层推荐自动派生。</div>
      <div class="eg-steps">
        ${step(1, "建班 · 导入名单", '上传学生名单 CSV (姓名 + 学号), 系统建班建档 · 多租户隔离。<a href="#/students">学生档案 →</a>')}
        ${step(2, "上传答题卡", '扫描录入 OCR 识别作答 → 自动判分入 student_answers。<a href="#/scan">扫描录入 →</a>')}
        ${step(3, "自动学情", "错题聚合真考点弱点 + 分层复习推荐 + 结构对齐同构练习 (本页)。")}
      </div>
    </div>`;
  }

  function shell() {
    return `
<h2 style="margin:0 0 2px;">分析学生 · 班级学情</h2>
<p class="muted" style="margin:0 0 14px;font-size:13px;">多租户: 老师只见自己班级学生 (teacher_id 隔离) · 错题 → 真考点弱点聚合</p>
${guide()}
<div class="bk-filter"><span class="bk-flabel">老师</span><span id="xs-teachers"></span>
  <span class="bk-flabel" style="margin-left:8px;">班级</span><span id="xs-classes"></span></div>
<div id="xs-banner"></div>
<section class="bk-card"><div class="bk-h"><span>班级薄弱真考点 <small>示例预览 · 错题聚合 avg 弱点分</small></span><span class="bk-src">/api/students/class_weakness</span></div>
  <div id="xs-heat" role="img" aria-label="班级薄弱真考点热力图 (示例数据)" style="height:340px;"></div>
  <div id="xs-heat-sr" class="sr-only"></div></section>`;
  }

  function pill(id, label, on, attr) {
    return `<button class="bk-pill ${on ? "on" : ""}" data-${attr}="${id}">${label}</button>`;
  }

  async function loadClasses() {
    const d = await fetchJSON(`/api/students/classes?teacher_id=${encodeURIComponent(state.teacher)}`).catch(() => ({ classes: [] }));
    const cls = d.classes || [];
    G.$("#xs-classes").innerHTML = cls.map(c => pill(c.class_id, `${c.name} (${c.n_students}人)`, c.class_id === state.cls, "cls")).join("") || '<span class="muted" style="font-size:12px;">无班级</span>';
    G.$$("#xs-classes [data-cls]").forEach(b => b.onclick = () => { state.cls = b.dataset.cls; loadClasses(); loadWeakness(); });
    if (cls.length) { if (!cls.some(c => c.class_id === state.cls)) state.cls = cls[0].class_id; loadWeakness(); }   // 总渲: 重访时 state.cls 已有也要渲, 否则 #xs-heat 空
  }

  async function loadWeakness() {
    if (!state.cls || !state.teacher) return;
    // teacher_id 必传: 路由 owns_class 多租户校验 (缺则 MISSING → 热力图空白死链, 已修)
    const d = await fetchJSON(`/api/students/class_weakness?class_id=${encodeURIComponent(state.cls)}&teacher_id=${encodeURIComponent(state.teacher)}`).catch(() => ({ weakness: [] }));
    if (d.error) { G.$("#xs-banner").innerHTML = `<span style="color:#BE3A2B">学情加载失败: ${d.error}</span>`; return; }
    G.$("#xs-banner").innerHTML = d.data_status
      ? `<div style="display:flex;align-items:center;gap:8px;padding:8px 12px;background:#FCEBEB;border:1px solid #F09595;border-radius:6px;margin-bottom:12px;font-size:12px;color:#791F1F;"><b style="font-weight:500;">${d.data_status}</b></div>` : "";
    const rows = (d.weakness || []).slice(0, 12).reverse();
    if (!window.echarts) { G.chartLoadError(G.$("#xs-heat")); return; }   // D0诚实: 图表组件失败显式报错
    if (!rows.length) { G.$("#xs-heat").innerHTML = '<p class="muted" style="padding:12px">暂无弱点数据 (示例库)</p>'; return; }
    chart = G.initChart(G.$("#xs-heat"));
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
    // a11y: 复用已派生 rows (单一计算点, 不重算/不 refetch)。rows 已 reverse 为图表自下而上序,
    // 这里再 reverse 回弱点由高到低的自然阅读序。诚实标"示例"。
    const ordered = rows.slice().reverse();
    const heatEl = G.$("#xs-heat");
    if (heatEl) {
      const head = ordered.slice(0, 5).map(r => `${r.label} ${Math.round(r.avg_score * 100)}%`).join(", ");
      heatEl.setAttribute("aria-label", `班级薄弱真考点热力图 (示例数据)，共 ${ordered.length} 项，弱点由高到低：${head}${ordered.length > 5 ? " 等" : ""}`);
    }
    const srEl = G.$("#xs-heat-sr");
    if (srEl) {
      const body = ordered.map(r => `<tr><td>${r.label}</td><td>${Math.round(r.avg_score * 100)}%</td><td>${r.n_weak_students}</td><td>${r.total_sample}</td></tr>`).join("");
      srEl.innerHTML = `<table><caption>班级薄弱真考点 (示例数据) — 弱点由高到低</caption><thead><tr><th>考点</th><th>弱点分</th><th>薄弱学生数</th><th>样本量 n</th></tr></thead><tbody>${body}</tbody></table>`;
    }
  }

  registerTab("xisheng", async () => {
    G.$("#content").innerHTML = shell();
    const t = await fetchJSON("/api/students/teachers").catch(() => ({ teachers: [] }));
    const teachers = t.teachers || [];
    if (!teachers.length) { G.$("#xs-teachers").innerHTML = '<span class="muted" style="font-size:12px;">无老师数据</span>'; return; }
    state.teacher = teachers[0].teacher_id;
    G.$("#xs-teachers").innerHTML = teachers.map(x => pill(x.teacher_id, `${x.name} (${x.n_classes}班)`, x.teacher_id === state.teacher, "tch")).join("");
    G.$$("#xs-teachers [data-tch]").forEach(b => b.onclick = () => { state.teacher = b.dataset.tch; state.cls = null; G.$$("#xs-teachers .bk-pill").forEach(p => p.classList.toggle("on", p.dataset.tch === state.teacher)); loadClasses(); });
    await G.ensureECharts();   // RC1: 等 echarts 就绪防静默空白
    await loadClasses();
    if (!window.__rzXs) { window.__rzXs = 1; window.addEventListener("resize", () => chart && chart.resize()); }  // RC1: 只绑一次防泄漏
  });
})();
