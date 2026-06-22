/* 考试词典金矿 — exam_vocabulary(4186词) 接前端 (交付收口 B1).
 *
 * 铁律1: 全 fetch /api/exam_dictionary 的 service 单算点产物, 前端只渲染不重算。
 * 诚实: 释义带 gloss_source provenance 徽章(教材/中考/COCA兜底); 辽宁高考命中=真题边真值非估算。
 */
(function () {
  const G = window.GZ;
  if (!G || !G.registerTab) return;
  const { fetchJSON, registerTab } = G;

  // gloss_source provenance 徽章 (释义可信度分层, 不混同)
  const SRC = {
    textbook: ["教材", "#1D9E75"], unit_vocab: ["教材", "#1D9E75"], hujiao: ["教材", "#1D9E75"],
    zhongkao: ["中考", "#378ADD"], exam: ["真题", "#185FA5"],
    coca: ["COCA兜底", "#B4B2A9"], coca_fallback: ["COCA兜底", "#B4B2A9"],
  };
  const STAGE_C = (window.GZ_CAT && window.GZ_CAT.stage) || {};   // 学段色单一来源 category-config.js (防 k12/dict 漂移)

  function srcBadge(s) {
    const k = (s || "").toLowerCase();
    const hit = Object.keys(SRC).find(x => k.includes(x));
    const [t, c] = hit ? SRC[hit] : [s || "—", "#B4B2A9"];
    return `<span style="font-size:10px;padding:1px 6px;border-radius:8px;background:${c}22;color:${c};white-space:nowrap;">${t}</span>`;
  }

  function shell() {
    return `
<h2 style="margin:0 0 2px;">考试词典 · 金矿</h2>
<p class="muted" style="margin:0 0 12px;font-size:13px;">exam_vocabulary <span id="dict-total">…</span> 词 (课标∪教材真超纲) · 释义三源溯源(教材→中考→COCA兜底) · 辽宁高考命中=真题边真值 · service 单算点</p>
<div style="display:flex;gap:8px;align-items:center;margin-bottom:10px;flex-wrap:wrap;">
  <input id="dict-q" placeholder="输入词首字母前缀检索…" style="flex:1;min-width:180px;padding:7px 10px;border:1px solid #d8d6cd;border-radius:6px;font-size:14px;">
  <select id="dict-stage" style="padding:7px;border:1px solid #d8d6cd;border-radius:6px;">
    <option value="">全部阶段</option><option>初中</option><option>高中必修</option><option>高中选修</option>
  </select>
  <label style="font-size:13px;color:#666;"><input type="checkbox" id="dict-exam"> 仅辽宁高考命中</label>
  <span id="dict-n" class="muted" style="font-size:12px;"></span>
</div>
<div id="dict-list" style="max-height:62vh;overflow:auto;"></div>`;
  }

  function row(w) {
    const stage = w.stage || "—", sc = STAGE_C[stage] || "#888";
    const hit = w.gaokao_hit_ln ? `<b style="color:#993C1D;">${w.gaokao_hit_ln}</b>` : '<span class="muted">—</span>';
    return `<tr style="border-bottom:1px solid #ece9e0;">
      <td style="padding:6px 8px;font-weight:600;">${w.word}</td>
      <td style="padding:6px 8px;color:#444;">${w.gloss || '<span class="muted">(无释义)</span>'} ${srcBadge(w.gloss_source)}</td>
      <td style="padding:6px 8px;"><span style="color:${sc};font-size:12px;">${stage}</span></td>
      <td style="padding:6px 8px;font-size:12px;color:#888;">${w.curriculum_level || "—"}</td>
      <td style="padding:6px 8px;text-align:center;font-size:12px;">${hit}</td></tr>`;
  }

  function render(rows) {
    const el = G.$("#dict-list");
    G.$("#dict-n").textContent = `${rows.length} 词` + (rows.length >= 300 ? " (前300, 缩小前缀)" : "");
    if (!rows.length) { el.innerHTML = '<p class="muted" style="padding:16px;">无匹配词 — 试试其它前缀</p>'; return; }
    el.innerHTML = `<table style="width:100%;border-collapse:collapse;font-size:14px;">
      <thead><tr style="position:sticky;top:0;background:#faf9f5;text-align:left;border-bottom:2px solid #d8d6cd;">
        <th style="padding:6px 8px;">词</th><th style="padding:6px 8px;">释义 · 源</th><th style="padding:6px 8px;">阶段</th><th style="padding:6px 8px;">课标级</th><th style="padding:6px 8px;text-align:center;">辽宁高考命中</th></tr></thead>
      <tbody>${rows.map(row).join("")}</tbody></table>`;
  }

  async function load() {
    const q = (G.$("#dict-q").value || "").trim();
    const stage = G.$("#dict-stage").value;
    const exam = G.$("#dict-exam").checked;
    const qs = [];
    if (q) qs.push("prefix=" + encodeURIComponent(q));
    if (stage) qs.push("stage=" + encodeURIComponent(stage));
    if (exam) qs.push("source=exam");
    const data = await fetchJSON("/api/exam_dictionary?" + qs.join("&")).catch(() => ({ rows: [] }));
    const tot = G.$("#dict-total");                       // 词典总词数 = service 返回 total, 非写死(no-hardcode)
    if (tot && data.total != null) tot.textContent = Number(data.total).toLocaleString();
    render(Array.isArray(data) ? data : (data.rows || data.words || []));
  }

  registerTab("dict", async () => {
    G.$("#content").innerHTML = shell();
    let t = null;
    G.$("#dict-q").oninput = () => { clearTimeout(t); t = setTimeout(load, 220); };
    G.$("#dict-stage").onchange = load;
    G.$("#dict-exam").onchange = load;
    await load();
  });
})();
