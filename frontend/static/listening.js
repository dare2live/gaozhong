/* 基础库 · 听力讲解 — 按实测分布结论先行, 再筛题看稿.
 * 数据: /api/listening/* (teaching_aid 单一计算点, 前端禁重算).
 */
(function () {
  const { registerTab, fetchSafe, isErr, errorBox, pageHead, audioPlayer } = window.GZ;
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => (
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  ));

  const SEC_LABEL = { short: "短对话 1–5", long: "长材料 6–20", unknown: "未分层" };
  const TRAP_HINT = {
    "原文提及但非答案": "听见过 ≠ 选得上",
    "语义场替换/概括干扰": "同场景换说法",
    "数字/时间邻近干扰": "听比较关系",
    "身份/关系干扰": "靠细节推断身份",
  };

  let _state = { qs: [], filtered: [], activeId: null, filters: { year: "", section: "", skill: "" } };

  function _audioUrl(audioId) {
    if (!audioId) return "";
    const m = String(audioId).match(/^(\d{4})\/listening\/(.+?)(?:\.mp3)?$/);
    if (!m) return "";
    return `/api/listening/file?year=${m[1]}&id=${encodeURIComponent(m[2])}`;
  }

  function _bar(pct, label) {
    const w = Math.max(2, Math.min(100, pct || 0));
    return `<div class="lt-bar" title="${esc(label)} ${pct}%">
      <span class="lt-bar-fill" style="width:${w}%"></span>
      <span class="lt-bar-lab">${esc(label)} <b>${pct}%</b></span>
    </div>`;
  }

  function _hero(summary) {
    const n = summary.n || 0;
    const shortN = (summary.by_section || {}).short || 0;
    const longN = (summary.by_section || {}).long || 0;
    const traps = Object.entries(summary.by_trap || {});
    const trapRows = traps.map(([k, v]) => {
      const hint = TRAP_HINT[k] || "";
      return `<div class="lt-stat">
        <div class="lt-stat-n">${v}</div>
        <div class="lt-stat-l">${esc(k)}</div>
        <div class="lt-stat-h">${esc(hint)}</div>
      </div>`;
    }).join("");
    const skills = Object.entries(summary.by_skill || {});
    const skillBars = skills.slice(0, 6).map(([k, v]) =>
      _bar(n ? Math.round(100 * v / n) : 0, k)
    ).join("");
    return `
      <section class="bk-card lt-hero">
        <div class="bk-h"><span>这套听力实际在考什么</span><span class="bk-src">${n} 题 · 2021–2025</span></div>
        <div class="lt-hero-grid">
          <div>
            <div class="zt-hero-num">${summary.paraphrase_pct || 0}<span class="zt-hero-pct">%</span></div>
            <p class="zt-hero-line"><b>答案靠「改写定位」</b> — 只有 ${summary.literal_pct || 0}% 能在原文原词对上选项。
              卡点主要是听懂后对上改写, 不是搜录音原词。</p>
            <div class="lt-split">
              <div class="lt-split-a" style="flex:${shortN || 1}"><b>${shortN}</b> 短对话<br><span>瞬时抓取</span></div>
              <div class="lt-split-b" style="flex:${longN || 1}"><b>${longN}</b> 长材料<br><span>一题一锚点</span></div>
            </div>
          </div>
          <div>
            <p class="lt-subh">干扰项怎么设（可核验计数）</p>
            <div class="lt-stats">${trapRows}</div>
            <p class="lt-subh" style="margin-top:14px">题干技能分布</p>
            <div class="lt-bars">${skillBars}</div>
          </div>
        </div>
        <p class="kb-dim" style="margin:12px 0 0">${esc(summary.teach_focus || "")} ${esc(summary.honesty || "")}</p>
      </section>`;
  }

  function _aidHTML(aid) {
    if (!aid) {
      return `<p class="kb-dim">本题暂无讲解（2026 整段听力未拆逐题）。</p>`;
    }
    const support = aid.answer_support || {};
    const kindLab = support.kind === "paraphrase" ? "改写对应" : "字面定位";
    const traps = (aid.distractors || []).map(d => {
      const cue = d.cue_in_transcript
        ? `<div class="lt-cue">原文诱饵: <em>${esc(d.cue_in_transcript)}</em></div>`
        : `<div class="lt-cue kb-dim">无字面诱饵（语义场/概括）</div>`;
      return `<li class="lt-trap">
        <div class="lt-trap-h"><span class="lt-opt">${esc(d.option)}</span>
          <strong>${esc(d.text)}</strong>
          <span class="lt-badge">${esc(d.trap)}</span></div>
        <p>${esc(d.why_wrong)}</p>${cue}
      </li>`;
    }).join("");
    const miss = (aid.easy_to_miss || []).map(x => `<li>${esc(x)}</li>`).join("");
    const tech = (aid.technique || []).map(x => `<li>${esc(x)}</li>`).join("");
    const bots = (aid.bottleneck || []).map(b => `<span class="lt-badge">${esc(b)}</span>`).join(" ");
    return `<div class="lt-aid">
      <div class="lt-meta">
        <span class="lt-badge lt-badge-sec">${esc(SEC_LABEL[aid.section] || aid.section)}</span>
        <span class="lt-badge">${esc(aid.skill)}</span>
        <span class="lt-badge lt-badge-kind">${esc(kindLab)}</span>
        ${bots}
      </div>
      <section class="lt-block lt-block-ans">
        <h4>答案</h4>
        <p class="lt-ans"><strong>${esc(aid.answer)}. ${esc(aid.answer_text)}</strong></p>
        <p class="kb-dim">${esc(support.note || "")}</p>
        ${support.transcript_span ? `<blockquote class="lt-span">${esc(support.transcript_span)}</blockquote>` : ""}
      </section>
      <section class="lt-block">
        <h4>干扰项（为何不选）</h4>
        <ul class="lt-traps">${traps || "<li class='kb-dim'>无</li>"}</ul>
      </section>
      <div class="lt-two">
        <section class="lt-block">
          <h4>容易忽略</h4>
          <ul class="lt-compact">${miss || "<li class='kb-dim'>无</li>"}</ul>
        </section>
        <section class="lt-block">
          <h4>怎么听</h4>
          <p class="lt-howto">${esc(aid.how_to || "")}</p>
          <ul class="lt-compact">${tech}</ul>
        </section>
      </div>
    </div>`;
  }

  function _renderDetail(d) {
    const panel = document.querySelector("#lt-detail");
    if (!panel) return;
    if (isErr(d) || d.error) {
      panel.innerHTML = errorBox({ title: "详情失败", msg: d.error || "未知错误" });
      return;
    }
    const aid = d.teaching_aid;
    const title = aid
      ? `${aid.year} 年 Q${aid.q} · ${aid.skill || ""}`
      : (d.origin_ref || "听力题");
    const src = _audioUrl(d.audio_id);
    panel.innerHTML = `
      <div class="lt-detail-h">
        <h3>${esc(title)}</h3>
        <p class="kb-dim">${esc(d.audio_note || "")}</p>
      </div>
      ${audioPlayer(src, d.audio_duration || 0)}
      ${_aidHTML(aid)}
      <details class="lt-fold"><summary>题干原文</summary><pre class="lt-pre">${esc(d.stem)}</pre></details>
      <details class="lt-fold"><summary>完整文字稿（对照关键句）</summary><pre class="gz-transcript lt-pre">${esc(d.transcript)}</pre></details>
    `;
  }

  function _applyFilters() {
    const { year, section, skill } = _state.filters;
    _state.filtered = _state.qs.filter(q => {
      if (year && String(q.year) !== String(year)) return false;
      if (section && q.section_layer !== section) return false;
      if (skill && q.skill !== skill) return false;
      return true;
    });
  }

  function _listHTML() {
    const rows = _state.filtered;
    if (!rows.length) return `<p class="kb-dim">当前筛选无题目。</p>`;
    return `<ul class="lt-qlist">${rows.map(q => {
      const active = String(q.qb_id) === String(_state.activeId) ? " is-active" : "";
      const sec = SEC_LABEL[q.section_layer] || "";
      return `<li class="lt-qitem${active}" data-id="${q.qb_id}">
        <span class="lt-qno">${esc(q.year)} · Q${esc(q.q)}</span>
        <span class="lt-qsk">${esc(q.skill || "")}</span>
        <span class="lt-qsec">${esc(sec)}</span>
        <span class="lt-qprev">${esc(q.stem_preview || "")}</span>
      </li>`;
    }).join("")}</ul>
    <p class="kb-dim lt-count">显示 ${rows.length} / ${_state.qs.length} 题</p>`;
  }

  function _wireFilters(summary) {
    const years = Object.entries(summary.by_year || {}).sort((a, b) => Number(b[0]) - Number(a[0]));
    const skills = Object.entries(summary.by_skill || {});

    function row(fid, lab, pairs, allLab) {
      const chips = [`<button type="button" class="lt-chip is-on" data-f="${fid}" data-v="">${esc(allLab)}</button>`]
        .concat(pairs.map(([v, n, label]) =>
          `<button type="button" class="lt-chip" data-f="${fid}" data-v="${esc(String(v))}">${esc(String(label || v))} <b>${n}</b></button>`
        ));
      return `<div class="lt-chiprow"><span class="lt-chiplab">${esc(lab)}</span><div class="lt-chips">${chips.join("")}</div></div>`;
    }

    const box = document.querySelector("#lt-filters");
    box.innerHTML =
      row("year", "年份", years.map(([y, n]) => [y, n, y]), "全部年")
      + row("section", "结构", [
        ["short", (summary.by_section || {}).short || 0, SEC_LABEL.short],
        ["long", (summary.by_section || {}).long || 0, SEC_LABEL.long],
      ], "全部")
      + row("skill", "技能", skills.slice(0, 8).map(([k, n]) => [k, n, k]), "全部技能");

    box.querySelectorAll(".lt-chip").forEach(btn => {
      btn.addEventListener("click", () => {
        const f = btn.dataset.f;
        _state.filters[f] = btn.dataset.v || "";
        box.querySelectorAll(`.lt-chip[data-f="${f}"]`).forEach(b => b.classList.toggle("is-on", b === btn));
        _applyFilters();
        if (_state.filtered.length) {
          _state.activeId = _state.filtered[0].qb_id;
          document.querySelector("#lt-list").innerHTML = _listHTML();
          _wireList();
          _loadDetail(_state.activeId);
        } else {
          document.querySelector("#lt-list").innerHTML = _listHTML();
          _wireList();
          document.querySelector("#lt-detail").innerHTML = `<p class="kb-dim">当前筛选无题目。</p>`;
        }
      });
    });
  }

  function _wireList() {
    document.querySelectorAll(".lt-qitem").forEach(li => {
      li.addEventListener("click", () => {
        _state.activeId = li.dataset.id;
        document.querySelector("#lt-list").innerHTML = _listHTML();
        _wireList();
        _loadDetail(_state.activeId);
      });
    });
  }

  async function _loadDetail(id) {
    const panel = document.querySelector("#lt-detail");
    panel.innerHTML = '<div class="loading-state"><span class="ls-dot"></span>载入讲解…</div>';
    const d = await fetchSafe(`/api/listening/detail?id=${encodeURIComponent(id)}`);
    _renderDetail(d);
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
    _state.qs = (list.questions || []).filter(q => q.has_teaching_aid);
    _state.filters = { year: "", section: "", skill: "" };
    _applyFilters();
    _state.activeId = (_state.filtered[0] || {}).qb_id || null;

    C.innerHTML = `<section class="scaffold lt-page">
      ${pageHead("基础库 · 听力讲解", "听后理解 · 改写定位 · 抗诱饵",
        `辽宁新高考 II · ${summary.n || 0} 题文字稿讲解（2021–2025）。音频为第三方核验档，非 NEEA 官方原声。`)}
      ${_hero(summary)}
      <section class="bk-card">
        <div class="bk-h"><span>按规律筛题</span><span class="bk-src">/api/listening/list</span></div>
        <div id="lt-filters"></div>
        <div class="lt-workspace">
          <div id="lt-list" class="lt-list">${_listHTML()}</div>
          <div id="lt-detail" class="lt-detail"><p class="kb-dim">点左侧题目查看讲解。</p></div>
        </div>
      </section>
    </section>`;

    _wireFilters(summary);
    _wireList();
    if (_state.activeId) _loadDetail(_state.activeId);
  });
})();
