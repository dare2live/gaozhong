/* 备课工作流「考点驾驶舱」— ①命题研判页 (P1 三问分区重构 2026-07-02).
 *
 * 结构 = 学习者三问: 区1 考什么(A 考点分布·通栏 + 帕累托注记) / 区2 怎么变(B 命题迁移哑铃图 + C 题型结构)
 *      / 区3 怎么考(D 设问类型 + F 题材×思维) + 顶部结论 3 行(带看证据锚点) + 页尾「数据怎么来的?」人话对照.
 * 铁律1 单一计算点: 全部 fetch /api/* service 产物, 前端只渲染。B 的 era 间差值在 service 算
 *   (shift.by_dimension), 前端仅按 |delta| 排序; A 的累计占比为纯渲染层注记(对 service 已算 pct 求和)。
 * 分层非平均: 按卷制 era 分段看, 不混历史均值。
 * 认识论编码: 实心=真值; 空心/虚线/降饱和=方向性(n<30 或 AI 标注)。红族=「你该主攻的重点」每视图≤1系列。
 * 学习者语言: 工程术语(explicit_label/双模型/era/PIT)收进页尾「数据怎么来的?」details, 不进正文。
 * E 词汇热力卡已撤(2026-07-02 P1: 词数按状态≠考点, 答不出页级三问; 词汇实证在 #/zhenti)。
 * ECharts 仅渲染层, 数据仍 service 单算; B 图窄屏(≤820px)/echarts 缺失时降级回文本行实现。
 */
