/* 初中(沪教牛津hujiao)课程 — 46节真实教材单元进度 (Phase E4后续, 2026-07-08).
 *
 * 铁律1: 只 fetch /api/course/junior/syllabus(course.junior_knowledge.junior_syllabus单算点), 前端只渲染。
 * 与高中"40节课程"页(app_router.js teaching tab)的关键差异(不能照抄, 理由已在 junior_knowledge.py
 * 模块docstring写明, 此处重申前端侧后果):
 *   - 组织轴 = 6册(7a/7b/8a/8b/9a/9b)真实教材单元进度, 不是命题频次分配的主题群(theme_l2) —
 *     所以按 volume_key 分章(高中按 theme_l2 分章), 章头无"考查权重占比"横条(初中没有该统计)。
 *   - 每节课自带 grammar/vocab/phrases 三轴 lineage(高中版 content=null 只有作业真题列表) —
 *     所以点开一节课展示三轴知识点卡片, 不是作业真题清单; 复用 jr_jichu.js 的 _knowledgeHTML
 *     渲染逻辑(同一份知识点结构, Rule5 第2消费者, 避免重复实现)。
 *   - 无覆盖模型/课程地图(那是命题频次驱动特有的"用最少课程覆盖最大权重"证明, 初中数据太薄
 *     撑不起同款统计, 不为了"看起来一致"而编造)。
 */
