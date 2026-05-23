// gaozhong frontend (vanilla JS, no framework). 拉 stdlib-http API + 渲染.

const $ = (sel) => document.querySelector(sel);
const fetchJSON = (path) => fetch(path).then((r) => r.json());

async function loadStats() {
  const s = await fetchJSON("/api/stats");
  const v = s.vocab_by_level || {};
  const c = s.cities_by_publisher || {};
  $("#stats-body").innerHTML = `
    <table>
      <tr><th>课标词汇表</th><td><b>${s.cefr_vocab}</b> 词 (义教 ${v["义教"]||0} / 必修★ ${v["必修"]||0} / 选必★★ ${v["选必"]||0})</td></tr>
      <tr><th>课标语法项目</th><td>${s.grammar_items} 顶级类目 (MVP)</td></tr>
      <tr><th>主题语境</th><td>${s.theme_contexts} (3 大语境 + 10 主题群)</td></tr>
      <tr><th>辽宁允许版本 (英语)</th><td>${s.liaoning_allowed_publishers} 个出版社</td></tr>
      <tr><th>辽宁 14 地市使用</th><td>${s.liaoning_city_textbook_choice} 城市 — 外研版 ${c["外研版"]||0} / 人教版 ${c["人教版"]||0}</td></tr>
      <tr><th>已入仓教材 PDF</th><td>${s.textbooks} 册</td></tr>
      <tr><th>文件 manifest</th><td>${s.file_manifest} 条 (含 sha256)</td></tr>
    </table>`;
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
  $("#vocab-go").addEventListener("click", () => loadVocab().catch(console.error));
  $("#vocab-prefix").addEventListener("keydown", (e) => { if (e.key === "Enter") loadVocab(); });
});
