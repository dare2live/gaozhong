/* 备课工作流「考点驾驶舱」— A考点分布 / B命题迁移 / C命题趋势 / D设问类型 / E词汇热力 (第七阶段 viz 7.1).
 *
 * 铁律1 单一计算点: 全部 fetch /api/* service 产物, 前端**只渲染**; 迁移(B)的 era 间做差也在
 *   service 算 (exam_point_shift, 审计HIGH#18 修; 前端只渲染 shift.by_dimension)。绝不在前端聚合/做差。
 * 分层非平均: 按卷制 era 分段看, 不混历史均值。
 * 样本量诚实: 趋势读 service 的 reliable 旗, 不可信→灰显虚线 + "样本不足" banner, 不画实斜率。
 * 词频≠考点: 词汇热力标题写"词频热力"(坑12 澄清)。
 * ECharts 仅渲染层 (CDN), 数据仍 service 单算。
 */
(function () {
  const G = window.GZ;
  if (!G || !G.registerTab) return;
  const { fetchJSON, registerTab } = G;

  const ERA_NEW = "2021+_新高考II";
  const ERA_OLD = "2015-2020_旧课标II";
  const DC = (window.GZ_CAT && window.GZ_CAT.dim) || {};   // 维度基础标签单一来源 category-config.js (防 beike/teacher/jiangke 漂移)
  const DIM_LABEL = { genre: DC.genre, theme_context: DC.theme_context, theme_l2: DC.theme_l2 + "·课标10群" };
  // 图表数据编码色 — 锚 design-system 令牌族值 (--down/--accent-ink; echarts 需 hex 故写值非 var, 跨图一致)
  const C = { blue: "#1F5F94", blueL: "#85B7EB", up: "#9C2C20", upBg: "#FAECE7", down: "#1F5F94", downBg: "#E6F1FB", grey: "#B4B2A9" };
  const STATUS = (window.GZ_CAT && window.GZ_CAT.examStatus) || {};   // 考点状态色单一来源 category-config.js

  let state = { era: ERA_NEW, dim: "theme_l2", dist: null, cross: "genre" };
  const charts = {};
  const crossCache = {};

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
  function setAria(chartId, label) { const el = G.$("#" + chartId); if (el) el.setAttribute("aria-label", label); }
  // 设问技能堆叠色 (推断=强调红, 与 D 区一致); 固定堆叠顺序让"推断"锚左边便于跨题材比
  const SKILL_COLOR = (window.GZ_CAT && window.GZ_CAT.skill) || {};   // 设问技能色单一来源 category-config.js
  const CROSS_LBL = { genre: DC.genre, theme_l2: DC.theme_l2, theme_context: "课标" + DC.theme_context };

  function shell() {
    return `
<h2 style="margin:0 0 2px;">备课 · 考点驾驶舱 <button id="bk-print" class="bk-export" title="打印/导PDF本页研判">${G.icon("printer")} 打印本页</button></h2>
<p class="muted" style="margin:0 0 14px;font-size:13px;">辽宁卷锚定 · 按卷制 era 分层(非历史平均) · 数据全来自 service 单一计算点, 前端不重算 · 各图右上可单独导出 PNG</p>
<div id="bk-filter" class="bk-filter"></div>
<div class="bk-grid">
  <section class="bk-card"><div class="bk-h"><span>A 考点分布 <small id="bk-dimname">主题群</small></span><span class="bk-src">/api/exam_point/distribution</span></div><div id="bk-dist" role="img" aria-label="考点分布条形图: 各课标主题群在辽宁卷的出现占比" style="height:300px;"></div></section>
  <section class="bk-card"><div class="bk-h"><span>B 命题迁移 <small>2015–20 → 2021+</small></span><span class="bk-src">/api/exam_point/distribution · shift</span></div><div id="bk-shift"></div></section>
  <section class="bk-card"><div class="bk-h"><span>C 题型结构演变 · 卷制presence</span><span id="bk-relbadge"></span></div><div id="bk-trend" role="img" aria-label="题型结构演变矩阵: 各题型在两个卷制时期的在场情况" style="height:240px;"></div><p id="bk-trendnote" class="muted" style="font-size:12px;margin:8px 0 0;"></p></section>
  <section class="bk-card"><div class="bk-h"><span>D 设问类型 · 怎么想 <small>子题级·教研显式标签</small></span><span class="bk-src">/api/exam_point/cognitive_skill</span></div><div id="bk-cog" role="img" aria-label="设问类型分布: 旧课标与新高考的认知技能占比对比" style="height:240px;"></div><p id="bk-cognote" class="muted" style="font-size:12px;margin:8px 0 0;"></p></section>
  <section class="bk-card"><div class="bk-h"><span>F 题材 × 思维 <small id="bk-crosslbl">体裁·2015–20截面</small></span><span class="bk-src">/api/exam_point/cognitive_by_content</span></div><div id="bk-crosstoggle" style="margin:2px 0 6px;"></div><div id="bk-cross" role="img" aria-label="题材与思维交叉: 各类语篇考查的认知技能分布" style="height:248px;"></div><p id="bk-crossnote" class="muted" style="font-size:12px;margin:8px 0 0;"></p></section>
  <section class="bk-card"><div class="bk-h"><span>E 词汇热力 <small>词频非考点</small></span><span class="bk-src">/api/heatmap/vocab</span></div><div id="bk-heat" role="img" aria-label="词汇热力图: 字母开头的词频分布(词频非考点)" style="height:300px;"></div></section>
</div>`;
  }

  function filterBar() {
    const eraPill = (id, label) => `<button class="bk-pill ${state.era === id ? "on" : ""}" data-era="${id}">${label}</button>`;
    const dimOpt = Object.keys(DIM_LABEL).map(k => `<option value="${k}" ${state.dim === k ? "selected" : ""}>${DIM_LABEL[k]}</option>`).join("");
    const eras = state.dist ? state.dist.eras : [ERA_NEW, ERA_OLD];
    // 样本充足性读 service 透传的 sufficiency.distribution_eligible (scope.MIN_DISTRIBUTION_SAMPLE 已 service 算), 前端不重判30 (Rule1)
    const suff = (state.dist && state.dist.sufficiency && state.dist.sufficiency[state.era]) || {};
    const n = suff.n_total != null ? suff.n_total
      : (eras.includes(state.era) && state.dist ? (state.dist.distribution[state.era].genre || []).reduce((a, x) => a + x.n, 0) : 0);
    const ok = suff.distribution_eligible != null ? suff.distribution_eligible : n >= 30;
    return `
<span class="bk-flabel">卷制</span>${eraPill(ERA_NEW, "2021+ 新高考II")}${eraPill(ERA_OLD, "2015–2020")}
<span class="bk-lock">辽宁卷·锁定</span>
<span class="bk-flabel" style="margin-left:8px;">维度</span><select id="bk-dim">${dimOpt}</select>
<span class="bk-suff ${ok ? "ok" : "warn"}">${ok ? "分布可用 · " + n + "题" : "样本不足 · " + n + "题"}</span>`;
  }

  function renderDist() {
    const rows = (state.dist.distribution[state.era][state.dim] || []).slice().reverse();
    G.$("#bk-dimname").textContent = DIM_LABEL[state.dim];
    charts.dist = echarts.getInstanceByDom(G.$("#bk-dist")) || echarts.init(G.$("#bk-dist"));
    charts.dist.setOption({
      grid: { left: 4, right: 44, top: 8, bottom: 8, containLabel: true },
      xAxis: { type: "value", max: Math.max(...rows.map(r => r.pct)) * 1.15, axisLabel: { formatter: "{value}%" }, splitLine: { lineStyle: { color: "rgba(128,128,128,0.12)" } } },
      yAxis: { type: "category", data: rows.map(r => r.label), axisTick: { show: false }, axisLine: { show: false } },
      tooltip: { trigger: "axis", formatter: p => `${p[0].name}<br/>${p[0].value}% · n=${rows[p[0].dataIndex].n}` },
      series: [{
        type: "bar", data: rows.map(r => r.pct), barWidth: "62%",
        itemStyle: { color: C.blue, borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: "right", formatter: p => `${p.value}% · n=${rows[p.dataIndex].n}`, fontSize: 11, color: "#888" },
      }],
    });
    // a11y: 动态 aria-label(图名+维度+era+前几项实值) + sr-only 数据表 — 复用本函数已用的 rows(原序非 reverse)
    const ariaRows = rows.slice().reverse();   // rows 已 reverse 给 echarts(自下而上); 读屏按占比大→小线性读
    const dimName = DIM_LABEL[state.dim];
    setAria("bk-dist",
      `考点分布条形图(${dimName} · ${state.era} 辽宁卷): ` +
      (ariaRows.slice(0, 4).map(r => `${r.label} ${r.pct}%`).join(", ") || "无数据") +
      (ariaRows.length > 4 ? ` 等共 ${ariaRows.length} 项` : ""));
    setSrTable("bk-dist", `考点分布 — ${escHtml(dimName)} · ${escHtml(state.era)} 辽宁卷`,
      ["类别", "占比", "题数"], ariaRows.map(r => [r.label, r.pct + "%", "n=" + r.n]));
    charts.dist.off("click");
    // #3: 点考点条 → 弹该考点浮窗(关联+真题, 复用#2修好的 exam_point 真题); fallback sendPrompt 下钻
    charts.dist.on("click", p => {
      const cid = `exam_point:${state.dim}:${p.name}`;
      if (G.openPopup) G.openPopup(cid);
      else if (G.sendPrompt) G.sendPrompt(`下钻 ${state.era} 辽宁卷 ${DIM_LABEL[state.dim]}「${p.name}」的真题清单`);
    });
  }

  function renderShift() {
    // 命题迁移在 service 算一次 (Rule1); 前端只渲染 state.dist.shift.by_dimension[dim]
    const rows = ((state.dist.shift || {}).by_dimension || {})[state.dim] || [];
    G.$("#bk-shift").innerHTML = rows.map(r => {
      const up = r.delta >= 0, col = up ? C.up : C.down, bg = up ? C.upBg : C.downBg;
      return `<div class="bk-shift-row"><span class="bk-shift-k">${r.label}</span>
        <span class="bk-shift-v">${r.then_pct}% → <b>${r.now_pct}%</b></span>
        <span class="bk-delta" style="color:${col};background:${bg};">${up ? "↑" : "↓"} ${Math.abs(r.delta)}pt</span></div>`;
    }).join("");
  }

  function renderTrend(p) {
    // 题型×年份 presence 热力(结构真值, 粒度无关; v2: signal 由卷面结构config定, extraction_gap 淡色虚线诚实标)。
    const items = (p && p.by_question_type) || [];
    const SIG = { skeleton: { c: C.blue, t: "骨架·两卷制常驻" }, retired: { c: "#BE3A2B", t: "真退场·卷面取消" }, introduced: { c: "#2E7D54", t: "真登场·卷面新增" }, unregistered: { c: C.grey, t: "未登记结构" } };
    const ord = { skeleton: 0, retired: 1, introduced: 2, unregistered: 3 };
    const list = items.slice().sort((a, b) => (ord[a.signal] ?? 9) - (ord[b.signal] ?? 9));
    const all = items.flatMap(x => [...(x.old_years || []), ...(x.new_years || [])]);
    if (!all.length) { G.$("#bk-trend").innerHTML = "<p class='muted'>无题型数据</p>"; return; }
    const years = []; for (let y = Math.min(...all); y <= Math.max(...all); y++) years.push(y);
    const qts = list.map(x => x.question_type + (x.extraction_gap ? " 注" : ""));
    const data = [];
    list.forEach((x, qi) => {
      const pres = new Set([...(x.old_years || []), ...(x.new_years || [])]);
      const sig = SIG[x.signal] || SIG.unregistered, gap = x.extraction_gap;
      years.forEach((y, yi) => {
        if (pres.has(y)) data.push({ value: [yi, qi, 1], itemStyle: { color: sig.c, opacity: gap ? 0.32 : 1, borderColor: gap ? "#888" : "#fff", borderWidth: 1, borderType: gap ? "dashed" : "solid" } });
      });
    });
    G.$("#bk-relbadge").innerHTML = `<span class="bk-suff ok">结构真值·卷面config掩码</span>`;
    charts.trend = echarts.getInstanceByDom(G.$("#bk-trend")) || echarts.init(G.$("#bk-trend"));
    charts.trend.setOption({
      grid: { left: 4, right: 12, top: 10, bottom: 22, containLabel: true },
      xAxis: { type: "category", data: years, splitArea: { show: true }, axisLabel: { fontSize: 10 } },
      yAxis: { type: "category", data: qts, axisLabel: { fontSize: 10 } },
      tooltip: { formatter: c => { const x = list[c.value[1]]; return `${x.question_type} · ${years[c.value[0]]}<br/>${(SIG[x.signal] || SIG.unregistered).t}${x.extraction_gap ? "<br/><b>注 提取不全·该年仅样本非首末考年</b>" : ""}`; } },
      series: [{ type: "heatmap", data, label: { show: false } }],
    }, true);
    const ret = items.filter(x => x.signal === "retired").map(x => x.question_type);
    const intro = items.filter(x => x.signal === "introduced").map(x => x.question_type);
    const gaps = items.filter(x => x.extraction_gap).map(x => x.question_type);
    // a11y: 动态 aria-label(题型数+信号分类) + sr-only 表(题型→信号+在场年份) — 复用本函数 list/SIG/all
    const skel = items.filter(x => x.signal === "skeleton").map(x => x.question_type);
    setAria("bk-trend",
      `题型结构演变矩阵(辽宁卷 ${Math.min(...all)}–${Math.max(...all)} 年, 共 ${list.length} 题型): ` +
      `骨架常驻 ${skel.length} 种, 真退场 ${ret.length} 种(${ret.join("、") || "无"}), 真登场 ${intro.length} 种(${intro.join("、") || "无"})`);
    setSrTable("bk-trend", "题型结构演变 — 各题型在场年份 · 信号",
      ["题型", "信号", "在场年份", "提取不全"], list.map(x => {
        const yrs = [...new Set([...(x.old_years || []), ...(x.new_years || [])])].sort((a, b) => a - b);
        return [x.question_type, (SIG[x.signal] || SIG.unregistered).t, yrs.join(" ") || "无", x.extraction_gap ? "是(年份仅样本)" : "否"];
      }));
    G.$("#bk-trendnote").innerHTML = `<b>结构真值</b>(题型 presence · signal 由<b>卷面结构</b>定非数据, 粒度无关): `
      + `蓝=骨架两卷制常驻(<b>万变不离其宗</b>) · 红=<b>真退场</b>(${ret.join("、") || "无"}: 新高考取消) · 绿=<b>真登场</b>(${intro.join("、") || "无"}: 新高考新增)。`
      + `<br><small class="muted">注 淡色虚线格=提取不全(${gaps.join("、") || "无"}): 卷面常驻/确有但本项目未抽全 → <b>presence年仅样本, 不作首末考年信号</b>(听力≠登场2021, 续写真登场但登场年不可信)。</small>`;
  }

  function renderCognitiveSkill(cs) {
    // 设问类型「怎么想」跨era演变 (单一计算点: service 已算 by_era + reliability, 前端只渲染双era迁移)。
    const byEra = (cs && cs.by_era) || {};
    const oldRows = byEra[ERA_OLD] || [], newRows = byEra[ERA_NEW] || [];
    if (!oldRows.length && !newRows.length) { G.$("#bk-cog").innerHTML = '<p class="muted">暂无设问类型数据</p>'; return; }
    const skills = [];
    [oldRows, newRows].forEach(rs => rs.forEach(r => { if (!skills.includes(r.label)) skills.push(r.label); }));
    const pctOf = (rs, label) => { const x = rs.find(r => r.label === label); return x ? x.pct : 0; };
    const nOf = (rs, label) => { const x = rs.find(r => r.label === label); return x ? x.n : 0; };
    const cats = skills.slice().reverse();
    const lbl = { show: true, position: "right", formatter: p => p.value ? `${p.value}%` : "", fontSize: 10, color: "#76716A" };
    // #11: 新era reliability — distribution_reliable=false(n<30)时不可把单年噪声渲成可信精度(死线3诚实分层)
    const relNew = (cs && cs.reliability && cs.reliability[ERA_NEW]) || {};
    const newOK = relNew.distribution_reliable !== false;   // 缺省视为可信; 仅显式 false 才降级
    charts.cog = echarts.getInstanceByDom(G.$("#bk-cog")) || echarts.init(G.$("#bk-cog"));
    charts.cog.setOption({
      grid: { left: 4, right: 48, top: 26, bottom: 8, containLabel: true },
      legend: { top: 0, right: 0, textStyle: { fontSize: 10 }, itemWidth: 12, itemHeight: 8 },
      xAxis: { type: "value", axisLabel: { formatter: "{value}%" }, splitLine: { lineStyle: { color: "rgba(128,128,128,0.12)" } } },
      yAxis: { type: "category", data: cats, axisTick: { show: false }, axisLine: { show: false } },
      tooltip: {
        trigger: "axis", axisPointer: { type: "shadow" },
        formatter: ps => `${ps[0].name}<br/>` + ps.map(p =>
          `${p.marker}${p.seriesName}: ${p.value}% · n=${(p.seriesIndex === 0 ? nOf(oldRows, p.name) : nOf(newRows, p.name))}`).join("<br/>"),
      },
      series: [
        { name: "旧课标II 15–20", type: "bar", barGap: "10%", data: cats.map(s => pctOf(oldRows, s)),
          itemStyle: { color: C.grey, borderRadius: [0, 3, 3, 0] }, label: lbl },
        { name: newOK ? "新高考II 21+" : "新高考II 21+ (样本不足)", type: "bar", data: cats.map(s => ({ value: pctOf(newRows, s),
          itemStyle: {
            color: !newOK ? "#C9C4B8" : (s === "推断" ? C.up : C.blue),   // #11 不可信→灰, 推断不抢眼防误读为可信精度
            opacity: newOK ? 1 : 0.5,
            borderColor: newOK ? "#fff" : "#76716A", borderWidth: 1, borderType: newOK ? "solid" : "dashed",
            borderRadius: [0, 3, 3, 0],
          } })), label: lbl },
      ],
    });
    const oInf = pctOf(oldRows, "推断"), nInf = pctOf(newRows, "推断");
    // a11y: 动态 aria-label(双era推断迁移概览) + sr-only 表(技能×双era占比/题数) — 复用 skills/pctOf/nOf/newOK
    const ariaSkills = skills.slice();   // skills 原序; cats 是其 reverse 仅供 echarts 自下而上
    setAria("bk-cog",
      `设问类型分布对比(辽宁卷, 旧课标II 2015–20 vs 新高考II 21+${newOK ? "" : " 样本不足"}): ` +
      `推断占比 旧 ${oInf}% → 新 ${nInf}%; 共 ${ariaSkills.length} 类认知技能`);
    setSrTable("bk-cog", `设问类型「怎么想」 — 旧课标II vs 新高考II${newOK ? "" : "(新era样本不足, 方向性信号)"}`,
      ["认知技能", "旧课标II 占比", "旧 题数", "新高考II 占比", "新 题数"],
      ariaSkills.map(s => [s, pctOf(oldRows, s) + "%", "n=" + nOf(oldRows, s), pctOf(newRows, s) + "%", "n=" + nOf(newRows, s)]));
    const rel = (cs && cs.reliability) || {};
    const nNew = (rel[ERA_NEW] || {}).n || newRows.reduce((a, r) => a + r.n, 0);
    const nOld = (rel[ERA_OLD] || {}).n || oldRows.reduce((a, r) => a + r.n, 0);
    // #11: 诚实叙事 — 新era不可信时 banner 显著(非12px灰) + 把"迁移真值"降级为"方向性信号"(critic: n=15单年不作趋势结论)
    const banner = !newOK
      ? `<div class="caveat-banner"><span class="cb-tag">样本不足</span><span>新高考II 仅 2023 单年 n=${nNew}(&lt;30) = <b>方向性信号, 非精确分布/趋势结论</b>; 待补 2022/2024/2025 真辽宁设问标注确认。</span></div>`
      : "";
    const inf = !newOK
      ? `方向性参考(非趋势结论): 推断占比 旧课标II ${oInf}% → 新高考II(2023) ${nInf}%`
      : `命题哲学迁移: <b style="color:${C.up}">推断 ${oInf}% → ${nInf}%</b>(细节下行)——新高考重高阶推断`;
    G.$("#bk-cognote").innerHTML = banner
      + `真相源=教研解析<b>显式标签</b>(强于双模型)。${inf}。`
      + `<br><small class="muted">旧课标II ${nOld}子题(2015–20六年, 分布可靠) vs 新高考II 仅2023 n=${nNew}。2021源=全国甲卷已剔(§7)。</small>`;
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
    charts.cross = echarts.getInstanceByDom(G.$("#bk-cross")) || echarts.init(G.$("#bk-cross"));
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
    G.$("#bk-crosslbl").innerHTML = `${CROSS_LBL[state.cross]} <span style="background:#EDE8DF;color:#7a2e15;padding:0 6px;border-radius:8px;font-size:10px;white-space:nowrap;">仅旧课标II 2015–20截面 · 2021+桥缺失</span>`;
    G.$("#bk-crossnote").innerHTML = `老师分流: 哪类语篇考哪种思维。<b>应用文/文学艺术 ≈ 纯找信息(0推断)</b>, <b style="color:${C.up}">说明文/记叙文最考推断</b> → 精读分流训练重心。`
      + `<br><small class="muted">注 技能侧=<b>教研显式标签(真值)</b> · 题材侧=<b>模型推断(dual_model_agree, 非真值交叉)</b>。粒度=子题数(同语篇题材重复计入), 覆盖 ${cov}; era锁2015–20(2021+桥缺失); n&lt;10格注仅参考。</small>`;
  }

  function renderHeat(heat) {
    const sts = ["core", "standard", "HV_extra", "LV_extra"];
    const data = [];
    heat.letters.forEach((L, xi) => sts.forEach((s, yi) => data.push([xi, yi, (heat.cells[L] || {})[s] || 0])));
    const maxv = Math.max(...data.map(d => d[2]));
    charts.heat = echarts.getInstanceByDom(G.$("#bk-heat")) || echarts.init(G.$("#bk-heat"));
    charts.heat.setOption({
      grid: { left: 60, right: 8, top: 8, bottom: 40, containLabel: false },
      xAxis: { type: "category", data: heat.letters, splitArea: { show: true }, axisLabel: { fontSize: 9 } },
      yAxis: { type: "category", data: sts.map(s => STATUS[s][0]), splitArea: { show: true } },
      visualMap: { min: 0, max: maxv, calculable: true, orient: "horizontal", left: "center", bottom: 0, inRange: { color: ["#F1EFE8", "#85B7EB", "#1F5F94"] }, textStyle: { fontSize: 10 } },
      tooltip: { formatter: p => `${heat.letters[p.data[0]]} · ${STATUS[sts[p.data[1]]][0]}<br/>${p.data[2]} 词` },
      series: [{ type: "heatmap", data, label: { show: false }, itemStyle: { borderColor: "rgba(255,255,255,0.4)", borderWidth: 1 } }],
    });
    // a11y: 动态 aria-label(各词汇状态总词数) + sr-only 表(字母×状态词数) — 复用 heat.letters/heat.cells/sts/STATUS
    const statusName = s => (STATUS[s] && STATUS[s][0]) || s;
    const statusTotal = s => heat.letters.reduce((a, L) => a + ((heat.cells[L] || {})[s] || 0), 0);
    setAria("bk-heat",
      `词汇热力图(词频非考点 · 字母开头 × 词汇状态): ` +
      sts.map(s => `${statusName(s)} ${statusTotal(s)} 词`).join(", "));
    setSrTable("bk-heat", "词汇热力 — 字母 × 词汇状态 词数(词频非考点)",
      ["字母", ...sts.map(statusName)],
      heat.letters.map(L => [L, ...sts.map(s => (heat.cells[L] || {})[s] || 0)]));
    charts.heat.off("click");
    charts.heat.on("click", p => G.sendPrompt ? G.sendPrompt(`列出 ${STATUS[sts[p.data[1]]][0]} 类 ${heat.letters[p.data[0]]} 开头的词`) : null);
  }

  function wire() {
    G.$("#bk-filter").innerHTML = filterBar();
    G.$$("#bk-filter [data-era]").forEach(b => b.onclick = () => { state.era = b.dataset.era; G.$("#bk-filter").innerHTML = filterBar(); wire(); renderDist(); renderShift(); });
    const sel = G.$("#bk-dim");
    if (sel) sel.onchange = () => { state.dim = sel.value; renderDist(); renderShift(); };
  }

  // #5: 给每张含 echarts 实例的卡追加 PNG 导出按钮 (getInstanceByDom 自动跳过非图卡如B区HTML)
  function wireExports() {
    if (!window.echarts) return;
    G.$$(".bk-card").forEach(card => {
      if (card.querySelector(".bk-export")) return;        // 防重复
      let inst = null;
      card.querySelectorAll("div[id]").forEach(d => { const i = echarts.getInstanceByDom(d); if (i) inst = i; });
      if (!inst) return;
      const h = card.querySelector(".bk-h");
      if (!h) return;
      const title = ((h.querySelector("span") || {}).textContent || "图").trim().split(" ")[0];
      const btn = document.createElement("button");
      btn.className = "bk-export"; btn.innerHTML = G.icon("download") + " PNG"; btn.title = "导出本图 PNG";
      btn.onclick = () => G.exportChartPNG(inst, `辽宁卷_${title}.png`);
      h.appendChild(btn);
    });
    const pb = G.$("#bk-print");
    if (pb) pb.onclick = () => G.printWithCharts();   // RC1: 打印保图(echarts→PNG注入)
  }

  registerTab("beike", async () => {
    G.$("#content").innerHTML = shell();
    const echartsOk = await G.ensureECharts();   // RC1: 轮询等 echarts 就绪, 根治 load 竞态静默空白
    const [dist, qt, heat, cog] = await Promise.all([
      // RC1/D0: distribution 是驾驶舱主数据, 失败必抛 → route() 显式错误态 (不冒充空壳掩盖后端故障)
      fetchJSON("/api/exam_point/distribution"),
      fetchJSON("/api/trend/question_type_presence").catch(() => ({ by_question_type: [] })),
      fetchJSON("/api/heatmap/vocab").catch(() => ({ letters: [], cells: {} })),
      fetchJSON("/api/exam_point/cognitive_skill").catch(() => ({ by_era: {} })),
    ]);
    state.dist = dist;
    wire();
    const cross = await loadCross(state.cross);
    if (echartsOk) {
      renderDist(); renderTrend(qt); renderHeat(heat); renderCognitiveSkill(cog);
      renderCrossToggle(); renderCogCross(cross);
    } else {
      G.chartLoadError(G.$("#bk-dist"));   // D0诚实: echarts 真失败显式报错, 不冒充空白
    }
    renderShift();
    wireExports();   // #5: 图卡追加 PNG 导出 + 打印按钮接线
    if (!window.__rzBeike) { window.__rzBeike = 1; window.addEventListener("resize", () => Object.values(charts).forEach(c => c && c.resize())); }  // RC1: 只绑一次防切tab累积泄漏
  });
})();
