// gaozhong frontend (vanilla JS, no framework). 拉 stdlib-http API + 渲染.

const $ = (sel) => document.querySelector(sel);
const fetchJSON = (path) => fetch(path).then((r) => r.json());

async function loadStats() {
  const s = await fetchJSON("/api/stats");
  const v = s.vocab_by_level || {};
  const c = s.cities_by_publisher || {};
  const ep = s.exam_by_province || {};
  const as = s.audit_by_severity || {};
  $("#stats-body").innerHTML = `
    <table>
      <tr><th>课标词汇表</th><td><b>${s.cefr_vocab}</b> 词 (义教 ${v["义教"]||0} / 必修★ ${v["必修"]||0} / 选必★★ ${v["选必"]||0})</td></tr>
      <tr><th>课标语法项目</th><td>${s.grammar_items} 行 (层级 depth 1-4)</td></tr>
      <tr><th>主题语境</th><td>${s.theme_contexts} (3 大语境 + 10 主题群)</td></tr>
      <tr><th>辽宁允许版本 (英语)</th><td>${s.liaoning_allowed_publishers} 个出版社</td></tr>
      <tr><th>辽宁 14 地市使用</th><td>${s.liaoning_city_textbook_choice} 城市 — 外研版 ${c["外研版"]||0} / 人教版 ${c["人教版"]||0}</td></tr>
      <tr><th>已入仓教材 PDF</th><td>${s.textbooks} 册</td></tr>
      <tr><th>真题镜像</th><td>${s.exam_questions} 题 — 辽宁推断 ${Object.entries(ep).filter(([k])=>k.includes("辽宁")).reduce((a,[,v])=>a+v,0)} / 未知 ${ep["未知"]||0}</td></tr>
      <tr><th>知识图谱</th><td>${s.nodes} nodes · ${s.edges} edges</td></tr>
      <tr><th>审计</th><td><b style="color:#2a9d8f">${as["OK"]||0} OK</b> · ${as["WARN"]||0} WARN · <b style="color:#e76f51">${as["FAIL"]||0} FAIL</b></td></tr>
      <tr><th>文件 manifest</th><td>${s.file_manifest} 条 (含 sha256)</td></tr>
    </table>`;
}

async function loadAudit() {
  const rows = await fetchJSON("/api/audit/findings");
  $("#audit-body tbody").innerHTML = rows.map((r) => `
    <tr style="background:${r.severity==='FAIL'?'#fde2e1':r.severity==='WARN'?'#fff7d6':''}">
      <td>${r.audit_kind}</td>
      <td><b style="color:${r.severity==='FAIL'?'#c1272d':r.severity==='WARN'?'#b8860b':'#2a9d8f'}">${r.severity}</b></td>
      <td>${r.target||''}</td>
      <td>${r.expected||''}</td>
      <td>${r.actual||''}</td>
      <td style="font-size:11px;color:#666">${r.note||''}</td>
    </tr>`).join("");
}

async function loadGraph() {
  const s = await fetchJSON("/api/graph/stats");
  const rows = (obj) => Object.entries(obj).sort((a,b)=>b[1]-a[1])
    .map(([k,v])=>`<tr><td>${k}</td><td>${v}</td></tr>`).join("");
  $("#graph-body").innerHTML = `
    <table style="float:left;width:48%">
      <thead><tr><th>node_type</th><th>count</th></tr></thead>
      <tbody>${rows(s.nodes)}</tbody>
      <tfoot><tr><td><b>total</b></td><td><b>${s.total_nodes}</b></td></tr></tfoot>
    </table>
    <table style="float:right;width:48%">
      <thead><tr><th>relation</th><th>count</th></tr></thead>
      <tbody>${rows(s.edges)}</tbody>
      <tfoot><tr><td><b>total</b></td><td><b>${s.total_edges}</b></td></tr></tfoot>
    </table>
    <div style="clear:both"></div>`;
}

