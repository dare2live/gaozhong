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
  exam_point: async () => {
    const d = await fetchJSON("/api/exam_point/distribution");
    const DIM = { genre: "体裁", theme_l2: "主题群 (课标官方10群)", theme_l3: "子主题 (课标第三级·最细)", theme_context: "主题 (3大类)" };
    const suff = (d.sufficiency || {}).by_era || {};  // 件3 样本诚实标
    const eraTag = (era) => {
      const s = suff[era]; if (!s) return "";
      return s.distribution_eligible
        ? `<span class="ep-ok" title="同卷制 era 总题数达标, 占比可信">样本充足 ✓ (${s.n_total}题)</span>`
        : `<span class="ep-thin" title="样本不足, 占比仅供参考">样本不足 ⚠ (${s.n_total}题)</span>`;
    };
    const dimBlock = (dim) => d.eras.map(era => {
      const rows = (d.distribution[era] || {})[dim] || [];
      const bars = rows.map(r =>
        `<div class="ep-bar"><span class="ep-lab">${r.label}</span>` +
        `<span class="ep-track"><span class="ep-fill" style="width:${r.pct}%"></span></span>` +
        `<span class="ep-n">${r.n} · ${r.pct}%</span></div>`).join("");
      return `<div class="ep-era"><h4>${era} ${eraTag(era)}</h4>${bars || "<i>无数据</i>"}</div>`;
    }).join("");
    $("#tab-exam_point").innerHTML = `
      <h2>考点分布 — ${d.province_scope}</h2>
      <p class="ep-note">${d.layered_by} · provenance: ${d.provenance}</p>
      ${["genre", "theme_context", "theme_l2", "theme_l3"].map(dim =>
        `<h3>${DIM[dim] || dim}</h3><div class="ep-grid">${dimBlock(dim)}</div>`).join("")}`;
  },
  cooccur: async () => {
    const d = await fetchJSON("/api/exam_point/cooccurrence");
    const DIMN = { genre: "体裁", theme_l2: "主题群", theme_context: "主题" };
    const eras = Object.keys(d.by_era).sort().reverse();  // 新高考II 在前
    const block = (era) => {
      const slot = d.by_era[era] || { pairs: [] };
      const tag = slot.distribution_eligible
        ? `<span class="ep-ok">样本充足 ✓ (${slot.era_total_questions}题)</span>`
        : `<span class="ep-thin">样本不足 ⚠ 仅作参考 (${slot.era_total_questions}题)</span>`;
      const rows = (slot.pairs || []).map(p =>
        `<div class="ep-bar"><span class="co-lab">${DIMN[p.a_dim]||p.a_dim}:${p.a_label} ⨯ ${DIMN[p.b_dim]||p.b_dim}:${p.b_label}</span>` +
        `<span class="ep-n">同卷 ${p.co_n} 题共现</span></div>`).join("");
      return `<div class="ep-era"><h4>${era} ${tag}</h4>${rows || "<i>无 ≥2 题共现的跨轴考点对</i>"}</div>`;
    };
    $("#tab-cooccur").innerHTML = `
      <h2>考点关联性 — 辽宁卷 (哪些考点常一起考)</h2>
      <p class="ep-note">同题跨轴共现 (体裁⨯主题); co_n≥${d.min_co} 守门, ${d.layered_by}; 服务即时算不落表</p>
      <div class="ep-grid">${eras.map(block).join("")}</div>`;
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
  // 备课整合: 单次调 /api/lesson_plan (服务端单一整合点 — 词/语法/主题考点/对齐/趋势诚实)。
  // 不再前端各调 subgraph + unit_exam_alignment 自拼 (Rule 1: 整合在 service 算一次)。
  const lp = await fetchJSON(`/api/lesson_plan?unit=${encodeURIComponent(uid)}`).catch(e => ({ error: String(e) }));
  if (lp.error || !lp.unit_id) {
    $("#lp-body").innerHTML = `<em>加载失败: ${lp.error || "无数据"}</em>`;
    return;
  }
  const words = lp.words || [], grammar = lp.grammar || [], rex = lp.related_exams || [];
  const al = lp.alignment_summary || {}, th = lp.trend_honesty || {};
  const pr = lp.page_range || [];
  const wChip = w => tagChip(`${w.word}${w.exam_freq_count ? " · " + w.exam_freq_count + "次" : ""}${w.exam_status === "HV_extra" ? " ⭐" : ""}`, "word");
  const gChip = g => tagChip(`${g.label} · ${g.recent_exam_trace.length}真题`, "grammar");
  $("#lp-body").innerHTML = `
    <p class="lp-meta"><strong>${lp.title || ""}</strong>${lp.theme ? " · 主题 " + lp.theme.replace("theme:", "") : " · 主题未匹配"} · p.${pr[0] ?? "-"}–${pr[1] ?? "-"}</p>
    <div class="trend-banner">📊 命题趋势 (${th.province_scope || "辽宁卷"}): ${th.note || ""}${th.trend_reliable ? "" : " · <span style='color:#c1272d'>逐年斜率样本不足, 不画 slope</span>"}</div>
    <h3>词汇 — 本单元引入 ${al.intro_total ?? words.length}, 高考考过 ${al.exam_overlap ?? "?"} (按高考频次降序)</h3>
    <div>${words.length ? words.map(wChip).join("") : "<em>无</em>"}</div>
    <h3>语法 (${grammar.length}) — 课标项 + 真题溯源 (教此语法, 高考这么考)</h3>
    <div>${grammar.length ? grammar.map(gChip).join("") : "<em>本单元无 curated 语法点 (诚实跳过歧义)</em>"}</div>
    <h3>同主题高考真题 (${rex.length}) — 教此单元主题, 高考这么考 (4路追溯)</h3>
    <div>${rex.length ? rex.map(e => tagChip(`${e.year} ${e.question_type} · ${e.theme_point}`, "year")).join("") : "<em>无</em>"}</div>`;
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
