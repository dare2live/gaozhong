/* gaozhong teacher.js — 教师端逻辑 (从 teacher.html 抽出, Rule 5).
   依赖 common.js (GZ.*) */
const { $, $$, fetchJSON, tagChip } = GZ;

const LOADERS = {
  overview: async () => {
    const s = await fetchJSON("/api/stats");
    const qb = await fetchJSON("/api/qb/stats");
    $("#tab-overview").innerHTML = `
      <h2>数据 + 题库概览</h2>
      <div class="stat-tile"><div class="n">${qb.total || 0}</div><div class="l">题库</div></div>
      <div class="stat-tile"><div class="n">${qb.tags_total || 0}</div><div class="l">标签</div></div>
      <div class="stat-tile"><div class="n">${qb.question_tags || 0}</div><div class="l">题-标</div></div>
      <div class="stat-tile"><div class="n">${s.exam_questions}</div><div class="l">真题</div></div>
      <div class="stat-tile"><div class="n">${s.nodes}</div><div class="l">graph nodes</div></div>
      <div class="stat-tile"><div class="n">${s.edges}</div><div class="l">graph edges</div></div>
      <h3>题型分布</h3>
      <table>${Object.entries(qb.by_type || {}).map(([k, v]) => `<tr><td>${k}</td><td><b>${v}</b></td></tr>`).join("")}</table>
      <h3>标签维度</h3>
      <table>${Object.entries(qb.tag_by_kind || {}).map(([k, v]) => `<tr><td>${k}</td><td><b>${v}</b></td></tr>`).join("")}</table>`;
  },
  lesson: async () => {
    if (!$("#tab-lesson").innerHTML) {
      $("#tab-lesson").innerHTML = `
        <h2>备课 — 选 unit 看考点与教材</h2>
        <label>unit: <select id="lp-unit" style="padding:6px;min-width:380px"></select></label>
        <button id="lp-go" class="btn-primary">查看</button>
        <div id="lp-body" style="margin-top:14px"></div>`;
      const rows = await fetchJSON("/api/units");
      $("#lp-unit").innerHTML = rows.map(r => `<option value="unit:${r.version_key}/${r.volume_key}/U${r.unit_number}">${r.version_key}/${r.volume_key}/U${r.unit_number} — ${r.title_en || ""}</option>`).join("");
      $("#lp-go").addEventListener("click", () => renderLesson($("#lp-unit").value));
    }
    if ($("#lp-unit").value) renderLesson($("#lp-unit").value);
  },
  qbank: async () => {
    if (!$("#tab-qbank").innerHTML) {
      const qb = await fetchJSON("/api/qb/stats");
      $("#tab-qbank").innerHTML = `
        <h2>题库浏览</h2>
        <label>题型: <select id="qb-type"><option value="">(全部)</option>${Object.keys(qb.by_type).map(k => `<option>${k}</option>`).join("")}</select></label>
        <input id="qb-tag" placeholder="tag_id (eg word:abandon, year:2022)" style="width:240px;padding:6px">
        <button id="qb-go" class="btn-primary">筛选</button>
        <div id="qb-body" style="margin-top:14px"></div>`;
      $("#qb-go").addEventListener("click", browseQbank);
    }
  },
  compose: async () => {
    if (!$("#tab-compose").innerHTML) {
      $("#tab-compose").innerHTML = `
        <h2>组卷</h2>
        <div class="compose-form">
          <label>题型分布:</label><input id="c-mix" value="阅读理解:4,语法填空:8,选义单选:8" placeholder="类型:数量,...">
          <label>必含标签:</label><input id="c-req" placeholder="word:abandon,unit:waiyan/bixiu_1/U1">
          <label>难度:</label><select id="c-diff"><option value="">(混合)</option><option>easy</option><option>mid</option><option>hard</option></select>
          <label>年份限制:</label><input id="c-year" placeholder="2020,2021,2022 (仅真题)">
          <label>随机种子:</label><input id="c-seed" type="number" value="42" style="width:80px">
          <label></label>
          <div><button id="c-go" class="btn-primary">生成试卷</button>
                <button id="c-print" style="margin-left:8px">打印</button></div>
        </div>
        <div id="c-body" style="margin-top:18px"></div>`;
      $("#c-go").addEventListener("click", composeRun);
      $("#c-print").addEventListener("click", () => window.print());
    }
  },
  graph: async () => {
    if (!$("#tab-graph").innerHTML) {
      const tags = await fetchJSON("/api/qb/tags?kind=word&limit=30");
      $("#tab-graph").innerHTML = `
        <h2>知识图谱 · 教师视角</h2>
        <h3>高频考词 top 30 (按题库标签数)</h3>
        <div>${tags.map(t => tagChip(`${t.label} · ${t.n_q}`, "word")).join("")}</div>
        <h3>13 种关系 + 4945+ 节点</h3>
        <p>详 <a href="/" target="_blank">主页探索</a> · graph stats <code>/api/graph/stats</code></p>`;
    }
  },
};

