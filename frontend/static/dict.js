/* 考试词典金矿 — exam_vocabulary(4186词) 接前端 (交付收口 B1).
 *
 * 铁律1: 全 fetch /api/exam_dictionary 的 service 单算点产物, 前端只渲染不重算。
 * 诚实: 释义带 gloss_source provenance 徽章(教材/中考/COCA兜底); 辽宁高考命中=真题边真值非估算。
 */
(function () {
  const G = window.GZ;
  if (!G || !G.registerTab) return;
  const { fetchJSON, registerTab } = G;

  // gloss_source provenance 徽章 (释义可信度分层, 不混同) — 单一来源 category-config.js GZ_CAT.glossSource
  // (#1 修: 旧本地 SRC 表 key=textbook/zhongkao 与实际 gloss_source renjiao/waiyan/中考词汇表 失配 → 85%行渲裸代码)
  const SRC = (window.GZ_CAT && window.GZ_CAT.glossSource) || {
    renjiao: ["教材", "#1D9E75"], waiyan: ["教材", "#1D9E75"], hujiao: ["教材", "#1D9E75"],
    "中考": ["中考", "#378ADD"], exam: ["真题", "#185FA5"],
    variant: ["变体继承", "#9C7A3C"], coca: ["COCA兜底", "#B4B2A9"],
  };
  const STAGE_C = (window.GZ_CAT && window.GZ_CAT.stage) || {};   // 学段色单一来源 category-config.js (防 k12/dict 漂移)

  function srcBadge(s) {
    const k = (s || "").toLowerCase();
    const hit = Object.keys(SRC).find(x => k.includes(x.toLowerCase()));
    const [t, c] = hit ? SRC[hit] : [s || "—", "#B4B2A9"];
    return `<span style="font-size:10px;padding:1px 6px;border-radius:8px;background:${c}22;color:${c};white-space:nowrap;">${t}</span>`;
  }

  function shell() {
    return `
<h2 style="margin:0 0 2px;">考试词典 · 金矿</h2>
<p class="muted" style="margin:0 0 12px;font-size:13px;">exam_vocabulary <span id="dict-total">…</span> 词 (课标∪教材真超纲) · 释义三源溯源(教材→中考→COCA兜底) · 辽宁高考命中=真题边真值 · <span style="border-bottom:1px dashed #b9b6ab;">点词</span>查跨阶段多义 · service 单算点</p>
<div style="display:flex;gap:8px;align-items:center;margin-bottom:10px;flex-wrap:wrap;">
  <input id="dict-q" placeholder="输入词首字母前缀检索…" style="flex:1;min-width:180px;padding:7px 10px;border:1px solid #d8d6cd;border-radius:6px;font-size:14px;">
  <select id="dict-stage" style="padding:7px;border:1px solid #d8d6cd;border-radius:6px;">
    <option value="">全部阶段</option><option>初中</option><option>高中必修</option><option>高中选修</option>
  </select>
  <label style="font-size:13px;color:#666;"><input type="checkbox" id="dict-exam"> 仅辽宁高考命中</label>
  <button id="dict-export" class="bk-export" title="导出当前筛选词表 CSV (备课发学生)">⬇ CSV</button>
  <span id="dict-n" class="muted" style="font-size:12px;"></span>
</div>
<div id="dict-list" style="max-height:62vh;overflow:auto;"></div>`;
  }

  // #10: 跨阶段多义详情渲染 (word_sense; provenance=dual_model → 必标方向性参考非真值, 守 J4 死亡红线)
  function _renderSenseDetail(d) {
    if (!d || !d.cross_stage_multi) {
      return '<div class="muted" style="font-size:12px;padding:6px 12px;">该词无跨阶段多义记录（单义, 或未判定为跨阶段真多义）</div>';
    }
    const hs = d.stages.find(s => s.stage === "高中") || {};
    const newset = new Set(hs.new_senses || []);
    const stageRow = (s) => {
      const sc = STAGE_C[s.stage] || "#888";
      const items = (s.senses || []).map(x =>
        (s.stage === "高中" && newset.has(x))
          ? `<span style="background:#FBEFD6;color:#8A5A00;padding:1px 6px;border-radius:4px;">${x}<span style="font-size:10px;margin-left:2px;">新增</span></span>`
          : `<span style="padding:1px 4px;">${x}</span>`).join("、");
      return `<div style="margin:3px 0;font-size:13px;"><span style="color:${sc};font-weight:600;">${s.stage}</span> ${items || '<span class="muted">—</span>'}</div>`;
    };
    return `<div style="padding:8px 12px;background:#FFFDF8;border-left:3px solid #D8A93B;">
      <div style="font-size:11px;color:#8A5A00;margin-bottom:5px;">⚠ 跨阶段多义 · 方向性参考（双模型对抗推断 LLM 层, 非确定真值; 确定释义以上方词条释义为准）</div>
      ${d.stages.map(stageRow).join("")}</div>`;
  }

  function row(w) {
    const stage = w.stage || "—", sc = STAGE_C[stage] || "#888";
    const hit = w.gaokao_hit_ln ? `<b style="color:#993C1D;">${w.gaokao_hit_ln}</b>` : '<span class="muted">—</span>';
    return `<tr style="border-bottom:1px solid #ece9e0;">
      <td style="padding:6px 8px;font-weight:600;"><span class="dict-word" data-word="${w.word}" title="查跨阶段多义" style="cursor:pointer;border-bottom:1px dashed #b9b6ab;">${w.word}</span></td>
      <td style="padding:6px 8px;color:#444;">${w.gloss || '<span class="muted">(无释义)</span>'} ${srcBadge(w.gloss_source)}</td>
      <td style="padding:6px 8px;"><span style="color:${sc};font-size:12px;">${stage}</span></td>
      <td style="padding:6px 8px;font-size:12px;color:#888;">${w.curriculum_level || "—"}</td>
      <td style="padding:6px 8px;text-align:center;font-size:12px;">${hit}</td></tr>`;
  }

  let lastRows = [];   // #5: 当前筛选结果, 供导出 CSV

  function render(rows) {
    lastRows = rows;
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
    // #10: 点词展开跨阶段多义 (事件委托挂容器, survive render 重绘子节点); 再点收起
    G.$("#dict-list").addEventListener("click", async (e) => {
      const wel = e.target.closest(".dict-word");
      if (!wel) return;
      const tr = wel.closest("tr");
      const nx = tr.nextElementSibling;
      if (nx && nx.classList.contains("dict-expand")) { nx.remove(); return; }
      const exp = document.createElement("tr");
      exp.className = "dict-expand";
      exp.innerHTML = '<td colspan="5" style="padding:0;"><div class="muted" style="padding:6px 12px;font-size:12px;">载入义项…</div></td>';
      tr.after(exp);
      const d = await fetchJSON("/api/word_detail?word=" + encodeURIComponent(wel.getAttribute("data-word"))).catch(() => null);
      exp.querySelector("td").innerHTML = _renderSenseDetail(d);
    });
    G.$("#dict-q").oninput = () => { clearTimeout(t); t = setTimeout(load, 220); };
    G.$("#dict-stage").onchange = load;
    G.$("#dict-exam").onchange = load;
    // #5: 导出当前筛选词表 CSV (词/释义/源/阶段/课标级/辽宁命中), 教研员备课发学生
    G.$("#dict-export").onclick = () => {
      if (!lastRows.length) return;
      G.exportCSV(lastRows, [
        { key: "word", label: "词" }, { key: "gloss", label: "释义" },
        { key: "gloss_source", label: "释义源" }, { key: "stage", label: "阶段" },
        { key: "curriculum_level", label: "课标级" }, { key: "gaokao_hit_ln", label: "辽宁高考命中" },
      ], `辽宁考试词典_${lastRows.length}词.csv`);
    };
    await load();
  });
})();
