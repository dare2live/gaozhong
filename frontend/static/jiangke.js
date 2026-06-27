/* 讲课工作流 — D 概念快查(4路追溯浮窗) + C' 考点关联网络 (第七阶段 7.2).
 *
 * 铁律1 单一计算点: C' 是把 service 已算的 cooccurrence pairs **展示层重塑**成 {nodes,edges}
 *   喂 ECharts 力导向图, 非重写 JOIN/agg(聚合在 exam_point/cooccur.py 已做)。
 * D 概念浮窗: 完全复用 graph_popup.js — 渲染 GZ.conceptLink('word:x','x') 即 .gz-concept,
 *   全局 click 委托自动弹 /api/graph/popup 的 真题↔考点↔课标↔教材 4 路追溯, 零新建。
 * 分层非平均: 共现按卷制 era(默认 2021+ 新高考II)。
 */
(function () {
  const G = window.GZ;
  if (!G || !G.registerTab) return;
  const { fetchJSON, conceptLink, registerTab } = G;

  const ERA = "2021+_新高考II";
  const _DCj = (window.GZ_CAT && window.GZ_CAT.dim) || {};   // 维度基础标签单一来源 category-config.js
  const CATS = [{ name: _DCj.genre, c: "#BE3A2B" }, { name: _DCj.theme_context, c: "#1F5F94" }, { name: _DCj.theme_l2, c: "#2E7D54" }];
  const DIMCAT = { genre: 0, theme_context: 1, theme_l2: 2 };
  // 高 gaokao 命中考点词 (teaching_hint 双印证), 当堂快查示例
  const QUICK = [["word:time", "time"], ["word:people", "people"], ["word:make", "make"], ["word:work", "work"], ["word:important", "important"], ["word:environment", "environment"], ["word:experience", "experience"]];
  let chart = null;

  function shell() {
    return `
<h2 style="margin:0 0 2px;">讲课 · 概念调取 + 考点关联</h2>
<p class="muted" style="margin:0 0 14px;font-size:13px;">当堂任一词/语法一键调出 4 路追溯(真题↔考点↔课标↔教材) · 共现网络看哪些考点同题考</p>

<section class="bk-card" style="margin-bottom:14px;">
  <div class="bk-h"><span>D 概念快查 <small>点词 → 4 路追溯浮窗</small></span><span class="bk-src">/api/graph/popup</span></div>
  <div style="display:flex;gap:8px;align-items:center;margin-bottom:10px;">
    <input id="jk-q" placeholder="输入讲到的词 (如 power / family) 回车" style="flex:1;padding:7px 10px;border:1px solid #d8d5cc;border-radius:6px;font-size:13px;">
    <button id="jk-go" style="padding:7px 14px;">查 4 路</button>
  </div>
  <div id="jk-hit" style="margin-bottom:10px;"></div>
  <div class="muted" style="font-size:11px;margin-bottom:5px;">常用高频考点词 (课标+辽宁高考双印证):</div>
  <div id="jk-quick" style="display:flex;flex-wrap:wrap;gap:7px;"></div>
</section>

<section class="bk-card">
  <div class="bk-h"><span>C' 考点关联网络 <small>同题共现 · 2021+ 辽宁卷</small></span><span class="bk-src">/api/exam_point/cooccurrence</span></div>
  <div class="muted" style="font-size:11px;margin-bottom:6px;">边粗=共现次数(co_n≥2 才报) · 拖拽/缩放 · 点节点看该考点真题。记叙文×人与社会、说明文×人与自我 等成对设计组卷。</div>
  <div id="jk-graph" role="img" aria-label="考点同题共现网络图(加载中)" style="height:420px;"></div>
  <div id="jk-graph-sr" class="sr-only"></div>
</section>`;
  }

  function renderQuick() {
    G.$("#jk-quick").innerHTML = QUICK.map(([id, lab]) => conceptLink(id, lab)).join("");
  }

  function doSearch() {
    const v = (G.$("#jk-q").value || "").trim().toLowerCase().replace(/[^a-z' -]/g, "");
    if (!v) return;
    G.$("#jk-hit").innerHTML = `点击调出 4 路追溯: ${conceptLink("word:" + v, v)} <span class="muted" style="font-size:11px;">(不存在则浮窗提示, 可改词/语法)</span>`;
  }

  function buildGraph(pairs) {
    const nodeMap = {};
    pairs.forEach(p => {
      [[p.a_label, p.a_dim], [p.b_label, p.b_dim]].forEach(([lab, dim]) => {
        if (!nodeMap[lab]) nodeMap[lab] = { name: lab, category: DIMCAT[dim] ?? 1, dim: dim, value: 0 };   // #3: 存 dim 供 click 拼 concept_id
        nodeMap[lab].value += p.co_n;
      });
    });
    const nodes = Object.values(nodeMap).map(n => ({ ...n, symbolSize: Math.min(54, 14 + n.value / 2.5) }));
    const links = pairs.map(p => ({ source: p.a_label, target: p.b_label, value: p.co_n, lineStyle: { width: Math.max(1, p.co_n / 5) } }));
    return { nodes, links };
  }

  function dimLabel(dim) { return _DCj[dim] || dim || "维度"; }   // genre→体裁 theme_context→主题语境 theme_l2→主题群

  // 读屏 a11y: 复用已算 nodes / usedPairs, 不重算不 refetch(Rule1 单一计算点)。
  // 诚实声明: 体裁/主题维度标签由模型推断方向性标注(C 层), 非官方判定; 共现=同题出现, 非因果。
  function applyA11y(el, nodes, usedPairs) {
    const topNodes = [...nodes].sort((a, b) => b.value - a.value).slice(0, 5);
    const topPairs = [...usedPairs].sort((a, b) => b.co_n - a.co_n).slice(0, 8);
    const overview = topPairs.length
      ? `共现对 ${usedPairs.length} 条、考点节点 ${nodes.length} 个。关联最强: ` +
        topPairs.slice(0, 3).map(p => `${p.a_label}×${p.b_label} 同题 ${p.co_n} 次`).join("、")
      : "暂无共现数据。";
    el.setAttribute("aria-label", `C' 考点同题共现网络(2021+ 辽宁卷)。${overview} 体裁/主题维度为模型推断方向性标注。`);

    const rowsNode = topNodes.map(n =>
      `<tr><td>${n.name}</td><td>${dimLabel(n.dim)}(模型推断)</td><td>${n.value}</td></tr>`).join("");
    const rowsPair = topPairs.map(p =>
      `<tr><td>${p.a_label}(${dimLabel(p.a_dim)})</td><td>${p.b_label}(${dimLabel(p.b_dim)})</td><td>${p.co_n}</td></tr>`).join("");
    const sr = G.$("#jk-graph-sr");
    if (sr) sr.innerHTML =
      `<p>C' 考点同题共现网络数据表(2021+ 辽宁卷, 共 ${nodes.length} 节点 / ${usedPairs.length} 共现对)。` +
      `体裁、主题语境、主题群维度为模型推断方向性标注(C 层, 非官方判定); 共现指同一真题中同时出现, 非因果。</p>` +
      `<table><caption>关联强度最高的考点(节点, 强度=同题共现次数累加)</caption>` +
      `<thead><tr><th>考点</th><th>维度</th><th>关联强度</th></tr></thead><tbody>${rowsNode}</tbody></table>` +
      `<table><caption>同题共现最频繁的考点对</caption>` +
      `<thead><tr><th>考点 A</th><th>考点 B</th><th>同题共现次数</th></tr></thead><tbody>${rowsPair}</tbody></table>`;
  }

  async function renderGraph(pairs) {
    const strong = pairs.filter(p => p.co_n >= 3);   // 滤弱边减 hairball (key 关联 co_n≥3 全保留)
    const usedPairs = strong.length ? strong : pairs;   // a11y 复用此同一选择, 不重算(Rule1)
    const { nodes, links } = buildGraph(usedPairs);
    const el = G.$("#jk-graph");
    // force 布局按 init 时 canvas 宽算节点位 → 必须等 SPA 挂载后 layout 完成(容器有宽)再 init, 否则挤左
    for (let i = 0; i < 30 && el.clientWidth < 80; i++) await new Promise(r => requestAnimationFrame(r));
    chart = echarts.getInstanceByDom(el) || echarts.init(el);
    chart.setOption({
      color: CATS.map(c => c.c),
      legend: [{ data: CATS.map(c => c.name), bottom: 0, textStyle: { fontSize: 11 } }],
      tooltip: { formatter: p => p.dataType === "edge" ? `${p.data.source} × ${p.data.target}<br/>同题共现 ${p.data.value} 次` : `${p.data.name}<br/>关联强度 ${p.data.value}` },
      series: [{
        type: "graph", layout: "force", roam: true, draggable: true,
        categories: CATS.map(c => ({ name: c.name })), data: nodes, links,
        label: { show: true, position: "right", fontSize: 11, color: "#333" },
        force: { repulsion: 480, edgeLength: [80, 200], gravity: 0.04, friction: 0.5 },
        lineStyle: { color: "source", opacity: 0.4, curveness: 0.15 },
        emphasis: { focus: "adjacency", label: { fontSize: 13 }, lineStyle: { width: 4, opacity: 0.8 } },
      }],
    });
    applyA11y(el, nodes, usedPairs);   // 读屏: aria-label 概览 + sr-only 共现对表(复用已算 nodes/usedPairs)
    setTimeout(() => chart && chart.resize(), 60);   // 修容器初始宽度0致节点挤左
    chart.off("click");
    // #3: 点考点节点 → 弹该考点浮窗(关联+真题, 复用#2); fallback sendPrompt
    chart.on("click", p => {
      if (p.dataType !== "node") return;
      const cid = p.data.dim ? `exam_point:${p.data.dim}:${p.data.name}` : null;
      if (cid && G.openPopup) G.openPopup(cid);
      else if (G.sendPrompt) G.sendPrompt(`看考点「${p.data.name}」在 2021+ 辽宁卷的真题与同题共现考点`);
    });
  }

  registerTab("jiangke", async () => {
    G.$("#content").innerHTML = shell();
    renderQuick();
    G.$("#jk-go").onclick = doSearch;
    G.$("#jk-q").addEventListener("keydown", e => { if (e.key === "Enter") doSearch(); });
    const echartsOk = await G.ensureECharts();   // RC1: 等 echarts 就绪防静默空白
    const co = await fetchJSON("/api/exam_point/cooccurrence").catch(() => ({ by_era: {} }));
    const pairs = ((co.by_era || {})[ERA] || {}).pairs || [];
    if (!echartsOk) G.chartLoadError(G.$("#jk-graph"));   // D0诚实: 图表组件失败显式报错
    else if (pairs.length) await renderGraph(pairs);
    else G.$("#jk-graph").innerHTML = '<p class="muted">无共现数据</p>';
    if (!window.__rzJk) { window.__rzJk = 1; window.addEventListener("resize", () => chart && chart.resize()); }  // RC1: 只绑一次防泄漏
  });
})();