(function () {
  const G = window.GZ;
  if (!G || !G.registerTab) return;
  const { fetchSafe, isErr, registerTab, pageHead } = G;
  const _esc = s => String(s == null ? "" : s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

  const VOL_LABEL = { "7a": "七年级上", "7b": "七年级下", "8a": "八年级上", "8b": "八年级下", "9a": "九年级上", "9b": "九年级下" };
  const VOL_ORDER = ["7a", "7b", "8a", "8b", "9a", "9b"];
  const _SEGC = [["var(--down)", "#fff"], ["var(--down-2)", "#fff"], ["var(--down-3)", "var(--ink)"]];

  // 三轴知识点卡片 — 复用 jr_jichu.js 的知识点渲染约定(同一批API字段: stage/zhongkao_exposure_count/
  // senior_exam_status/zhongkao_verified_questions/recurs_in_senior_textbook), 这里独立小实现
  // (非跨文件函数调用, 两个tab脚本互不依赖加载顺序; 若未来共享收口到common.js再抽, 当前2处不算过量重复)。
  function _kgroup(title, n, inner) { return n ? `<div class="tb-kg"><span class="tb-kg-h">${title} <b>${n}</b></span>${inner}</div>` : ""; }
  function _lessonKnowledgeHTML(l) {
    const STAGE_OVER = { "高中必修": 1, "高中选修": 1, "校本超纲": 1 };
    const words = (l.vocab && l.vocab.words || []).map(v => {
      const isOver = !!STAGE_OVER[v.stage];
      const zk = v.zhongkao_exposure_count || 0;
      const badge = zk > 0 ? `<sup class="tb-hit" title="中考真题曝光 ${zk} 次">${zk}</sup>` : "";
      return `<a class="gz-concept tb-word${zk > 0 ? " tb-word-tested" : ""}" data-concept="word:${_esc(v.word)}" title="${_esc(v.zh_def)}${v.stage ? ' · 学段: ' + _esc(v.stage) : ''}">${_esc(v.word)}${v.pos ? `<i>${_esc(v.pos)}</i>` : ""}${badge}${isOver ? '<sup class="tb-extra" title="超出初中课标">超</sup>' : ""}</a>`;
    }).join("");
    const gram = (l.grammar || []).map(g => {
      const zk = g.zhongkao_verified_questions || [];
      const badge = zk.length ? `<span class="tb-gram-pct" title="${zk.map(_esc).join(', ')}">中考验证 ${zk.length} 题</span>`
        : `<span class="tb-gram-pct tb-gram-pct-none">暂无中考验证</span>`;
      const senior = g.senior_exam_status ? `<span class="tb-chip">高中: ${_esc(g.senior_exam_status)}</span>` : "";
      const label = g.grammar_item_id ? G.conceptLink("grammar:jr:" + g.grammar_item_id, g.label || "?") : `<span class="tb-gram-l">${_esc(g.label || "?")}</span>`;
      return `<div class="tb-gram-row"><span class="tb-gram-l">${label}</span>${badge}${senior}</div>`;
    }).join("");
    const phrases = (l.phrases || []).map(p =>
      `<span class="tb-chip">${_esc(p.canonical)}${p.recurs_in_senior_textbook ? '<i>→高中复现</i>' : ''}</span>`).join("");
    const parts = [
      _kgroup("语法", (l.grammar || []).length, `<div>${gram}</div>`),
      _kgroup("词汇", (l.vocab && l.vocab.n_total) || 0, `<div class="tb-words">${words}</div>${l.vocab && l.vocab.n_overrun ? `<p class="tb-legend">其中 ${l.vocab.n_overrun} 词超出初中课标学段</p>` : ""}`),
      _kgroup("短语/句型/表达", (l.phrases || []).length, `<div class="tb-chips">${phrases}</div>`),
    ].filter(Boolean).join("");
    return (parts || '<span class="muted" style="font-size:12px;">本节暂无结构化知识点</span>')
      + (l.scope_note ? `<p class="tb-phrase-note">${_esc(l.scope_note)}</p>` : "");
  }

  function _lessonCard(l) {
    const title = l.title_en || (l.units_covered || []).map(u => u.title_en).filter(Boolean).join(" / ") || "";
    const nG = (l.grammar || []).length;
    const nV = (l.vocab && l.vocab.n_total) || 0;
    const nP = (l.phrases || []).length;
    return `<details class="ks-lesson"><summary class="ks-sum">
        <span class="ks-seq">第 ${l.seq} 节</span>
        <span class="ks-hwn" style="flex:1;">${_esc(title)}</span>
        <span class="ks-hwn">语法${nG} · 词汇${nV} · 短语${nP}</span>
      </summary>
      <div class="ks-body">${_lessonKnowledgeHTML(l)}</div>
    </details>`;
  }

  // 按 volume_key 分章 (真实教材册序, 非命题频次) — 每节课单元自带 volume_key, 连续同 volume 归一章
  function _volumeGroups(lessons) {
    const gs = [];
    for (const l of (lessons || [])) {
      const vk = l.volume_key || ((l.units_covered || [])[0] || {}).volume_key;
      const last = gs[gs.length - 1];
      if (!last || last.vol !== vk) gs.push({ vol: vk, lessons: [] });
      gs[gs.length - 1].lessons.push(l);
    }
    return gs;
  }

  function _chapter(g, i) {
    const [bg] = _SEGC[i % _SEGC.length];
    return `<section class="ks-chapter" id="jrks-ch-${i}">
      <header class="ks-ch-head">
        <div class="ks-ch-row">
          <span class="ks-ch-dot" style="background:${bg}"></span>
          <h2 class="ks-ch-name">${_esc(VOL_LABEL[g.vol] || g.vol || "未分册")}</h2>
          <span class="ks-ch-n">${g.lessons.length} 节</span>
        </div>
      </header>
      <div class="ks-tl">${g.lessons.map(l => `<div class="ks-tl-item">${_lessonCard(l)}</div>`).join("")}</div>
    </section>`;
  }

  function _courseMap(gs) {
    const segs = gs.map((g, i) => {
      const [bg, fg] = _SEGC[i % _SEGC.length];
      const t = `${VOL_LABEL[g.vol] || g.vol} · ${g.lessons.length} 节`;
      return `<button type="button" class="ks-map-seg" data-ch="jrks-ch-${i}" style="flex:${g.lessons.length} 1 0;background:${bg};color:${fg}" title="${_esc(t)} — 点击跳到该章">${_esc(t)}</button>`;
    }).join("");
    return `<div class="ks-map" role="navigation" aria-label="课程地图: ${gs.length} 册, 点击跳到对应章">${segs}</div>`;
  }

  registerTab("jr_kecheng", async () => {
    const C = G.$("#content");
    C.innerHTML = '<div class="loading-state"><span class="ls-dot"></span>载入课程框架…</div>';
    const syl = await fetchSafe("/api/course/junior/syllabus");
    if (isErr(syl)) { C.innerHTML = G.errorBox({ title: "课程框架加载失败" }); return; }
    const lessons = syl.lessons || [];
    const gs = _volumeGroups(lessons);
    C.innerHTML = `<section class="scaffold">
      ${pageHead("初中 · 课程", "46节真实教学进度", `组织轴 = ${_esc(syl.organizing_axis || "真实教材单元进度")} — 每节 = 1个真实教材单元, 自带语法/词汇/短语三轴知识点(非命题频次分配, 与高中"40节课程"方法论不同)。`)}
      ${_courseMap(gs)}
      ${gs.map((g, i) => _chapter(g, i)).join("")}
      <details class="zt-datahow"><summary>数据怎么来的?</summary>
        <ul>
          <li>组织轴: 6册46个真实教材单元(沪教牛津hujiao), 按学习顺序1单元=1节, 不套用命题频次分配。</li>
          <li>语法/词汇/短语三轴均逐条lineage到教材原文(grammar_occurrences/unit_vocab_intro/phrases), 挂载已有的高中衔接(deepens)边与中考真题验证(tests_grammar/tests_word)边。</li>
          <li>${_esc(lessons[0] && lessons[0].scope_note || "")}</li>
        </ul>
      </details>
    </section>`;
    C.querySelectorAll(".ks-map-seg").forEach(b => b.onclick = () => {
      const t = G.$("#" + b.dataset.ch);
      if (t) t.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
})();
