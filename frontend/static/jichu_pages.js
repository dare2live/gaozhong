/* 基础库子页 — 真题库 (tiku) + 课标库 (kebiao) 浏览. 北极星 Phase B.
 *
 * 复用现有 service/endpoint (铁律1 前端禁重算): 真题库读 /api/exam/liaoning_browse (province 前缀 坑7-safe),
 * 课标库读 /api/curriculum/summary + /api/theme_contexts + /api/grammar_items。每条可溯源, 数据真值。
 */
(function () {
  const { registerTab, fetchSafe, isErr, errorBox } = window.GZ;
  const esc = s => String(s == null ? "" : s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

  // ── ③-b 真题库: 辽宁卷真题按年/题型浏览, 每题溯源原卷 ──
  function _tikuQ(q) {
    return `<li class="tk-q">
      <span class="tk-qtype">${esc(q.question_type)}</span>
      <span class="tk-qprev">${esc(q.preview)}…</span>
      <span class="tk-qmeta">${q.has_answer ? '<span class="tk-ans">含答案</span>' : ""}<span class="tk-src" title="溯源原卷">${esc(q.source_file)}#${q.source_index}</span></span>
    </li>`;
  }
  function _tikuYear(year, qs) {
    return `<section class="tk-year" data-year="${year}"><h3 class="tk-year-h">${year} 年 <span class="tk-year-n">${qs.length} 题</span></h3><ul class="tk-qlist">${qs.map(_tikuQ).join("")}</ul></section>`;
  }
  registerTab("tiku", async () => {
    const C = document.querySelector("#content");
    C.innerHTML = '<div class="loading-state"><span class="ls-dot"></span>载入真题库…</div>';
    const d = await fetchSafe("/api/exam/liaoning_browse");
    if (isErr(d)) { C.innerHTML = errorBox({ title: "真题库加载失败", msg: "后端未就绪或数据未算出 — 真实错误。" }); return; }
    const typeChips = Object.entries(d.type_counts).map(([t, n]) => `<span class="tk-tchip">${esc(t)} <b>${n}</b></span>`).join("");
    const yearOpts = ['<option value="">全部年份</option>'].concat(d.years.map(y => `<option value="${y}">${y}</option>`)).join("");
    const years = Object.keys(d.by_year).sort((a, b) => b - a);
    C.innerHTML = `<section class="scaffold">
      ${pageHead("基础库 · 真题库", "历年辽宁卷真题", `${esc(d.scope)} · 共 ${d.total} 题 (2015+ 新课标 II 卷)。每题可溯源到原卷, 也是课程作业的题源。`)}
      <div class="tk-types">${typeChips}</div>
      <div class="tk-filter"><label for="tk-year">按年份</label><select id="tk-year" aria-label="按年份筛选真题">${yearOpts}</select></div>
      <div id="tk-body">${years.map(y => _tikuYear(y, d.by_year[y])).join("")}</div>
    </section>`;
    const sel = document.querySelector("#tk-year");
    if (sel) sel.onchange = () => {
      const y = sel.value;
      document.querySelectorAll(".tk-year").forEach(s => { s.style.display = (!y || s.dataset.year === y) ? "" : "none"; });
    };
  });

  // ── ③-c 课标库: 主题群 / 语法体系 / 词汇 (按学段) ──
  function _themeGroups(themes) {
    const by1 = {};
    themes.forEach(t => { (by1[t.level1] = by1[t.level1] || []).push(t.level2); });
    return Object.entries(by1).map(([l1, subs]) => {
      const items = subs.filter(Boolean).map(s => `<span class="kb-pill">${esc(s)}</span>`).join("");
      return `<div class="kb-row"><span class="kb-row-h">${esc(l1)}</span><div class="kb-pills">${items || '<span class="kb-dim">主题</span>'}</div></div>`;
    }).join("");
  }
  function _grammarTop(grammar) {
    const tops = grammar.filter(g => g.depth === 1);
    const childCount = p => grammar.filter(g => g.parent_id === p).length;
    return tops.map(g => `<div class="kb-row"><span class="kb-row-h">${esc(g.label)}</span><span class="kb-dim">${childCount(g.grammar_item_id)} 子项</span></div>`).join("")
      || '<div class="kb-dim">语法体系</div>';
  }
  registerTab("kebiao", async () => {
    const C = document.querySelector("#content");
    C.innerHTML = '<div class="loading-state"><span class="ls-dot"></span>载入课标库…</div>';
    const [sum, themes, grammar] = await Promise.all([
      fetchSafe("/api/curriculum/summary"), fetchSafe("/api/theme_contexts"), fetchSafe("/api/grammar_items"),
    ]);
    if (isErr(sum) || isErr(themes) || isErr(grammar)) { C.innerHTML = errorBox({ title: "课标库加载失败", msg: "后端未就绪。" }); return; }
    const vocab = sum.vocab_by_level || {};
    const vChips = Object.entries(vocab).map(([lv, n]) => `<span class="tk-tchip">${esc(lv)} <b>${n}</b></span>`).join("");
    C.innerHTML = `<section class="scaffold">
      ${pageHead("基础库 · 课标库", "官方课标里有什么", `${esc(sum.source)} — 主题群 ${sum.themes_total} · 语法 ${sum.grammar_total} 项 · 词汇 ${sum.vocab_total} (按学段)。高考命题与本产品课程对齐的第一手依据。`)}
      <section class="bk-card"><div class="bk-h"><span>主题语境 · 三大主题 → 子主题群</span><span class="bk-src">/api/theme_contexts</span></div><div class="kb-list">${_themeGroups(themes)}</div></section>
      <section class="bk-card"><div class="bk-h"><span>语法体系 · 课标层级</span><span class="bk-src">/api/grammar_items</span></div><div class="kb-list">${_grammarTop(grammar)}</div></section>
      <section class="bk-card"><div class="bk-h"><span>词汇 · 按学段</span><span class="bk-src">/api/curriculum/summary</span></div>
        <div class="tk-types">${vChips}</div>
        <p class="kb-dim" style="margin:8px 0 0;">逐词释义 + 辽宁高考命中标记见 <a href="#/dict">考试词典</a>。</p></section>
    </section>`;
  });
})();
