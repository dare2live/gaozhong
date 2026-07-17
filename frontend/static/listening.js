/* 基础库 · 听力讲解 — 文字稿锚定的干扰项/易忽略点/应对技巧.
 * 数据: /api/listening/* (teaching_aid 单一计算点, 前端禁重算).
 * 音频诚实: 第三方核验档, 非 NEEA 官方原声.
 */
(function () {
  const { registerTab, fetchSafe, isErr, errorBox, pageHead, audioPlayer } = window.GZ;
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => (
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  ));

  const SEC_LABEL = { short: "短对话 1–5", long: "长对话/独白 6–20", unknown: "未分层" };

  function _audioUrl(audioId) {
    if (!audioId) return "";
    const m = String(audioId).match(/^(\d{4})\/listening\/(.+?)(?:\.mp3)?$/);
    if (!m) return "";
    return `/api/listening/file?year=${m[1]}&id=${encodeURIComponent(m[2])}`;
  }

  function _aidHTML(aid) {
    if (!aid) {
      return `<p class="kb-dim">本题暂无讲解辅助（仅 2021–2025 逐题有稿）。</p>`;
    }
    const traps = (aid.distractors || []).map(d => {
      const cue = d.cue_in_transcript
        ? `<div class="lt-cue">原文诱饵句: <em>${esc(d.cue_in_transcript)}</em></div>`
        : `<div class="lt-cue kb-dim">无字面诱饵句（语义场/概括干扰）</div>`;
      return `<li class="lt-trap">
        <strong>${esc(d.option)}. ${esc(d.text)}</strong>
        <span class="lt-badge">${esc(d.trap)}</span>
        <p>${esc(d.why_wrong)}</p>${cue}
      </li>`;
    }).join("");
    const miss = (aid.easy_to_miss || []).map(x => `<li>${esc(x)}</li>`).join("");
    const tech = (aid.technique || []).map(x => `<li>${esc(x)}</li>`).join("");
    const bots = (aid.bottleneck || []).map(b => `<span class="lt-badge">${esc(b)}</span>`).join(" ");
    const support = aid.answer_support || {};
    return `<div class="lt-aid">
      <div class="lt-meta">
        <span class="lt-badge">${esc(SEC_LABEL[aid.section] || aid.section)}</span>
        <span class="lt-badge">${esc(aid.skill)}</span>
        ${bots}
      </div>
      <section class="lt-block">
        <h4>答案怎么来的</h4>
        <p><strong>${esc(aid.answer)}. ${esc(aid.answer_text)}</strong>
          · ${esc(support.kind === "paraphrase" ? "改写对应" : "字面定位")}</p>
        <p class="kb-dim">${esc(support.note || "")}</p>
        ${support.transcript_span ? `<blockquote class="lt-span">${esc(support.transcript_span)}</blockquote>` : ""}
      </section>
      <section class="lt-block">
        <h4>干扰项拆解</h4>
        <ul class="lt-traps">${traps || "<li class='kb-dim'>无</li>"}</ul>
      </section>
      <section class="lt-block">
        <h4>容易忽略</h4>
        <ul>${miss || "<li class='kb-dim'>无</li>"}</ul>
      </section>
      <section class="lt-block">
        <h4>本题怎么应对</h4>
        <p>${esc(aid.how_to || "")}</p>
        <ul>${tech}</ul>
      </section>
      <p class="kb-dim">provenance=${esc(aid.provenance)} · ${esc(aid.review_status || "")}</p>
    </div>`;
  }

  function _renderDetail(d) {
    const panel = document.querySelector("#lt-detail");
    if (!panel) return;
    if (isErr(d) || d.error) {
      panel.innerHTML = errorBox({ title: "详情失败", msg: d.error || "未知错误" });
      return;
    }
    const src = _audioUrl(d.audio_id);
    panel.innerHTML = `
      <div class="lt-detail-h">
        <h3>${esc(d.origin_ref || "")}</h3>
        <p class="kb-dim">${esc(d.audio_note || "")}</p>
      </div>
      ${audioPlayer(src, d.audio_duration || 0)}
      <details class="lt-stem" open><summary>题干</summary><pre class="lt-pre">${esc(d.stem)}</pre></details>
      <details class="lt-tr" open><summary>文字稿</summary><pre class="gz-transcript lt-pre">${esc(d.transcript)}</pre></details>
      ${_aidHTML(d.teaching_aid)}
    `;
  }

  function _layerCards(summary) {
    const bySkill = Object.entries(summary.by_skill || {}).slice(0, 8)
      .map(([k, n]) => `<span class="tk-tchip">${esc(k)} <b>${n}</b></span>`).join("");
    const bySec = Object.entries(summary.by_section || {})
      .map(([k, n]) => `<span class="tk-tchip">${esc(SEC_LABEL[k] || k)} <b>${n}</b></span>`).join("");
    return `
      <section class="bk-card">
        <div class="bk-h"><span>听力卡点分层（可教规律）</span><span class="bk-src">/api/listening/teaching_summary</span></div>
        <ol class="lt-layers">
          <li><strong>短对话</strong>：容错小，卡在改写瞬时对齐与旁支诱饵。</li>
          <li><strong>长对话/独白</strong>：信息过载，卡在「一题一锚点」定位。</li>
          <li><strong>干扰项</strong>：原文提过≠答案；数字/关系题默认有邻近诱饵。</li>
        </ol>
        <div class="tk-types" style="margin-top:8px">${bySec} ${bySkill}</div>
        <p class="kb-dim" style="margin:8px 0 0">${esc(summary.honesty || "")}</p>
      </section>`;
  }

  registerTab("listening", async () => {
    const C = document.querySelector("#content");
    C.innerHTML = '<div class="loading-state"><span class="ls-dot"></span>载入听力讲解…</div>';
    const [sumPack, list] = await Promise.all([
      fetchSafe("/api/listening/teaching_summary"),
      fetchSafe("/api/listening/list"),
    ]);
    if (isErr(sumPack) || isErr(list)) {
      C.innerHTML = errorBox({ title: "听力讲解加载失败", msg: "后端未就绪或讲解 jsonl 未生成。" });
      return;
    }
    const summary = sumPack.summary || {};
    const years = [...new Set((list.questions || []).map(q => q.year).filter(Boolean))].sort((a, b) => b - a);
    const yearOpts = ['<option value="">全部年份</option>']
      .concat(years.map(y => `<option value="${y}">${y}</option>`)).join("");
    const qs = (list.questions || []).filter(q => q.has_teaching_aid);

    function fillQuestions(year) {
      const filtered = qs.filter(q => !year || String(q.year) === String(year));
      return filtered.map(q => {
        const label = `${q.year || "?"} Q${q.q || "?"} · ${q.skill || ""} · ${q.stem_preview || ""}`;
        return `<option value="${q.qb_id}">${esc(label)}</option>`;
      }).join("");
    }

    C.innerHTML = `<section class="scaffold lt-page">
      ${pageHead("基础库 · 听力讲解", "文字稿上的干扰项与应对",
        `已覆盖讲解 ${summary.n || 0} 题（辽宁新高考 II 2021–2025）。先听再对稿：标出诱饵、易忽略句、本题技巧。`)}
      ${_layerCards(summary)}
      <section class="bk-card">
        <div class="bk-h"><span>逐题讲解</span><span class="bk-src">/api/listening/detail</span></div>
        <div class="tk-filter" style="gap:12px;display:flex;flex-wrap:wrap;align-items:center">
          <label>年份 <select id="lt-year">${yearOpts}</select></label>
          <label style="flex:1;min-width:240px">题目
            <select id="lt-q" style="width:100%">${fillQuestions("")}</select>
          </label>
        </div>
        <div id="lt-detail" class="lt-detail"><p class="kb-dim">选择题目查看文字稿讲解。</p></div>
      </section>
    </section>`;

    const yearSel = document.querySelector("#lt-year");
    const qSel = document.querySelector("#lt-q");

    async function load() {
      const id = qSel.value;
      if (!id) return;
      const panel = document.querySelector("#lt-detail");
      panel.innerHTML = '<div class="loading-state"><span class="ls-dot"></span>载入…</div>';
      const d = await fetchSafe(`/api/listening/detail?id=${encodeURIComponent(id)}`);
      _renderDetail(d);
    }
    yearSel.onchange = () => { qSel.innerHTML = fillQuestions(yearSel.value); load(); };
    qSel.onchange = load;
    if (qSel.value) load();
  });
})();