(function () {
  const G = window.GZ;
  if (!G || !G.registerTab) return;
  const { fetchJSON, registerTab } = G;

  const ERA_NEW = "2021+_新高考II";
  const ERA_OLD = "2015-2020_旧课标II";
  // 坑(2026-07-05 根因审计): state.era 是下划线拼接的内部 key(给 lookup 用), 3处(157/161/168行)
  // 曾直接把这个原始 key 拼进屏幕阅读器 aria-label / sr-only 表标题 / sendPrompt 下钻文案, 同文件
  // eraPill 按钮早已各自手写人话标签, 这里补一份单一映射复用, 不再漏 raw key。
  const ERA_LABEL = { [ERA_NEW]: "2021+ 新高考II", [ERA_OLD]: "2015–2020 旧课标II" };
  const DC = (window.GZ_CAT && window.GZ_CAT.dim) || {};   // 维度基础标签单一来源 category-config.js (防 beike/teacher/jiangke 漂移)
  const DIM_LABEL = { genre: DC.genre, theme_context: DC.theme_context, theme_l2: DC.theme_l2 + "·课标10群" };
  // 图表数据编码色 — 锚 design-system 令牌族值 (blue=--down / blue3=--down-3 / blue4=--down-4
  // / up=--accent-ink·--up / grey=--data-gray; echarts canvas 需 hex 故写值非 var, 跨图一致; 无新增 ad-hoc 色)
  const C = { blue: "#1F5F94", blue3: "#8FAECB", blue4: "#C3D4E3", up: "#9C2C20", upBg: "#FAECE7", downBg: "#E6F1FB", grey: "#B4B2A9" };
  const INK3 = "#76716A";   // 值锚 --ink-3 (canvas 标签用)
  const PRES = { out: "#BE3A2B", in: "#2E7D54" };   // presence 语义色(原热力沿用): 红=退场(值锚 --accent) / 绿=登场

  let state = { era: ERA_NEW, dim: "theme_l2", dist: null, cross: "genre" };
  const charts = {};
  const crossCache = {};
  const SHIFT_MQ = window.matchMedia ? window.matchMedia("(max-width: 820px)") : { matches: false };

  // ── a11y (RC1): 动态 aria-label + sr-only 数据表 fallback。复用各 render 已有的同一份 service 数据
  //    (单一计算点, 不重算/不 refetch); 仅追加读屏文字, 不动任何视觉 echarts option。
  const escHtml = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  // 给图表容器(div#id)旁注入/替换 sr-only 兄弟节点 (idempotent: 同 chartId 重渲染只替换不累加)。
  function setSrTable(chartId, captionHtml, headers, rows) {
    const el = G.$("#" + chartId);
    if (!el) return;
    const cls = "bk-sr-" + chartId;
    let sr = el.parentNode.querySelector("." + cls);
    if (!sr) { sr = document.createElement("table"); sr.className = "sr-only " + cls; el.insertAdjacentElement("afterend", sr); }
    const thead = "<thead><tr>" + headers.map(h => `<th>${escHtml(h)}</th>`).join("") + "</tr></thead>";
    const tbody = "<tbody>" + rows.map(r => "<tr>" + r.map(c => `<td>${escHtml(c)}</td>`).join("") + "</tr>").join("") + "</tbody>";
    sr.innerHTML = `<caption>${captionHtml}</caption>${thead}${tbody}`;
  }
  function rmSrTable(chartId) {
    const el = G.$("#" + chartId);
    const sr = el && el.parentNode.querySelector(".bk-sr-" + chartId);
    if (sr) sr.remove();
  }
  function setAria(chartId, label) { const el = G.$("#" + chartId); if (el) el.setAttribute("aria-label", label); }
  // 设问技能堆叠色 (推断=强调红, 与 D 区一致); 固定堆叠顺序让"推断"锚左边便于跨题材比
  const SKILL_COLOR = (window.GZ_CAT && window.GZ_CAT.skill) || {};   // 设问技能色单一来源 category-config.js
  const CROSS_LBL = { genre: DC.genre, theme_l2: DC.theme_l2, theme_context: "课标" + DC.theme_context };

  function shell() {
    const sect = (id, hid, t, sub, inner, links) => `
<section class="bk-sect" id="${id}" aria-labelledby="${hid}">
  <h3 class="bk-sect-h" id="${hid}">${t} <span class="bk-sect-sub">${sub}</span></h3>
  ${inner}
  ${links ? `<p class="bk-sect-links">${links}</p>` : ""}
</section>`;
    const cardA = `<section class="bk-card" id="bk-card-a"><div class="bk-h"><span>A 考点分布 <small id="bk-dimname">主题群</small></span><span class="bk-src">/api/exam_point/distribution</span></div><div id="bk-dist" role="img" aria-label="考点分布条形图: 各课标主题群在辽宁卷的考查占比 (真被考的占比, 非教材出现频次)" style="height:300px;"></div><p id="bk-distnote" class="muted" style="font-size:12px;margin:8px 0 0;"></p></section>`;
    const cardB = `<section class="bk-card"><div class="bk-h"><span>B 命题迁移 <small>2015–20 → 2021+ · 变化最大的排最上</small></span><span class="bk-src">/api/exam_point/distribution · shift</span></div><div id="bk-shift" role="img" aria-label="命题迁移哑铃图: 各类别在旧卷制与新卷制的考查占比变化"></div><p id="bk-shiftnote" class="muted" style="font-size:12px;margin:8px 0 0;"></p></section>`;
    const cardC = `<section class="bk-card"><div class="bk-h"><span>C 题型结构演变 · 存续时间带</span><span id="bk-relbadge"></span></div><div id="bk-trend" role="img" aria-label="题型结构存续时间带: 各题型在辽宁卷的存续区间与登场、退场事件" style="height:240px;"></div><p id="bk-trendnote" class="muted" style="font-size:12px;margin:8px 0 0;"></p></section>`;
    const cardD = `<section class="bk-card"><div class="bk-h"><span>D 设问类型 · 怎么想 <small>子题级 · 教研解析标签</small></span><span class="bk-src">/api/exam_point/cognitive_skill</span></div><div id="bk-cog" role="img" aria-label="设问类型分布: 旧课标与新高考的认知技能占比对比" style="height:240px;"></div><p id="bk-cognote" class="muted" style="font-size:12px;margin:8px 0 0;"></p></section>`;
    const cardF = `<section class="bk-card" id="bk-card-f"><div class="bk-h"><span>F 题材 × 思维 <small id="bk-crosslbl">体裁·2015–20截面</small></span><span class="bk-src">/api/exam_point/cognitive_by_content</span></div><div id="bk-crosstoggle" style="margin:2px 0 6px;"></div><div id="bk-cross" role="img" aria-label="题材与思维交叉: 各类语篇考查的认知技能分布" style="height:248px;"></div><p id="bk-crossnote" class="muted" style="font-size:12px;margin:8px 0 0;"></p></section>`;
    return `
${G.pageHead("高中 · 辽宁新高考 II 卷", "高考英语考什么", "考什么 · 怎么变 · 怎么考 — 每个数字来自辽宁真题与课标原文的统计, 可以点开追到原卷。", `<button id="bk-print" class="bk-export" title="打印/导PDF本页研判">${G.icon("printer")} 打印本页</button>`)}
<div id="bk-verdict" class="bk-verdict" aria-live="polite"></div>
<div id="bk-filter" class="bk-filter"></div>
${sect("bk-sect-what", "bk-h-what", "考什么", "— 真被考的主题与体裁, 按考查占比排", cardA,
    `这些考点不是孤立出的 — <a href="#/graph">考点怎么绑着出题 → 考点关联</a>`)}
${sect("bk-sect-change", "bk-h-change", "怎么变", "— 2021 换卷后, 命题重心挪去了哪", cardB + cardC, "")}
${sect("bk-sect-how", "bk-h-how", "怎么考", "— 同一篇文章, 设问在考哪种思维 (下方两图跨度不同: D含新老两卷对比, F仅2015–20旧卷截面)", `<div class="bk-grid">${cardD}${cardF}</div>`,
    `<a href="#/zhenti">完整套路 → 真题特点</a>`)}
<div class="bk-foot">
  <p class="bk-next">下一步: <a href="#/zhenti">看词从哪来的实证 → 真题特点</a></p>
  <details class="bk-method"><summary>数据怎么来的?</summary>
    <ul>
      <li><b>出现 ≠ 考查</b> — 教材里出现过 ≠ 高考考过, 本页只统计真被考的。</li>
      <li><b>卷制 era 分层</b> — 新高考(2021 起)和老高考分开统计, 不混着平均。</li>
      <li><b>双模型标注</b> — 题材/主题类标签由两个 AI 独立标注且结论一致才计入(方向性参考)。</li>
      <li><b>explicit_label(教研显式标签)</b> — 设问类型的题型标签直接来自教研解析, 不靠 AI 猜。</li>
    </ul>
  </details>
</div>`;
  }

  function filterBar() {
    const eraPill = (id, label) => `<button class="bk-pill ${state.era === id ? "on" : ""}" data-era="${id}">${label}</button>`;
    const dimOpt = Object.keys(DIM_LABEL).map(k => `<option value="${k}" ${state.dim === k ? "selected" : ""}>${DIM_LABEL[k]}</option>`).join("");
    // 样本充足性: 后端审计#5 — genre/theme 是篇章级维度, 样本量按该(era,维度)篇章数(by_era_dim),
    // 非 era 子题池(142会虚高~4.5x 且掩盖 theme_l2 n=19<30 的不足)。service 已算 distribution_eligible, 前端不重判 (Rule1)。
    const _sf = (state.dist && state.dist.sufficiency) || {};
    const suff = ((_sf.by_era_dim || {})[state.era] || {})[state.dim]
              || ((_sf.by_era || {})[state.era] || {});   // 兜底: 无 per-dim 时回退 era 池
    const n = suff.n_total != null ? suff.n_total : 0;
    const ok = !!suff.distribution_eligible;
    const unit = (_sf.by_era_dim && _sf.by_era_dim[state.era] && _sf.by_era_dim[state.era][state.dim]) ? "篇" : "题";
    return `
<span class="bk-flabel">卷制</span>${eraPill(ERA_NEW, "2021+ 新高考II")}${eraPill(ERA_OLD, "2015–2020")}
<span class="bk-lock">辽宁卷·锁定</span>
<span class="bk-flabel" style="margin-left:8px;">维度</span><select id="bk-dim" aria-label="考点分布维度">${dimOpt}</select>
<span class="bk-suff ${ok ? "ok" : "warn"}">${ok ? "分布可用 · " + n + unit : "样本不足(方向性) · " + n + unit}</span>`;
  }

  // era+dim 的样本充足旗 (service 已算 distribution_eligible, 前端只读 — Rule1)
  function distEligible(era, dim) {
    const byEraDim = ((state.dist && state.dist.sufficiency) || {}).by_era_dim || {};
    const s = (byEraDim[era] || {})[dim];
    return !s || s.distribution_eligible !== false;   // 缺省视为可用; 仅显式 false 才降级
  }

  function renderDist() {
    const desc = (state.dist.distribution[state.era][state.dim] || []);   // service 已按占比降序
    const rows = desc.slice().reverse();                                  // echarts 横条自下而上
    // 坑(2026-07-06 数据关联设计审查): 小样本(如n=19分7类, 单类n=1)下累计占比原精确到小数点1位,
    // 与旁边"样本不足(方向性)"警示语气冲突, 给人虚假精确感。distEligible=false 时累计占比降级为
    // 整数(tooltip/label/note/aria-label/sr表 5处输出全部读同一份cums, 一处降级全部生效)。
    const elig = distEligible(state.era, state.dim);
    // 帕累托注记 (#3): 累计占比 = 纯渲染层对 service 已算 pct 求和 (排序累计, 不重算占比本身)
    let cum = 0;
    const cums = desc.map(r => { cum += r.pct; return elig ? +cum.toFixed(1) : Math.round(cum); });
    let pN = desc.length;
    for (let i = 0; i < desc.length; i++) if (cums[i] >= 70) { pN = i + 1; break; }
    G.$("#bk-dimname").textContent = DIM_LABEL[state.dim];
    charts.dist = G.initChart(G.$("#bk-dist"));
    charts.dist.setOption({
      grid: { left: 4, right: 96, top: 8, bottom: 8, containLabel: true },
      // 坑(2026-07-05 数据可视化审计): 无 rows 时 Math.max(...[]) = -Infinity(轴崩); 姊妹图 cog 图(下方
      // renderCognitiveSkill)已用 ,0 兜底, 此处补齐同款防御(现无数据会触发, 补上防未来 dim/era 组合为空)。
      // 坑(2026-07-05 教师视角审计): 未取整的浮点乘法(如31.6*1.15)会产生 36.339999999999996 这类原始
      // 浮点噪声直接喂给 echarts 当轴上限刻度; 姊妹图 renderShiftDumbbell(下方)已用 Math.ceil(...*1.15)
      // 处理过同一模式, 此处补齐同款取整。
      xAxis: { type: "value", max: Math.ceil(Math.max(...rows.map(r => r.pct), 0) * 1.15), axisLabel: { formatter: "{value}%" }, splitLine: { lineStyle: { color: "rgba(128,128,128,0.12)" } } },
      yAxis: { type: "category", data: rows.map(r => r.label), axisTick: { show: false }, axisLine: { show: false } },
      tooltip: { trigger: "axis", formatter: p => `${p[0].name}<br/>${p[0].value}% · n=${rows[p[0].dataIndex].n} · 累计前${desc.length - p[0].dataIndex}类 ${cums[desc.length - 1 - p[0].dataIndex]}%` },
      series: [{
        type: "bar", data: rows.map(r => r.pct), barWidth: "62%",
        itemStyle: { color: C.blue, borderRadius: [0, 4, 4, 0] },
        label: {
          show: true, position: "right", fontSize: 11, color: INK3,
          formatter: p => {
            const i = desc.length - 1 - p.dataIndex;   // 还原降序位次
            const base = `${p.value}% · n=${rows[p.dataIndex].n}`;
            return i > 0 ? `${base} {c|▸累计${cums[i]}%}` : base;
          },
          rich: { c: { color: C.grey, fontSize: 10 } },   // 条尾灰字=累计占比 (锚 --data-gray)
        },
      }],
    });
    // 坑(2026-07-06 数据关联设计审查): A卡切到"体裁"维度时6个体裁分类与F卡(题材×思维)完全重叠
    // (同一份底层真题池, 只是A是passage粒度/F是子题粒度), 但两卡分属"考什么"/"怎么考"两个区块,
    // 中间隔着整个"怎么变"区, 无任何呼应——补一条跳转提示, 不做echarts跨图高亮(复杂度/收益不对等)。
    // 坑: 页面本身就是 #/beike 路由, 用 <a href="#bk-card-f"> 会把hash改成"bk-card-f"触发SPA路由
    // 误判为未知页面——沿用本文件已有的 data-goto + scrollIntoView 模式(非真正hash跳转)。
    const xlink = state.dim === "genre"
      ? `<br><button type="button" class="bk-vlink" data-goto="bk-card-f" style="font-size:11.5px;">同一批真题按题材看"怎么想"(推断占比) → F卡</button>` : "";
    G.$("#bk-distnote").innerHTML = desc.length > 1
      ? `前 <b>${pN}</b> 类 = <b>${cums[pN - 1]}%</b> 考查权重 — 备课先覆盖这 ${pN} 类${elig ? "" : "(本维度样本不足, 方向性参考)"}。条尾灰字为累计占比。${xlink}`
      : "";
    G.$$("#bk-distnote [data-goto]").forEach(b => b.onclick = () => {
      const t = document.getElementById(b.dataset.goto);
      if (t) t.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    // a11y: 动态 aria-label(图名+维度+era+前几项实值) + sr-only 数据表 — 复用本函数已用的 rows(原序非 reverse)
    const dimName = DIM_LABEL[state.dim];
    setAria("bk-dist",
      `考点分布条形图(${dimName} · ${ERA_LABEL[state.era] || state.era} 辽宁卷): ` +
      (desc.slice(0, 4).map(r => `${r.label} ${r.pct}%`).join(", ") || "无数据") +
      (desc.length > 4 ? ` 等共 ${desc.length} 项` : "") +
      (desc.length > 1 ? `; 前 ${pN} 类合计 ${cums[pN - 1]}%` : ""));
    setSrTable("bk-dist", `考点分布 — ${escHtml(dimName)} · ${escHtml(ERA_LABEL[state.era] || state.era)} 辽宁卷`,
      ["类别", "占比", "题数", "累计占比"], desc.map((r, i) => [r.label, r.pct + "%", "n=" + r.n, cums[i] + "%"]));
    charts.dist.off("click");
    // #3: 点考点条 → 弹该考点浮窗(关联+真题, 复用#2修好的 exam_point 真题); fallback sendPrompt 下钻
    charts.dist.on("click", p => {
      const cid = `exam_point:${state.dim}:${p.name}`;
      if (G.openPopup) G.openPopup(cid);
      else if (G.sendPrompt) G.sendPrompt(`下钻 ${ERA_LABEL[state.era] || state.era} 辽宁卷 ${DIM_LABEL[state.dim]}「${p.name}」的真题清单`);
    });
  }

  // ── B 命题迁移: 宽屏=echarts custom 哑铃图 / 窄屏(≤820px)·无 echarts=文本行降级 (#1)
  function renderShift() {
    const el = G.$("#bk-shift");
    if (!el || !state.dist) return;
    const raw = ((state.dist.shift || {}).by_dimension || {})[state.dim] || [];
    const rows = raw.slice().sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));   // 渲染层按 |delta| 降序 (差值本身 service 已算)
    if (!rows.length) {
      const inst0 = window.echarts && window.echarts.getInstanceByDom(el);
      if (inst0) { inst0.dispose(); delete charts.shift; }
      el.removeAttribute("role"); el.style.height = "";
      el.innerHTML = '<p class="muted">无迁移数据</p>';
      const note0 = G.$("#bk-shiftnote"); if (note0) note0.textContent = "";
      rmSrTable("bk-shift");
      return;
    }
    if (SHIFT_MQ.matches || !window.echarts) renderShiftText(rows, el);
    else renderShiftDumbbell(rows, el);
  }

  // 窄屏降级路径: 保留原文本行实现 (行序同哑铃图 = |delta| 降序)
  function renderShiftText(rows, el) {
    const inst = window.echarts && window.echarts.getInstanceByDom(el);
    if (inst) { inst.dispose(); delete charts.shift; }
    el.removeAttribute("role"); el.removeAttribute("aria-label"); el.style.height = "";
    rmSrTable("bk-shift");   // 文本行本身可读, 移除图模式残留的 sr 表防重复朗读
    el.innerHTML = rows.map(r => {
      const up = r.delta >= 0, col = up ? C.up : C.blue, bg = up ? C.upBg : C.downBg;
      return `<div class="bk-shift-row"><span class="bk-shift-k">${escHtml(r.label)}</span>
        <span class="bk-shift-v">${r.then_pct}% → <b>${r.now_pct}%</b></span>
        <span class="bk-delta" style="color:${col};background:${bg};">${up ? "↑" : "↓"} ${Math.abs(r.delta)}pt</span></div>`;
    }).join("");
    renderShiftNote(rows);
  }

  function renderShiftDumbbell(rows, el) {
    // 端点 n 查 service 已算的 distribution[era][dim] (渲染层查表, 不重算 — Rule1)
    const nOfEra = (era, label) => {
      const a = ((state.dist.distribution || {})[era] || {})[state.dim] || [];
      const x = a.find(v => v.label === label);
      return x ? x.n : null;
    };
    const solidNew = distEligible(ERA_NEW, state.dim);   // 认识论: 新era n<30 → 空心虚线环+虚连线 = 方向性
    el.style.height = (rows.length * 38 + 46) + "px";
    el.setAttribute("role", "img");
    let inst = window.echarts.getInstanceByDom(el);
    if (!inst) { el.innerHTML = ""; inst = G.initChart(el); }
    else inst.resize();   // 行数随维度变 → 容器高度变
    if (!inst) return;
    charts.shift = inst;
    const maxV = Math.max(...rows.flatMap(r => [r.then_pct, r.now_pct]));
    inst.setOption({
      grid: { left: 4, right: 84, top: 26, bottom: 8, containLabel: true },
      xAxis: {
        type: "value", min: 0, max: Math.ceil(maxV * 1.15),
        axisLabel: { formatter: "{value}%", fontSize: 10 },
        splitLine: { lineStyle: { color: "rgba(128,128,128,0.12)" } },
      },
      yAxis: { type: "category", data: rows.map(r => r.label), inverse: true, axisTick: { show: false }, axisLine: { show: false }, axisLabel: { fontSize: 11 } },
      tooltip: {
        trigger: "item", confine: true,
        formatter: p => {
          const r = rows[p.dataIndex];
          if (!r) return "";
          const n0 = nOfEra(ERA_OLD, r.label), n1 = nOfEra(ERA_NEW, r.label);
          return `<b>${escHtml(r.label)}</b><br/>2015–20 旧课标II: ${r.then_pct}%${n0 != null ? " · n=" + n0 : ""}<br/>`
            + `2021+ 新高考II: ${r.now_pct}%${n1 != null ? " · n=" + n1 : ""}<br/>`
            + `${r.delta >= 0 ? "↑ 升" : "↓ 降"} ${Math.abs(r.delta)}pt · AI 标注 · 看方向`;
        },
      },
      series: [{
        type: "custom", clip: false,
        renderItem: (params, api) => {
          const r = rows[params.dataIndex];
          const p0 = api.coord([r.then_pct, params.dataIndex]);
          const p1 = api.coord([r.now_pct, params.dataIndex]);
          const up = r.delta >= 0;
          const lineCol = up ? C.up : C.blue;                                // 连线色=方向: 升=--accent-ink / 降=--down
          const lw = Math.min(3, Math.max(1.5, Math.abs(r.delta) / 8));      // 粗细∝|delta|, clamp 1.5–3px
          const cs = params.coordSys;
          const pillX = cs.x + cs.width + 10, pillW = 62, pillH = 18;        // 行尾 delta pill (canvas 版 .bk-delta 同色系)
          return { type: "group", children: [
            { type: "line", shape: { x1: p0[0], y1: p0[1], x2: p1[0], y2: p1[1] },
              style: { stroke: lineCol, lineWidth: lw, lineDash: solidNew ? null : [4, 3] } },
            { type: "circle", shape: { cx: p0[0], cy: p0[1], r: 5 },          // 旧era端点: 灰描边白填充空心 (--data-gray)
              style: { fill: "#fff", stroke: C.grey, lineWidth: 1.6 } },
            solidNew
              ? { type: "circle", shape: { cx: p1[0], cy: p1[1], r: 5.5 },    // 新era端点: 实心 --down
                  style: { fill: C.blue, stroke: "#fff", lineWidth: 1 } }
              : { type: "circle", shape: { cx: p1[0], cy: p1[1], r: 5.5 },    // 样本不足: 空心虚线环 = 方向性
                  style: { fill: "#fff", stroke: C.blue, lineWidth: 1.6, lineDash: [3, 2] } },
            { type: "rect", shape: { x: pillX, y: p1[1] - pillH / 2, width: pillW, height: pillH, r: 9 },
              style: { fill: up ? C.upBg : C.downBg } },
            { type: "text", style: {
                x: pillX + pillW / 2, y: p1[1] + 0.5, text: `${up ? "↑" : "↓"} ${Math.abs(r.delta)}pt`,
                fill: up ? C.up : C.blue, align: "center", verticalAlign: "middle", font: "600 11px sans-serif" } },
          ] };
        },
        data: rows.map(r => [r.then_pct, r.now_pct]),
      }],
    }, true);
    renderShiftNote(rows, solidNew);
    // a11y: 图模式补读屏 (文本模式行本身可读, 不加)
    const top3 = rows.slice(0, 3).map(r => `${r.label} ${r.delta >= 0 ? "升" : "降"} ${Math.abs(r.delta)}pt`).join(", ");
    setAria("bk-shift", `命题迁移哑铃图(${DIM_LABEL[state.dim]} · 2015–20 → 2021+ 辽宁卷, 按变化幅度降序): ${top3}${rows.length > 3 ? ` 等共 ${rows.length} 项` : ""}`);
    setSrTable("bk-shift", `命题迁移 — ${escHtml(DIM_LABEL[state.dim])} · 2015–20 → 2021+ 辽宁卷`,
      ["类别", "2015–20 占比", "2021+ 占比", "变化"],
      rows.map(r => [r.label, r.then_pct + "%", r.now_pct + "%", (r.delta >= 0 ? "升 " : "降 ") + Math.abs(r.delta) + "pt"]));
  }

  function renderShiftNote(rows, solidNew) {
    const note = G.$("#bk-shiftnote");
    if (!note) return;
    const isChart = !(SHIFT_MQ.matches || !window.echarts);
    // 坑(2026-07-05 数据可视化审计): 图例圆点符号原写死实心●, 但 solidNew=false 时渲染层(见上方
    // renderShiftDumbbell)实际画的是空心虚线圈——图例与图不符(默认维度 theme_l2 现时 n=19<30 即触发)。
    // 圆点符号跟渲染层同一个 solidNew 判据, 不再写死。
    const newDot = isChart && solidNew === false ? "○" : "●";
    const legend = isChart
      ? `读法: <span style="color:${C.grey}">○</span> 2015–20 起点 · <span style="color:${C.blue}">${newDot}</span> 2021+ 现状; <span style="color:${C.up}">红线=升温</span> · <span style="color:${C.blue}">蓝线=降温</span>, 线越粗变化越大。`
      : `读法: <span style="color:${C.up}">↑红=升温</span> · <span style="color:${C.blue}">↓蓝=降温</span>, 按变化幅度排。`;
    const suffNew = (((state.dist.sufficiency || {}).by_era_dim || {})[ERA_NEW] || {})[state.dim] || {};
    const caveat = (isChart && solidNew === false)
      ? `<br><small class="muted">2021+ 该维度样本${suffNew.n_total != null ? " n=" + suffNew.n_total + "篇" : ""}不足 30 → 空心虚线 = 方向性参考, 非精确分布。</small>`
      : "";
    note.innerHTML = legend + ` <small class="muted">题材/主题为 AI 标注, 看方向。</small>` + caveat;
  }

  function renderTrend(p) {
    // C 卡「存续时间带」(P2-5, 方案书图表6 P4 形态; 2026-07-03 重写自 presence 热力, 语义平移不变):
    // 每题型一行, 存续区间=连续横带; 事件端点=退场红点/登场绿点; 2021 era 竖虚线保留。
    // 结构真值语义沿用原热力: signal 由卷面结构config定非数据; extraction_gap/未登记年=淡色虚线诚实标注
    // (存续年仅样本, 不作首末考年信号)。认识论编码: 实心带·点=真值, 淡色虚线带·段·空心点=方向性。
    const items = (p && p.by_question_type) || [];
    const SIG = { skeleton: { t: "骨架·两卷制常驻" }, retired: { t: "真退场·卷面取消" }, introduced: { t: "真登场·卷面新增" }, unregistered: { t: "未登记结构" } };
    const ord = { skeleton: 0, retired: 1, introduced: 2, unregistered: 3 };
    const list = items.slice().sort((a, b) => (ord[a.signal] ?? 9) - (ord[b.signal] ?? 9));
    const all = items.flatMap(x => [...(x.old_years || []), ...(x.new_years || [])]);
    if (!all.length) { G.$("#bk-trend").innerHTML = "<p class='muted'>无题型数据</p>"; return; }
    const years = []; for (let y = Math.min(...all); y <= Math.max(...all); y++) years.push(y);
    const xi = {}; years.forEach((y, i) => { xi[y] = i; });
    const REFORM = parseInt(ERA_NEW, 10);   // 2021 新高考改革年 (era 常量单一来源, 非另行 hardcode)
    // 渲染层几何预算: 连续存续段 runs + 段间未登记 gap 年 (平移原热力空格语义 = 数据缺口, 非卷面取消)
    const rows = list.map(x => {
      const pres = [...new Set([...(x.old_years || []), ...(x.new_years || [])])].sort((a, b) => a - b);
      const runs = [];
      pres.forEach(y => { const r = runs[runs.length - 1]; if (r && y === r[1] + 1) r[1] = y; else runs.push([y, y]); });
      const gaps = [];
      for (let i = 1; i < runs.length; i++) gaps.push([runs[i - 1][1] + 1, runs[i][0] - 1]);
      return { ...x, pres, runs, gaps };
    });
    const fmtRuns = rs => rs.map(([a, b]) => a === b ? String(a) : a + "–" + b).join("、");
    const qts = list.map(x => x.question_type + (x.extraction_gap ? " 注" : ""));
    G.$("#bk-relbadge").innerHTML = `<span class="bk-suff ok">结构真值·卷面config掩码</span>`;
    const el = G.$("#bk-trend");
    el.style.height = (rows.length * 30 + 56) + "px";   // 行数驱动高度 (时间带每行 30px + 轴/era标签)
    charts.trend = G.initChart(el);
    if (!charts.trend) return;
    charts.trend.resize();   // 容器高度改动后同步画布 (复用实例场景)
    charts.trend.setOption({
      grid: { left: 4, right: 16, top: 26, bottom: 22, containLabel: true },
      xAxis: { type: "category", data: years, axisLabel: { fontSize: 10 }, axisTick: { alignWithLabel: true }, splitLine: { show: false } },
      yAxis: { type: "category", data: qts, inverse: true, axisLabel: { fontSize: 10 }, axisTick: { show: false }, axisLine: { show: false } },
      tooltip: {
        confine: true,
        formatter: c => {
          const r = rows[c.dataIndex];
          if (!r) return "";
          const lines = [`<b>${escHtml(r.question_type)}</b> · ${(SIG[r.signal] || SIG.unregistered).t}`];
          if (!r.pres.length) lines.push("无提取记录 (卷面旧制有, 本项目未抽到)");
          else if (r.extraction_gap) lines.push(`记录年: ${fmtRuns(r.runs)} — <b>仅样本</b>, 卷面确有但未抽全, 不作首末考年`);
          else lines.push(`存续: ${fmtRuns(r.runs)}`);
          if (r.gaps.length && !r.extraction_gap) lines.push(`虚线段 ${fmtRuns(r.gaps)} = 该年未登记 (数据缺口, 非卷面取消)`);
          if (r.signal === "retired") lines.push(`<b style="color:${PRES.out}">新高考取消</b> (${REFORM} 起卷面不再考)`);
          if (r.signal === "introduced") lines.push(`<b style="color:${PRES.in}">新高考新增</b>${r.extraction_gap ? " (首考年未抽全, 登场年不可信)" : ""}`);
          return lines.join("<br/>");
        },
      },
      series: [{
        type: "custom", clip: false,
        renderItem: (params, api) => {
          const r = rows[params.dataIndex];
          const w = api.size([1, 0])[0];                                  // 单年像素宽
          const rowY = api.coord([0, params.dataIndex])[1];               // 行中心 y
          const px = y => api.coord([xi[y], params.dataIndex])[0];        // 年份中心 x
          const cs = params.coordSys, bh = 10;
          const kids = [];
          // 2021 era 分界: 竖虚线 + 「新高考改革」标签 (只在第一行画一次, 跨全高)
          if (params.dataIndex === 0 && xi[REFORM] != null && xi[REFORM - 1] != null) {
            const bx = px(REFORM) - w / 2;
            kids.push({ type: "line", silent: true, shape: { x1: bx, y1: cs.y, x2: bx, y2: cs.y + cs.height },
              style: { stroke: INK3, lineWidth: 1, lineDash: [4, 3], opacity: 0.6 } });
            kids.push({ type: "text", silent: true, style: { x: bx + 4, y: cs.y - 5, text: REFORM + " 新高考改革",
              fill: INK3, font: "600 10px sans-serif", verticalAlign: "bottom" } });
          }
          // 存续带: 实心蓝=已抽全存续(真值) / 淡色虚线框带=提取不全(方向性, 年份仅样本) — 平移原热力 0.32 淡色格
          r.runs.forEach(([a, b]) => {
            const x0 = px(a) - w / 2 + 1, x1 = px(b) + w / 2 - 1;
            kids.push(r.extraction_gap
              ? { type: "rect", shape: { x: x0, y: rowY - bh / 2, width: x1 - x0, height: bh, r: 2 },
                  style: { fill: C.blue4, stroke: C.blue3, lineWidth: 1, lineDash: [3, 2] } }
              : { type: "rect", shape: { x: x0, y: rowY - bh / 2, width: x1 - x0, height: bh, r: 2 },
                  style: { fill: C.blue } });
          });
          // 段间未登记年: 细虚线段 (诚实标注数据缺口, 不画成实带冒充存续)
          r.gaps.forEach(([a, b]) => {
            kids.push({ type: "line", shape: { x1: px(a) - w / 2 + 1, y1: rowY, x2: px(b) + w / 2 - 1, y2: rowY },
              style: { stroke: C.blue3, lineWidth: 1.5, lineDash: [3, 3] } });
          });
          // 事件端点: 实心点=年份真值 / 空心虚线环=登退场年不可信(只作卷面级信号) — 同哑铃图认识论编码
          const dot = (cx, col, solid) => ({ type: "circle", shape: { cx, cy: rowY, r: 4.5 },
            style: solid ? { fill: col, stroke: "#fff", lineWidth: 1 } : { fill: "#fff", stroke: col, lineWidth: 1.6, lineDash: [2, 2] } });
          const txt = (x, text, col, align) => ({ type: "text",
            style: { x, y: rowY + 0.5, text, fill: col, align, verticalAlign: "middle", font: "600 10px sans-serif" } });
          if (r.signal === "retired") {
            if (r.pres.length) {
              const cx = px(r.pres[r.pres.length - 1]) + w / 2 - 1;
              // 取消年: 末考年真值时=末考年+1 (短文改错 2020+1=2021, 与改革年重合); 否则退回改革年(卷面级信号)
              const yr = (!r.extraction_gap && r.last_year != null) ? r.last_year + 1 : REFORM;
              kids.push(dot(cx, PRES.out, !r.extraction_gap));
              kids.push(txt(cx + 7, yr + " 已取消", PRES.out, "left"));
            } else {
              // 0 提取记录 (书面表达): 灰字诚实占位, 空心红点挂 era 分界 (取消=卷面级信号, 非数据推得)
              const bx = xi[REFORM] != null ? px(REFORM) - w / 2 : cs.x + cs.width;
              kids.push({ type: "text", silent: true, style: { x: (cs.x + bx) / 2, y: rowY + 0.5, text: "卷面旧制有 · 未抽到记录",
                fill: C.grey, align: "center", verticalAlign: "middle", font: "10px sans-serif" } });
              kids.push(dot(bx, PRES.out, false));
              kids.push(txt(bx + 7, REFORM + " 已取消", PRES.out, "left"));
            }
          }
          if (r.signal === "introduced" && r.pres.length) {
            const first = r.pres[0];
            const cx = px(first) - w / 2 + 1;
            const solid = !r.extraction_gap && r.first_year != null;
            // 提取不全 → 登场年不可信 (续写/应用文写作), 只标卷面级「新高考新增」不标年
            const label = solid ? first + " 新增" : "新高考新增";
            kids.push(dot(cx, PRES.in, solid));
            kids.push(xi[first] >= 2 ? txt(cx - 7, label, PRES.in, "right") : txt(cx + 7, label, PRES.in, "left"));
          }
          return { type: "group", children: kids };
        },
        data: rows.map((r, i) => [r.pres.length ? xi[r.pres[0]] : 0, i]),
      }],
    }, true);
    const ret = items.filter(x => x.signal === "retired").map(x => x.question_type);
    const intro = items.filter(x => x.signal === "introduced").map(x => x.question_type);
    const gaps = items.filter(x => x.extraction_gap).map(x => x.question_type);
    // a11y: 动态 aria-label(题型数+信号分类) + sr-only 表(题型→信号+存续年份) — 复用本函数 rows/SIG
    const skel = items.filter(x => x.signal === "skeleton").map(x => x.question_type);
    setAria("bk-trend",
      `题型结构存续时间带(辽宁卷 ${years[0]}–${years[years.length - 1]} 年, 共 ${list.length} 题型): ` +
      `骨架常驻 ${skel.length} 种, 真退场 ${ret.length} 种(${ret.join("、") || "无"}), 真登场 ${intro.length} 种(${intro.join("、") || "无"})`);
    setSrTable("bk-trend", "题型结构演变 — 各题型存续年份 · 信号",
      ["题型", "信号", "存续年份", "提取不全"], rows.map(x =>
        [x.question_type, (SIG[x.signal] || SIG.unregistered).t, fmtRuns(x.runs) || "无", x.extraction_gap ? "是(年份仅样本)" : "否"]));
    G.$("#bk-trendnote").innerHTML = `<b>结构真值</b>(题型存续时间带 · 登退场信号由<b>卷面结构</b>定非数据): `
      + `蓝横带=存续区间(<b>万变不离其宗</b>: 骨架题型跨两卷制常驻) · <b style="color:${PRES.out}">红点=真退场</b>(${ret.join("、") || "无"}: 新高考取消) · <b style="color:${PRES.in}">绿点=真登场</b>(${intro.join("、") || "无"}: 新高考新增) · 竖虚线=${REFORM} 新高考改革。`
      + `<br><small class="muted">注 淡色虚线带·段=提取不全或该年未登记(${gaps.join("、") || "无"}): 卷面常驻/确有但本项目未抽全 → <b>存续年仅样本, 不作首末考年信号</b>(听力≠登场2021, 续写真登场但登场年不可信); 空心点=登/退场年不可信, 只作卷面级信号。</small>`;
  }

  function renderCognitiveSkill(cs) {
    // 设问类型「怎么想」跨era演变 (单一计算点: service 已算 by_era + reliability, 前端只渲染)。
    // #5 降维: 旧era(n=85 分布可靠)=实心条(真值, 推断行=本图唯一红=你该主攻); 新era(n<30
    // distribution_reliable=false)=空心 scatter 目标刻度(描边 --down)=方向性, 不再画等宽第二组条冒充可信精度。
    const byEra = (cs && cs.by_era) || {};
    const oldRows = byEra[ERA_OLD] || [], newRows = byEra[ERA_NEW] || [];
    if (!oldRows.length && !newRows.length) { G.$("#bk-cog").innerHTML = '<p class="muted">暂无设问类型数据</p>'; return; }
    const skills = [];
    [oldRows, newRows].forEach(rs => rs.forEach(r => { if (!skills.includes(r.label)) skills.push(r.label); }));
    const pctOf = (rs, label) => { const x = rs.find(r => r.label === label); return x ? x.pct : 0; };
    const nOf = (rs, label) => { const x = rs.find(r => r.label === label); return x ? x.n : 0; };
    const cats = skills.slice().reverse();
    const relNew = (cs && cs.reliability && cs.reliability[ERA_NEW]) || {};
    const newOK = relNew.distribution_reliable !== false;   // 缺省视为可信; 仅显式 false 才降级
    const maxNew = Math.max(...newRows.map(r => r.pct), 0);
    charts.cog = G.initChart(G.$("#bk-cog"));
    charts.cog.setOption({
      grid: { left: 4, right: 56, top: 26, bottom: 8, containLabel: true },
      legend: { top: 0, right: 0, textStyle: { fontSize: 10 }, itemWidth: 12, itemHeight: 8 },
      xAxis: { type: "value", axisLabel: { formatter: "{value}%" }, splitLine: { lineStyle: { color: "rgba(128,128,128,0.12)" } } },
      yAxis: { type: "category", data: cats, axisTick: { show: false }, axisLine: { show: false } },
      tooltip: {
        trigger: "axis", axisPointer: { type: "shadow" },
        formatter: ps => `${ps[0].name}<br/>` + ps.map(p => {
          const v = Array.isArray(p.value) ? p.value[0] : p.value;
          const n = p.seriesIndex === 0 ? nOf(oldRows, p.name) : nOf(newRows, p.name);
          const tag = p.seriesIndex === 1 && !newOK ? " · 方向性" : "";
          return `${p.marker}${p.seriesName}: ${v}% · n=${n}${tag}`;
        }).join("<br/>"),
      },
      series: [
        { name: "旧课标II 15–20", type: "bar", barWidth: "52%", data: cats.map(s => ({ value: pctOf(oldRows, s),
          // 实心=真值; 推断=--up (本图唯一红=主攻重点), 其余=--down
          itemStyle: { color: s === "推断" ? C.up : C.blue, borderRadius: [0, 3, 3, 0] } })),
          label: { show: true, position: "right", formatter: p => p.value ? `${p.value}%` : "", fontSize: 10, color: INK3 } },
        newOK
          ? { name: "新高考II 21+", type: "bar", data: cats.map(s => pctOf(newRows, s)),
              itemStyle: { color: C.blue, borderRadius: [0, 3, 3, 0] },
              label: { show: true, position: "right", formatter: p => p.value ? `${p.value}%` : "", fontSize: 10, color: INK3 } }
          : { name: "2021+ 方向 (n<30)", type: "scatter", z: 3, symbol: "circle", symbolSize: 12,
              data: cats.map(s => [pctOf(newRows, s), s]),
              itemStyle: { color: "#fff", borderColor: C.blue, borderWidth: 2 },   // 空心目标刻度=方向性 (描边 --down)
              label: { show: true, position: "top", distance: 3, fontSize: 10, color: C.blue,
                formatter: p => { const v = p.value[0]; return (v === maxNew ? "2021+ 方向 " : "") + "▸" + v + "%"; } } },
      ],
    }, true);
    const oInf = pctOf(oldRows, "推断"), nInf = pctOf(newRows, "推断");
    // a11y: 动态 aria-label(双era推断迁移概览) + sr-only 表(技能×双era占比/题数) — 复用 skills/pctOf/nOf/newOK
    const ariaSkills = skills.slice();   // skills 原序; cats 是其 reverse 仅供 echarts 自下而上
    setAria("bk-cog",
      `设问类型分布对比(辽宁卷, 旧课标II 2015–20 实心条 vs 新高考II 21+${newOK ? "" : " 空心方向标记·样本不足"}): ` +
      `推断占比 旧 ${oInf}% → 新 ${nInf}%; 共 ${ariaSkills.length} 类认知技能`);
    setSrTable("bk-cog", `设问类型「怎么想」 — 旧课标II vs 新高考II${newOK ? "" : "(新era样本不足, 方向性信号)"}`,
      ["认知技能", "旧课标II 占比", "旧 题数", "新高考II 占比", "新 题数"],
      ariaSkills.map(s => [s, pctOf(oldRows, s) + "%", "n=" + nOf(oldRows, s), pctOf(newRows, s) + "%", "n=" + nOf(newRows, s)]));
    const rel = (cs && cs.reliability) || {};
    const nNew = (rel[ERA_NEW] || {}).n || newRows.reduce((a, r) => a + r.n, 0);
    const nOld = (rel[ERA_OLD] || {}).n || oldRows.reduce((a, r) => a + r.n, 0);
    // 坑(2026-07-04 全数据审计): 旧版硬编码"仅2023单年", 后来2024数据接入(n=15→28)后文案未同步,
    // 长期显示"仅2023单年n=28"这种自相矛盾的过时描述。改读后端真实年份列表(cognitive_skill.py
    // reliability[era].years), 不再硬编码具体年份(单一计算点, 防再漂移)。
    const newYears = (rel[ERA_NEW] || {}).years || [];
    const newYearsLabel = newYears.length ? newYears.join("/") + "年" : "近年";
    // 诚实叙事 — 新era不可信时 banner 显著 + 把"迁移真值"降级为"方向性信号"(样本不足不作趋势结论)
    const banner = !newOK
      ? `<div class="caveat-banner"><span class="cb-tag">样本不足</span><span>新高考II 仅 ${newYearsLabel} n=${nNew}(&lt;30) = <b>方向性信号, 非精确分布/趋势结论</b>; 其余年份暂无设问思维标注数据。</span></div>`
      : "";
    const inf = !newOK
      ? `方向性参考(非趋势结论): 推断占比 旧课标II ${oInf}% → 新高考II(${newYearsLabel}) ${nInf}%`
      : `命题哲学迁移: <b style="color:${C.up}">推断 ${oInf}% → ${nInf}%</b>(细节下行)——新高考重高阶推断`;
    // 坑(2026-07-05 教师视角审计): 推断/理解具体信息/理解主旨要义/理解词汇 术语在本页首次
    // 出现无解释; 真题特点页已有完整讲解卡片, 此处加一句跳转链接而非重复整套讲解。
    // 坑(2026-07-07 知识点颗粒度追问): 此前硬编码"这4种", 理解目的接入后实际是5种未同步跟着改
    // (同坑16的"仅2023单年"教训); 改读 skills.length 动态拼, 并显式披露官方7项里还缺几项
    // (cognitive_skill_distribution 新增 missing_categories 字段, 单一计算点)。
    const missing = (cs && cs.missing_categories) || [];
    const missingNote = missing.length
      ? `<br><small class="muted">官方定义7项理解性技能, 当前真题解析数据覆盖${skills.length}项; ${missing.join("/")}这${missing.length}项当前无可得教研解析显式标注真题样本(不臆测补齐)。</small>`
      : "";
    G.$("#bk-cognote").innerHTML = `<a href="#/zhenti" style="font-size:11px;">这${skills.length}种"怎么想"是什么意思? →</a><br>` + banner
      + `题型标签直接来自教研解析, 不靠 AI 猜(详见页尾「数据怎么来的?」)。${inf}。`
      + `<br><small class="muted">实心条=旧课标II ${nOld}子题(2015–20六年, 分布可靠), <b style="color:${C.up}">红条=推断(主攻重点)</b>; 空心圆=新高考II 方向(仅${newYearsLabel} n=${nNew})。2021 年源数据混入外省卷, 已按省份核验剔除。</small>`
      + missingNote;
  }

  async function loadCross(by) {
    if (!crossCache[by]) crossCache[by] = await fetchJSON("/api/exam_point/cognitive_by_content?by=" + by).catch(() => ({ by_content: {} }));
    return crossCache[by];
  }

  function renderCrossToggle() {
    const pill = k => `<button class="bk-pill ${state.cross === k ? "on" : ""}" data-cross="${k}">${CROSS_LBL[k]}</button>`;
    G.$("#bk-crosstoggle").innerHTML = `${pill("genre")}${pill("theme_l2")}${pill("theme_context")}`;
    G.$$("#bk-crosstoggle [data-cross]").forEach(b => b.onclick = async () => {
      state.cross = b.dataset.cross; renderCrossToggle();
      renderCogCross(await loadCross(state.cross));
    });
  }

  function renderCogCross(d) {
    // 设问技能 × 题材/主题 交叉 (单一计算点: service 已算; 前端只渲染 100%-堆叠条, 应用文全一色=纯找信息一眼可见)。
    const bc = (d && d.by_content) || {};
    const cats = Object.keys(bc);
    if (!cats.length) { G.$("#bk-cross").innerHTML = '<p class="muted">暂无交叉数据</p>'; return; }
    const ordered = cats.slice().sort((a, b) => bc[a].total - bc[b].total); // 横向条 y 轴自下而上 → 大类在上
    const skills = ["推断", "理解具体信息", "理解主旨要义", "理解词汇"];
    const pctOf = (cat, sk) => { const s = (bc[cat].skills || []).find(x => x.label === sk); return s ? s.pct : 0; };
    charts.cross = G.initChart(G.$("#bk-cross"));
    charts.cross.setOption({
      grid: { left: 4, right: 8, top: 22, bottom: 6, containLabel: true },
      legend: { top: 0, textStyle: { fontSize: 10 }, itemWidth: 11, itemHeight: 8 },
      xAxis: { type: "value", max: 100, axisLabel: { formatter: "{value}%" }, splitLine: { show: false } },
      yAxis: { type: "category", data: ordered.map(c => `${c}${bc[c].thin ? " 注" : ""} · n${bc[c].total}`), axisTick: { show: false }, axisLine: { show: false }, axisLabel: { fontSize: 11 } },
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, formatter: ps => ps[0].name + "<br/>" + ps.filter(p => p.value > 0).map(p => `${p.marker}${p.seriesName}: ${p.value}%`).join("<br/>") },
      series: skills.map(sk => ({ name: sk, type: "bar", stack: "t", barWidth: "62%", data: ordered.map(c => pctOf(c, sk)), itemStyle: { color: SKILL_COLOR[sk] } })),
    });
    const cov = d.n_matched && d.n_subq_total ? `${d.n_matched}/${d.n_subq_total}` : "?";
    // a11y: 动态 aria-label(交叉维度+题材数+首项构成) + sr-only 表(题材×各技能占比) — 复用 ordered/skills/pctOf/bc
    const ariaCats = ordered.slice().reverse();   // ordered 升序给 echarts 自下而上; 读屏按 total 大→小
    const top = ariaCats[0];
    setAria("bk-cross",
      `题材与思维交叉(${CROSS_LBL[state.cross]} · 仅旧课标II 2015–20截面 辽宁卷, 共 ${ariaCats.length} 类语篇): ` +
      (top ? `${top} 占比最大, ${skills.map(sk => `${sk} ${pctOf(top, sk)}%`).join(", ")}` : "无数据"));
    setSrTable("bk-cross", `题材 × 思维 — ${escHtml(CROSS_LBL[state.cross])} · 仅旧课标II 2015–20截面`,
      ["语篇题材", "子题数", ...skills], ariaCats.map(c => [c, "n=" + bc[c].total, ...skills.map(sk => pctOf(c, sk) + "%")]));
    // #14: era 锁醒目徽章 (F卡是唯一旧era截面卡, 防夹在双era视图里被误读为新高考结论)
    G.$("#bk-crosslbl").innerHTML = `${CROSS_LBL[state.cross]} <span style="background:var(--accent-wash);color:var(--accent-ink);padding:0 6px;border-radius:8px;font-size:10px;white-space:nowrap;">仅旧课标II 2015–20截面 · 2021+数据尚不足</span>`;
    // 坑(2026-07-05 根因审计): 原硬编码"应用文/文学艺术≈纯找信息(0推断), 说明文/记叙文最考推断"
    // 是字面写死的类别名+断言, 用户切换 renderCrossToggle(题材/主题群/主题语境)后图表已换数据, 这
    // 句文案不跟着变(与已修的语法考点caption同一bug)。改成从 bc/ordered/pctOf(本函数已有, 43行上方
    // aria-label 已这样动态算)现算最低/最高推断占比类别, 跟随 state.cross 当前维度。
    const byInfer = ordered.map(c => ({ c, v: pctOf(c, "推断") })).sort((a, b) => b.v - a.v);
    const highest = byInfer[0], lowest = byInfer[byInfer.length - 1];
    // 坑(2026-07-06 数据关联设计审查): D卡已有卡内联行链接解释设问技能术语, F卡同一组术语首现
    // 在图例/tooltip里, 只靠区块级公共链接兜底, 位置不对等——补一份同款卡内联行链接, 与D卡一致。
    G.$("#bk-crossnote").innerHTML = `<a href="#/zhenti" style="font-size:11px;">这4种"怎么想"是什么意思? →</a><br>`
      + (highest && lowest && highest.c !== lowest.c
      ? `老师分流: 哪类${CROSS_LBL[state.cross]}考哪种思维。<b>${lowest.c} ≈ 纯找信息(${lowest.v}%推断)</b>, <b style="color:${C.up}">${highest.c}最考推断(${highest.v}%)</b> → 精读分流训练重心。`
      : `老师分流: 哪类${CROSS_LBL[state.cross]}考哪种思维, 见下方堆叠条各类推断占比 → 精读分流训练重心。`)
      + `<br><small class="muted">注 技能侧=教研解析标签(真值) · 题材侧=AI 标注(两个 AI 一致才计入, 看方向)。粒度=子题数(同语篇题材重复计入), 覆盖 ${cov}; 时间范围锁 2015–20(2021+ 数据尚不足); n&lt;10格注仅参考。</small>`;
  }

  function wire() {
    G.$("#bk-filter").innerHTML = filterBar();
    G.$$("#bk-filter [data-era]").forEach(b => b.onclick = () => { state.era = b.dataset.era; G.$("#bk-filter").innerHTML = filterBar(); wire(); renderDist(); renderShift(); });
    const sel = G.$("#bk-dim");
    if (sel) sel.onchange = () => { state.dim = sel.value; G.$("#bk-filter").innerHTML = filterBar(); wire(); renderDist(); renderShift(); };
  }

  // #5: 给每张含 echarts 实例的卡追加 PNG 导出按钮 (getInstanceByDom 自动跳过非图卡)
  function wireExports() {
    if (!window.echarts) return;
    G.$$(".bk-card").forEach(card => {
      if (card.querySelector(".bk-export")) return;        // 防重复
      let inst = null;
      card.querySelectorAll("div[id]").forEach(d => { const i = echarts.getInstanceByDom(d); if (i) inst = i; });
      if (!inst) return;
      const h = card.querySelector(".bk-h");
      if (!h) return;
      const full = ((h.querySelector("span") || {}).textContent || "图").trim();
      const title = full.split(" ")[0];
      const btn = document.createElement("button");
      btn.className = "bk-export"; btn.innerHTML = G.icon("download") + " PNG"; btn.title = "导出本图 PNG";
      // P2-3 PNG 自包含: 传卡名 meta, 导出图离开页面自带标题+来源脚注
      btn.onclick = () => G.exportChartPNG(inst, `辽宁卷_${title}.png`, { title: `辽宁高考 · ${full}` });
      h.appendChild(btn);
    });
    const pb = G.$("#bk-print");
    if (pb) pb.onclick = () => G.printWithCharts();   // RC1: 打印保图(echarts→PNG注入)
  }

  // 结论先行 (#6): 3 行结构化 — 每行 = 数据判断(全部取自已 fetch 的 service 数据, 零 hardcode) + 看证据锚点。
  function renderVerdict(dist, cog, stage) {
    const el = G.$("#bk-verdict"); if (!el) return;
    const items = [];
    // a. 考查词学段 → 主攻高中新增 (证据=真题特点页的词学段实证)
    if (stage && !G.isErr(stage) && stage.foundation_pct != null) {
      // P2-6 微缩学段带: GZ.stageMiniBand 单渲染点 (common.js, 防多处分段实现漂移); 仅此一处, 结论卡微图 ≤1
      const band = G.stageMiniBand ? G.stageMiniBand(stage) : "";
      items.push({
        text: `考查词 <strong>${stage.foundation_pct}% 初中前已学</strong>${band} → 词汇主攻高中新增的 <strong>${stage.senior_pct}%</strong>`,
        // 坑(2026-07-05 教师视角审计): 本条"看证据"跳去另一页(真题特点), b/c两条"看证据↓"是
        // 页内滚动——同一"看证据"字样+相似箭头容易让人以为3条行为一致。改用 ↗(离开当前页
        // 的通用符号)区别于 ↓(页内滚动), 不改变既有配色/无下划线的链接风格(与全站其它跳页
        // 链接一致, 如.zt-nextlink)。
        link: `<a class="bk-vlink" href="#/zhenti">看证据 ↗ 真题特点</a>`,
      });
    }
    // b. 主导设问思维 → 练怎么想 (锚区「怎么考」; 样本量诚实: n<30 带 n+方向性标注)
    const byEra = (cog && cog.by_era) || {};
    const newEraKey = Object.keys(byEra).find(k => /2021|新高考/.test(k)) || Object.keys(byEra)[0];
    const oldEraKey = Object.keys(byEra).find(k => k !== newEraKey);
    const skills = newEraKey ? byEra[newEraKey] : null;
    if (Array.isArray(skills) && skills.length) {
      const top = skills.slice().sort((a, b) => (b.pct || 0) - (a.pct || 0))[0];
      const rel = ((cog || {}).reliability || {})[newEraKey] || {};
      const relTag = rel.distribution_reliable === false ? ` · n=${rel.n} 方向性` : "";
      // 坑(2026-07-05 教师视角审计): 结论条原只报"占比最高的技能", 但下方D图始终把"推断"
      // 标红当"主攻重点"(该项跨era涨幅最大, 见 renderCognitiveSkill 的 s==="推断" 判断) ——
      // 当占比最高的技能不是推断时, 结论条与图表视觉强调的技能不一致。此时把推断的涨幅一并
      // 说清楚, 结论与图表对齐, 不再各说各话。
      const infer = skills.find(s => s.label === "推断");
      const inferOld = oldEraKey ? (byEra[oldEraKey] || []).find(s => s.label === "推断") : null;
      const risingNote = (infer && top.label !== "推断" && inferOld)
        ? ` · <strong>推断</strong>题增长快(${inferOld.pct}%→${infer.pct}%), 最值得针对性练`
        : "";
      // 坑(2026-07-06 数据关联设计审查): D图内部已用实心/空心区分置信度, 但结论卡把n<30方向性
      // 推断与真值统计视觉权重拉平——weak标记复用同一份rel.distribution_reliable判断, 不新增计算。
      if (top && top.label) items.push({
        text: `设问以 <strong>${top.label}</strong> 为主 (${top.pct}%${relTag})${risingNote} → 备课重心=练「怎么想」`,
        link: `<button type="button" class="bk-vlink" data-goto="bk-sect-how">看证据 ↓</button>`,
        weak: rel.distribution_reliable === false,
      });
    }
    // c. 最大命题迁移 (锚区「怎么变」; 扫 genre+theme_l2 细粒度维度, theme_context 3 大类过粗不参与)
    const sd = (dist && dist.shift && dist.shift.by_dimension) || {};
    let mv = null;
    ["genre", "theme_l2"].forEach(k => (sd[k] || []).forEach(m => { if (!mv || Math.abs(m.delta) > Math.abs(mv.delta)) mv = m; }));
    if (mv && Math.abs(mv.delta) >= 1) {
      // 坑(2026-07-06 数据关联设计审查): 原c条完全不显示样本量, 比b条(有n+方向性标注)更不透明——
      // 复核发现c条引用样本可能比b条更小却毫无提示。exam_point_shift已补n_new/n_old(同era分布
      // 口径, 30与MIN_DISTRIBUTION_SAMPLE同一约定), 现补上并按同阈值弱化标记。
      const MIN_SAMPLE = 30;
      const nNew = mv.n_new || 0;
      items.push({
        text: `最大命题迁移: <strong>${mv.label}</strong> ${mv.delta >= 0 ? "升" : "降"} ${Math.abs(mv.delta).toFixed(1)}pt (n=${nNew}${nNew < MIN_SAMPLE ? " 方向性" : ""})`,
        link: `<button type="button" class="bk-vlink" data-goto="bk-sect-change">看证据 ↓</button>`,
        weak: nNew < MIN_SAMPLE,
      });
    }
    if (!items.length) { el.style.display = "none"; return; }
    el.innerHTML = `<div class="bk-verdict-h">研判结论 · 辽宁新高考 II 卷</div>`
      + `<ul class="bk-verdict-list">` + items.map(i => `<li${i.weak ? ' class="bk-verdict-weak"' : ""}>${i.text} ${i.link}</li>`).join("") + `</ul>`
      + `<p class="bk-verdict-foot">题材/主题由 AI 标注(看方向, 非官方真值); 新老卷制分开统计不混平均 — 详见页尾「数据怎么来的?」。</p>`;
    G.$$("#bk-verdict [data-goto]").forEach(b => b.onclick = () => {
      const t = document.getElementById(b.dataset.goto);
      if (t) t.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  registerTab("beike", async () => {
    G.$("#content").innerHTML = shell();
    const echartsOk = await G.ensureECharts();   // RC1: 轮询等 echarts 就绪, 根治 load 竞态静默空白
    const [dist, qt, cog, stage] = await Promise.all([
      // RC1/D0: distribution 是驾驶舱主数据, 失败必抛 → route() 显式错误态 (不冒充空壳掩盖后端故障)
      fetchJSON("/api/exam_point/distribution"),
      fetchJSON("/api/trend/question_type_presence").catch(() => ({ by_question_type: [] })),
      fetchJSON("/api/exam_point/cognitive_skill").catch(() => ({ by_era: {} })),
      G.fetchSafe("/api/k12/tested_word_stage"),  // 结论行 a 的考查词学段
    ]);
    state.dist = dist;
    renderVerdict(dist, cog, stage);   // 结论先行: 顶部 3 行数据研判 + 看证据锚点 (北极星 ① 命题研判)
    wire();
    const cross = await loadCross(state.cross);
    if (echartsOk) {
      renderDist(); renderTrend(qt); renderCognitiveSkill(cog);
      renderCrossToggle(); renderCogCross(cross);
    } else {
      G.chartLoadError(G.$("#bk-dist"));   // D0诚实: echarts 真失败显式报错, 不冒充空白
    }
    renderShift();   // B 图自带降级: 宽屏=哑铃图 / 窄屏·无 echarts=文本行
    wireExports();   // #5: 图卡追加 PNG 导出 + 打印按钮接线
    if (!window.__rzBeike) { window.__rzBeike = 1; window.addEventListener("resize", () => Object.values(charts).forEach(c => c && c.resize())); }  // RC1: 只绑一次防切tab累积泄漏
    if (!window.__mqBeike) {   // 跨 820px 断点时 B 图在哑铃图/文本行间切换 (只绑一次)
      window.__mqBeike = 1;
      const onMq = () => { if (G.$("#bk-shift") && state.dist) renderShift(); };
      if (SHIFT_MQ.addEventListener) SHIFT_MQ.addEventListener("change", onMq);
      else if (SHIFT_MQ.addListener) SHIFT_MQ.addListener(onMq);
    }
  });
})();
