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
  // 共现网络渲染口径 = GZ.renderCooccurNetwork (common.js 单点, 与图谱tab同源同配色; dim色/节点边/点击→popup/a11y 统一)
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

  async function renderGraph(pairs) {
    const el = G.$("#jk-graph");
    // force 布局按 init 时 canvas 宽算节点位 → 必须等 SPA 挂载后 layout 完成(容器有宽)再渲, 否则挤左
    for (let i = 0; i < 30 && el.clientWidth < 80; i++) await new Promise(r => requestAnimationFrame(r));
    // 共享口径: 与图谱 tab 同源同配色 (dim色/节点边/点击→popup/aria+sr表 全在 GZ.renderCooccurNetwork)。
    // strongMin=3 滤弱边减 hairball (讲课聚焦强关联); srEl 出读屏数据表。
    chart = G.renderCooccurNetwork(el, pairs, { strongMin: 3, srEl: "#jk-graph-sr", eraLabel: "2021+ 新高考II" });
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
