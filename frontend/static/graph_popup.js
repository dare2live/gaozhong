/* 全局图谱浮窗 (用户 2026-05-24).
   任意 .gz-concept[data-id=concept_id] 点击 → 弹 modal:
     中心节点 + 1 层关联 + 真题题目节点 + 可递归点继续扩展.

   依赖: /api/graph/popup (backend/api/routes/graph_popup.py)
   挂载: app.html 末尾 <script src=...> 自动绑定全局 click.
*/
(function () {
  const { fetchJSON } = window.GZ;

  // 事件委托 — 全局监听
  document.addEventListener("click", async (ev) => {
    const a = ev.target.closest(".gz-concept[data-concept]");
    if (!a) return;
    ev.preventDefault();
    await openPopup(a.dataset.concept);
  });

  // modal 栈 — 支持"返回上一层"
  const STACK = [];

  async function openPopup(cid) {
    let modal = document.getElementById("gz-popup");
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "gz-popup";
      modal.innerHTML = `
        <div class="gz-popup-back" onclick="if(event.target===this)window._gzClosePopup()"></div>
        <div class="gz-popup-body">
          <div class="gz-popup-head">
            <span class="gz-popup-nav"></span>
            <span class="gz-popup-close" onclick="window._gzClosePopup()">✕</span>
          </div>
          <div class="gz-popup-content">载入中...</div>
        </div>`;
      document.body.appendChild(modal);
    }
    modal.classList.add("open");
    STACK.push(cid);
    await render(cid);
  }

  async function render(cid) {
    const cont = document.querySelector("#gz-popup .gz-popup-content");
    const nav  = document.querySelector("#gz-popup .gz-popup-nav");
    cont.innerHTML = `载入 ${cid} ...`;
    nav.innerHTML = STACK.length > 1
      ? `<a href="#" onclick="window._gzBack();return false">← 返回</a> · 深度 ${STACK.length}`
      : `深度 1`;
    try {
      const data = await fetchJSON("/api/graph/popup?id=" + encodeURIComponent(cid));
      if (data.error) { cont.innerHTML = `<p>${data.error}</p>`; return; }
      cont.innerHTML = renderHTML(data);
    } catch (err) {
      cont.innerHTML = `载入失败: ${err.message}`;
    }
  }

  function renderHTML(d) {
    const { center, related, questions } = d;
    // 按 type 分组 related
    const byType = {};
    for (const r of related) (byType[r.type] = byType[r.type] || []).push(r);

    let h = `<h3 class="gz-center">
      <span class="gz-type-${center.type}">[${center.type}]</span> ${center.label}
      <small style="color:#888">${center.id}</small>
    </h3>`;

    h += `<div class="gz-section">
      <div class="gz-sec-title">📚 关联拓展 (${related.length})</div>`;
    if (related.length === 0) {
      h += `<p style="color:#888">无直接关联</p>`;
    } else {
      for (const t of Object.keys(byType).sort()) {
        h += `<div class="gz-group"><strong>${t}</strong> `;
        h += byType[t].map(r =>
          `<a href="#" class="gz-concept gz-chip gz-type-${r.type}" data-concept="${r.id}"
              title="${r.relation} (${r.direction})">${r.label}</a>`
        ).join(" ");
        h += `</div>`;
      }
    }
    h += `</div>`;

    h += `<div class="gz-section">
      <div class="gz-sec-title">📝 真题命中 (${questions.length})</div>`;
    if (questions.length === 0) {
      h += `<p style="color:#888">无真题直接命中</p>`;
    } else {
      h += `<ul class="gz-qlist">`;
      for (const q of questions) {
        const yr = q.year ? ` <span class="gz-year">${q.year}</span>` : "";
        const qb = q.qb_id != null
          ? `<a href="#" class="gz-concept gz-qlink" data-concept="${q.concept_id}">#${q.qb_id}</a>`
          : `<span class="gz-qlink">${q.concept_id}</span>`;
        h += `<li>${qb} <em>[${q.question_type}]</em>${yr}<br><small>${escapeHtml(q.stem_preview)}...</small></li>`;
      }
      h += `</ul>`;
    }
    h += `</div>`;
    return h;
  }

  function escapeHtml(s) {
    return (s || "").replace(/[&<>"']/g, c => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[c]));
  }

  window._gzClosePopup = () => {
    document.getElementById("gz-popup")?.classList.remove("open");
    STACK.length = 0;
  };
  window._gzBack = async () => {
    STACK.pop(); // 当前
    const prev = STACK.pop();
    if (prev) {
      await openPopup(prev);  // 重新 push + render
    } else {
      window._gzClosePopup();
    }
  };
})();