async function renderLesson(uid) {
  const sub = await fetchJSON(`/api/graph/subgraph?node=${encodeURIComponent(uid)}&depth=1&max_nodes=80`);
  const words = sub.nodes.filter(n => n.node_type === "word").map(n => n.label);
  const themes = sub.nodes.filter(n => n.node_type === "theme").map(n => n.label);
  // 4.2.F 深度交叉关联 — 加 unit→真题考过词 (现 API 已通)
  const align = await fetchJSON(`/api/recommend/unit_exam_alignment?unit=${encodeURIComponent(uid)}`);
  $("#lp-body").innerHTML = `
    <h3>词汇 (${words.length})</h3>
    <div>${words.map(w => tagChip(w, "word")).join("")}</div>
    <h3>主题</h3>
    <div>${themes.length ? themes.map(t => tagChip(t, "theme")).join("") : "<em>未匹配</em>"}</div>
    <h3>真题对齐 — 本 unit 引入词中, 高考考过的 ${align.exam_overlap}/${align.intro_total}</h3>
    <div>${(align.examples || []).map(e => tagChip(`${e.word} · ${e.exam_freq}次`, "year")).join("")}</div>`;
}

async function browseQbank() {
  const t = $("#qb-type").value, tag = $("#qb-tag").value;
  const qs = new URLSearchParams();
  if (t) qs.set("type", t);
  if (tag) qs.set("tag", tag);
  qs.set("limit", "50");
  const rows = await fetchJSON("/api/qb/browse?" + qs);
  $("#qb-body").innerHTML = rows.map(q => `
    <div class="qb-row" onclick="loadDetail(${q.qb_id})">
      ${tagChip(q.question_type, "question_type")} ${tagChip(q.difficulty, "difficulty")}
      ${q.stem_preview}…
      <div class="meta">qb#${q.qb_id} · ${q.origin} · 答案 ${q.answer || "—"}</div>
    </div>`).join("");
}

async function composeRun() {
  const mix = $("#c-mix").value, req = $("#c-req").value;
  const diff = $("#c-diff").value, year = $("#c-year").value, seed = $("#c-seed").value;
  const q = new URLSearchParams();
  q.set("type_mix", mix);
  if (req) q.set("require_tags", req);
  if (diff) q.set("difficulty", diff);
  if (year) q.set("year_in", year);
  if (seed) q.set("seed", seed);
  const p = await fetchJSON("/api/paper/compose?" + q);
  if (p.error) { $("#c-body").innerHTML = `<em>${p.error}</em>`; return; }
  let html = `<h3>试卷 ${p.paper_id} · 目标 ${p.target_total} 实出 ${p.actual_total}</h3>`;
  if (Object.values(p.shortfalls || {}).some(v => v > 0))
    html += `<p style="color:#c1272d">缺额: ${JSON.stringify(p.shortfalls)}</p>`;
  for (const q of p.questions) {
    html += `<div class="paper-q">
      <div><b>${q.seq}.</b> ${tagChip(q.qtype, "question_type")} ${tagChip(q.difficulty, "difficulty")}</div>
      <div class="stem">${(q.stem || "").slice(0, 1500)}</div>
      ${q.options ? "<ul>" + q.options.map(o => `<li>${o.label}. ${o.text}</li>`).join("") + "</ul>" : ""}
      <details><summary>答案 / 解析</summary><pre style="white-space:pre-wrap">${q.answer || ""}
${q.analysis || ""}</pre></details>
      <div style="font-size:11px;color:#888">qb#${q.qb_id} · ${q.tags.slice(0, 8).map(t => tagChip(t, "")).join("")}</div>
    </div>`;
  }
  $("#c-body").innerHTML = html;
}

async function loadDetail(qbid) {
  const d = await fetchJSON(`/api/qb/detail?id=${qbid}`);
  alert(`qb#${d.qb_id}\n类型: ${d.qtype}\n标签: ${d.tags.join(" · ")}\n\n${d.stem.slice(0, 1500)}\n\n答案: ${d.answer}`);
}

window.loadDetail = loadDetail;

document.addEventListener("DOMContentLoaded", () => {
  GZ.mountLayout("/teacher");
  $$("#nav li").forEach(li => {
    li.addEventListener("click", () => {
      $$("#nav li").forEach(x => x.classList.remove("active"));
      li.classList.add("active");
      $$(".tab").forEach(t => t.style.display = "none");
      document.getElementById("tab-" + li.dataset.tab).style.display = "block";
      LOADERS[li.dataset.tab]?.();
    });
  });
  LOADERS.overview();
});