async function loadExam() {
  const prov = $("#exam-prov").value;
  const qtype = $("#exam-qtype").value;
  const year = $("#exam-year").value;
  const qs = new URLSearchParams();
  if (prov) qs.set("province", prov);
  if (qtype) qs.set("type", qtype);
  if (year) qs.set("year", year);
  qs.set("limit", "30");
  const rows = await fetchJSON("/api/exam_questions?" + qs);
  if (!rows.length) {
    $("#exam-body").innerHTML = "<em>无匹配</em>";
    return;
  }
  $("#exam-body").innerHTML = rows.map((r) => `
    <details style="margin-bottom:6px;border:1px solid #eee;padding:6px;border-radius:4px">
      <summary><b>${r.year}</b> · ${r.question_type} · <code>${r.question_id}</code> · ${r.province}</summary>
      <pre style="white-space:pre-wrap;font-size:12px;margin:6px 0 0">${r.preview}</pre>
    </details>`).join("");
}

async function loadCities() {
  const rows = await fetchJSON("/api/liaoning/city_choice");
  $("#cities-src").textContent = (rows[0]||{}).source || "";
  $("#cities-body").innerHTML = rows.map((r) => `
    <div class="city ${r.publisher_short === "外研版" ? "waiyan" : "renjiao"}">
      <div><b>${r.city}</b></div>
      <div class="pub">${r.publisher_short}</div>
    </div>`).join("");
}

async function loadPublishers() {
  const rows = await fetchJSON("/api/liaoning/allowed_publishers");
  $("#publishers-body tbody").innerHTML = rows.map((r) => `
    <tr>
      <td>${r.chief_editor || ""}</td>
      <td>${r.publisher}</td>
      <td>${r.book_title}</td>
      <td>${(r.volumes || []).length} 册</td>
    </tr>`).join("");
}

async function loadTextbooks() {
  const rows = await fetchJSON("/api/textbooks");
  $("#textbooks-body tbody").innerHTML = rows.map((r) => `
    <tr>
      <td>${r.publisher_label}</td>
      <td>${r.volume_key}</td>
      <td>${r.pdf_pages || "-"}</td>
      <td><code>${r.pdf_sha256.slice(0, 12)}…</code></td>
      <td><a href="/api/textbooks/${r.version_key}/${r.volume_key}/pdf" target="_blank">打开 PDF</a></td>
    </tr>`).join("");
}

async function loadHeatmap() {
  const d = await fetchJSON("/api/heatmap/vocab");
  const STATUSES = ["core", "standard", "HV_extra", "LV_extra"];
  const total = STATUSES.reduce((a, s) => a + (d.totals[s] || 0), 0);
  // legend + totals
  const legendHtml = `
    <div class="heat-totals">
      <b>${total.toLocaleString()}</b> 词分 4 象限 (基于课标 ∩ 高考 vs 教材引入)
    </div>
    <div class="heat-legend">${STATUSES.map(s => `
      <span><i style="background:${d.legend[s].color}"></i>
        <b>${s}</b> ${d.totals[s]||0} — ${d.legend[s].hint}</span>`).join("")}
    </div>`;
  // grid: header row + per-letter rows
  let html = legendHtml + `<div class="heat-grid">
    <div class="head"></div>
    ${STATUSES.map(s => `<div class="head" style="background:${d.legend[s].color};color:white">${s}</div>`).join("")}`;
  // compute max for sizing
  let max = 0;
  for (const L of d.letters)
    for (const s of STATUSES)
      max = Math.max(max, (d.cells[L]||{})[s]||0);
  for (const L of d.letters) {
    html += `<div class="letter">${L}</div>`;
    for (const s of STATUSES) {
      const n = (d.cells[L]||{})[s] || 0;
      const intensity = max > 0 ? (n / max) : 0;
      const bg = n === 0 ? "" : d.legend[s].color;
      const alpha = n === 0 ? 1 : 0.3 + 0.7 * intensity;
      html += `<div class="cell ${n===0?'empty':''}"
                    style="background:${bg};opacity:${alpha}"
                    data-status="${s}" data-letter="${L}">${n||"·"}</div>`;
    }
  }
  html += `</div>`;
  $("#heatmap-body").innerHTML = html;
  // click drilldown
  document.querySelectorAll("#heatmap-body .cell").forEach((el) => {
    el.addEventListener("click", async () => {
      const letter = el.dataset.letter, status = el.dataset.status;
      if ((d.cells[letter]||{})[status] === undefined) return;
      const words = await fetchJSON(`/api/heatmap/words_by_status?status=${status}&letter=${letter}`);
      const dd = $("#heat-drilldown");
      dd.style.display = "block";
      dd.innerHTML = `<b>[${status}] · ${letter}</b> · ${words.length} words<br>` +
        words.map(w => `<span class="word" title="${(w.attrs||'').replace(/"/g, '&quot;')}">${w.word}</span>`).join("");
    });
  });
}

