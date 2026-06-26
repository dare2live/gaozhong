/* 单元备课 — 按 unit 看 词汇画像/语法/同主题真题 (教研室#7: 从 legacy /teacher#lesson 收敛进主SPA).
 *
 * 铁律1: 全 fetch /api/lesson_plan 的 service 单一整合点(词/语法/主题考点/对齐/趋势诚实), 前端只渲染不重算。
 * 改进(vs legacy): 词/考点走 GZ.conceptLink → 点弹 4路追溯浮窗(复用#2-4); 打印复用#5。
 */
(function () {
  const G = window.GZ;
  if (!G || !G.registerTab) return;
  const { $, fetchJSON, conceptLink, tagChip, registerTab } = G;

  function shell() {
    return `
<h2 style="margin:0 0 2px;">备课 · 单元备课 <button id="lp-print" class="bk-export" title="打印本单元备课">🖶 打印</button></h2>
<p class="muted" style="margin:0 0 12px;font-size:13px;">选 unit 看 词汇画像(越纲率)/语法+真题溯源/同主题高考真题 · service 单一整合点 · 词与考点可点弹 4 路追溯浮窗</p>
<div style="display:flex;gap:8px;align-items:center;margin-bottom:12px;flex-wrap:wrap;">
  <label style="font-size:13px;color:#666;">单元 <select id="lp-unit" style="padding:6px 8px;min-width:360px;border:1px solid #d8d6cd;border-radius:6px;font-size:13px;"></select></label>
</div>
<div id="lp-body"><p class="muted">载入单元列表…</p></div>`;
  }

  async function renderLesson(uid) {
    const body = $("#lp-body");
    body.innerHTML = `<p class="muted">载入备课…</p>`;
    const lp = await fetchJSON(`/api/lesson_plan?unit=${encodeURIComponent(uid)}`).catch(e => ({ error: String(e) }));
    if (lp.error || !lp.unit_id) { body.innerHTML = `<p class="muted">加载失败: ${lp.error || "无数据"}</p>`; return; }
    const words = lp.words || [], grammar = lp.grammar || [], rex = lp.related_exams || [];
    const al = lp.alignment_summary || {}, th = lp.trend_honesty || {}, vp = lp.vocab_profile || {};
    const pr = lp.page_range || [];
    // 词 → conceptLink (点弹浮窗: 教学元数据#4 + 真题#2); 真超纲辽宁考过标红点
    const wChip = w => conceptLink(`word:${w.word}`, `${w.word}${w.exam_freq_count ? "·" + w.exam_freq_count + "次" : ""}${w.syllabus_category === "真超纲·辽宁考过" ? " ⭑" : ""}`);
    const gChip = g => tagChip(`${g.label} · ${(g.recent_exam_trace || []).length}真题`, "grammar");
    body.innerHTML = `
      <p class="lp-meta" style="font-size:13px;"><strong>${lp.title || ""}</strong>${lp.theme ? " · 主题 " + lp.theme.replace("theme:", "") : " · 主题未匹配"} · p.${pr[0] ?? "-"}–${pr[1] ?? "-"}</p>
      <div class="trend-banner" style="background:#f7f7f4;border:1px solid #e6e3da;border-radius:8px;padding:6px 10px;font-size:12px;margin:6px 0;">命题趋势 (${th.province_scope || "辽宁卷"}): ${th.note || ""}${th.trend_reliable ? "" : " · <span style='color:var(--accent-ink)'>逐年斜率样本不足, 不画 slope</span>"}</div>
      <h3 style="margin:14px 0 6px;font-size:15px;">词汇 — 本单元引入 ${al.intro_total ?? words.length}, 高考考过 ${al.exam_overlap ?? "?"} (按高考频次降序)</h3>
      <p class="muted" style="font-size:12px;margin:0 0 6px;">词汇画像 (§不偏离学校 · 词形归并+高考核对): 课标内 <b>${vp.in_syllabus ?? "-"}</b> · 真超纲<b style="color:var(--accent-ink)">辽宁考过 ${vp.over_ln_tested ?? "-"}</b>(必教) · 仅外省 ${vp.over_other_tested ?? "-"} · 未考 ${vp.over_untested ?? "-"}(选学)${vp.proper_noise ? " · 专名 " + vp.proper_noise : ""} · <b>越纲率 ${vp.over_rate_pct ?? "-"}%</b></p>
      <div>${words.length ? words.map(wChip).join(" ") : "<em class='muted'>无</em>"}</div>
      <h3 style="margin:14px 0 6px;font-size:15px;">语法 (${grammar.length}) — 课标项 + 真题溯源 (教此语法, 高考这么考)</h3>
      <div>${grammar.length ? grammar.map(gChip).join(" ") : "<em class='muted'>本单元无 curated 语法点 (诚实跳过歧义)</em>"}</div>
      <h3 style="margin:14px 0 6px;font-size:15px;">同主题高考真题 (${rex.length}) — 教此单元主题, 高考这么考</h3>
      <div>${rex.length ? rex.map(e => tagChip(`${e.year} ${e.question_type} · ${e.theme_point}`, "year")).join(" ") : "<em class='muted'>无</em>"}</div>`;
  }

  registerTab("lesson", async () => {
    $("#content").innerHTML = shell();
    const rows = await fetchJSON("/api/units").catch(() => []);
    const list = Array.isArray(rows) ? rows : (rows.rows || rows.units || []);
    const sel = $("#lp-unit");
    if (!list.length) { $("#lp-body").innerHTML = '<p class="muted">无单元数据</p>'; return; }
    sel.innerHTML = list.map(r => `<option value="unit:${r.version_key}/${r.volume_key}/U${r.unit_number}">${r.version_key}/${r.volume_key}/U${r.unit_number} — ${r.title_en || ""}</option>`).join("");
    sel.onchange = () => renderLesson(sel.value);
    const pb = $("#lp-print"); if (pb) pb.onclick = () => window.print();
    await renderLesson(sel.value);
  });
})();
