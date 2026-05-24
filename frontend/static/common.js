/*
 * gaozhong common.js — 3 个前端共享 (架构 Rule 5).
 * 用法 (在 html 末): <script src="/static/common.js"></script>
 * 提供: $, $$, fetchJSON, tagChip, mountLayout, formToQs, ...
 */

window.GZ = (function () {
  const NAV = [
    { href: "/", label: "概览" },
    { href: "/teacher", label: "教师端" },
    { href: "/student", label: "学生端" },
  ];

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return [...(root || document).querySelectorAll(sel)]; }

  async function fetchJSON(path) {
    const r = await fetch(path);
    if (!r.ok) throw new Error(`HTTP ${r.status} on ${path}`);
    return r.json();
  }

  function tagChip(text, kind) {
    const k = (kind || "").replace(/[^a-z_]/gi, "");
    return `<span class="tag-chip ${k}">${text}</span>`;
  }

  function renderTable(rows, columns) {
    // columns: [{key, label, render?}]
    const head = columns.map(c => `<th>${c.label}</th>`).join("");
    const body = rows.map(r => "<tr>" +
      columns.map(c => `<td>${c.render ? c.render(r[c.key], r) : (r[c.key] ?? "")}</td>`).join("") +
      "</tr>").join("");
    return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
  }

  function formToQs(form) {
    const fd = new FormData(form);
    const qs = new URLSearchParams();
    for (const [k, v] of fd) if (v) qs.set(k, v);
    return qs;
  }

  function mountLayout(activeHref) {
    // 在 <body> 顶部注入 header + nav, 保持 3 页一致
    const header = document.createElement("header");
    header.innerHTML = `
      <h1>沈阳/辽宁高中英语 ·
        <span class="nav-inline">
          ${NAV.map(n => `<a href="${n.href}" class="${n.href === activeHref ? 'active' : ''}">${n.label}</a>`).join(" · ")}
        </span>
      </h1>`;
    document.body.insertBefore(header, document.body.firstChild);
  }

  function colorByTagKind(kind) {
    const map = {
      word: "#0a4d75", grammar: "#1c5d99", year: "#f4a261",
      question_type: "#c1272d", difficulty: "#2a9d8f",
      unit: "#7aa6c2", theme: "#2a9d8f",
    };
    return map[kind] || "#888";
  }

  // expose
  return {
    $, $$, fetchJSON, tagChip, renderTable, formToQs,
    mountLayout, colorByTagKind, NAV,
  };
})();