async function loadUnits() {
  const rows = await fetchJSON("/api/units");
  $("#units-body tbody").innerHTML = rows.map((r) => {
    const bgColor = r.extract_method === 'outline' ? '' :
                    r.extract_method === 'regex_min' ? 'background:#fffaf0' :
                    'background:#fde2e1';
    return `<tr style="${bgColor}">
      <td>${r.version_key}</td>
      <td>${r.volume_key}</td>
      <td>${r.unit_number}</td>
      <td>${r.title_en}</td>
      <td>p${r.page_start}–${r.page_end}</td>
      <td><code style="font-size:11px">${r.extract_method}</code></td>
    </tr>`;
  }).join("");
}

async function loadThemes() {
  const rows = await fetchJSON("/api/theme_contexts");
  const byL1 = {};
  for (const r of rows) {
    if (!byL1[r.level1]) byL1[r.level1] = [];
    if (r.level2) byL1[r.level1].push(r.level2);
  }
  $("#themes-body").innerHTML = Object.entries(byL1).map(([l1, l2s]) => `
    <div class="theme-l1">${l1}</div>
    ${l2s.map((l) => `<div class="theme-l2">· ${l}</div>`).join("")}
  `).join("");
}

async function loadGrammar() {
  const rows = await fetchJSON("/api/grammar_items");
  $("#grammar-body tbody").innerHTML = rows.map((r) => `
    <tr>
      <td>${r.grammar_item_id}</td>
      <td>${r.category || ""}</td>
      <td>${r.label}</td>
      <td>${r.cefr_level}</td>
    </tr>`).join("");
}

async function loadVocab() {
  const level = $("#vocab-level").value;
  const prefix = $("#vocab-prefix").value;
  const limit = $("#vocab-limit").value;
  const qs = new URLSearchParams();
  if (level) qs.set("level", level);
  if (prefix) qs.set("prefix", prefix);
  if (limit) qs.set("limit", limit);
  const rows = await fetchJSON("/api/cefr_vocab?" + qs);
  if (!rows.length) {
    $("#vocab-body").innerHTML = `<em>无匹配 (${qs})</em>`;
    return;
  }
  $("#vocab-body").innerHTML = rows.map((r) => `
    <span class="vocab-item l-${r.cefr_level}">
      ${r.word}<span class="lvl">${r.cefr_level}</span>
    </span>`).join("");
}

document.addEventListener("DOMContentLoaded", () => {
  loadStats().catch(console.error);
  loadCities().catch(console.error);
  loadPublishers().catch(console.error);
  loadTextbooks().catch(console.error);
  loadThemes().catch(console.error);
  loadGrammar().catch(console.error);
  loadVocab().catch(console.error);
  loadAudit().catch(console.error);
  loadGraph().catch(console.error);
  loadExam().catch(console.error);
  loadUnits().catch(console.error);
  loadHeatmap().catch(console.error);
  $("#vocab-go").addEventListener("click", () => loadVocab().catch(console.error));
  $("#vocab-prefix").addEventListener("keydown", (e) => { if (e.key === "Enter") loadVocab(); });
  $("#exam-go").addEventListener("click", () => loadExam().catch(console.error));
});
