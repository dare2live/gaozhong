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

  // ===== D0 诚实取数: 区分"真无数据"与"接口失败" (RC1 根因#2: 根治 .catch(()=>空) 把 500/断网冒充无数据) =====
  // fetchSafe: 失败返回 {__err} 哨兵 (不再静默吞成 []/{}); 调用方 isErr() 判, 用 errorBox() 渲可见错误态。
  async function fetchSafe(path) {
    try { return await fetchJSON(path); }
    catch (e) { return { __err: String((e && e.message) || e), __path: path }; }
  }
  function isErr(v) { return !!(v && v.__err); }
  // 可见错误态 HTML (取代各 tab 灰字"无数据"静默降级; 与 design-system .error-state 同源)。
  function errorBox(opts) {
    opts = opts || {};
    const retry = opts.retry === false ? "" : '<button class="es-retry" type="button" onclick="location.reload()">重新载入</button>';
    return `<div class="error-state" style="margin:0"><div class="es-title">${opts.title || "加载失败"}</div>`
      + `<div class="es-msg">${opts.msg || "后端接口未能返回 (非数据为空)。"} ${retry}</div></div>`;
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

  /**
   * 全局浮窗友好的 concept 链接 (用户 2026-05-24).
   * 用法: html += GZ.conceptLink('word:family', 'family')
   * 渲染: <a class="gz-concept" data-concept="word:family">family</a>
   * 点击 → graph_popup.js 自动弹关联图 + 真题
   */
  function conceptLink(conceptId, label) {
    const id = String(conceptId || "");
    const text = String(label || conceptId || "");
    const safe = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    // a11y: tabindex+role 使无 href 的概念链接键盘可聚焦; Enter/Space 由全局 keydown 委托激活
    return `<a class="gz-concept" tabindex="0" role="link" data-concept="${id.replace(/"/g, '&quot;')}">${safe}</a>`;
  }

  // ===== 全局键盘可达委托 (a11y RC1): 非原生可激活元素响应 Enter/Space → click =====
  // 用法: 给可点 div/span/li 加 role="button" tabindex="0" (或 data-gz-key), click 处理已有即可键盘激活。
  if (typeof document !== "undefined") {
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Enter" && e.key !== " " && e.key !== "Spacebar") return;
      const el = e.target;
      if (!el || typeof el.matches !== "function") return;
      if (el.tagName === "BUTTON" || (el.tagName === "A" && el.hasAttribute("href")) ||
          el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT") return;
      if (el.matches('a.gz-concept, [data-gz-key], [role="button"][tabindex], [role="link"][tabindex]')) {
        e.preventDefault();
        el.click();
      }
    });
  }

  /**
   * 极简 markdown → HTML (无 lib).
   * 支持: ### / ## # 标题, **bold**, - list, \n\n 段落.
   * 保留 HTML 标签 (eg <a class="gz-concept">) 直接通过.
   */
  function mdToHtml(md) {
    if (!md) return "";
    const lines = md.split("\n");
    const out = [];
    let inList = false;
    for (const raw of lines) {
      const line = raw.trimEnd();
      if (line.startsWith("### ")) {
        if (inList) { out.push("</ul>"); inList = false; }
        out.push(`<h3>${line.slice(4)}</h3>`);
      } else if (line.startsWith("## ")) {
        if (inList) { out.push("</ul>"); inList = false; }
        out.push(`<h2>${line.slice(3)}</h2>`);
      } else if (line.startsWith("# ")) {
        if (inList) { out.push("</ul>"); inList = false; }
        out.push(`<h1>${line.slice(2)}</h1>`);
      } else if (line.startsWith("- ")) {
        if (!inList) { out.push("<ul>"); inList = true; }
        out.push(`<li>${line.slice(2).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")}</li>`);
      } else if (line === "---") {
        if (inList) { out.push("</ul>"); inList = false; }
        out.push("<hr>");
      } else if (!line) {
        if (inList) { out.push("</ul>"); inList = false; }
      } else {
        if (inList) { out.push("</ul>"); inList = false; }
        const txt = line.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
                        .replace(/_(.+?)_/g, "<em>$1</em>");
        out.push(`<p>${txt}</p>`);
      }
    }
    if (inList) out.push("</ul>");
    return out.join("\n");
  }

  /**
   * 听力播放器 HTML (Phase 7.2).
   * audioSrc: mp3 路径 (或空 → 显示 "无音频" 提示)
   * duration: 预估秒数 (用于无音频时显示)
   */
  function audioPlayer(audioSrc, duration) {
    const uid = "ap_" + Math.random().toString(36).slice(2, 8);
    if (!audioSrc) {
      return `<div class="gz-audio-player" style="opacity:0.6">
        <button class="play-btn" disabled aria-label="播放(无音频)">${icon("play")}</button>
        <div class="progress-wrap">
          <span class="time-label">无音频文件 (预估 ${duration || "?"}s), 可用 TTS 合成</span>
        </div>
      </div>`;
    }
    return `<div class="gz-audio-player" id="${uid}">
      <audio preload="metadata" src="${audioSrc}"></audio>
      <button class="play-btn" aria-label="播放/暂停" onclick="GZ._toggleAudio('${uid}')">${icon("play")}</button>
      <div class="progress-wrap">
        <input type="range" class="progress-bar" min="0" max="100" value="0"
               oninput="GZ._seekAudio('${uid}', this.value)">
        <span class="time-label">0:00 / ${_fmtTime(duration || 0)}</span>
      </div>
      <button class="speed-btn" onclick="GZ._cycleSpeed('${uid}')">1x</button>
    </div>`;
  }

  function _fmtTime(s) {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return m + ":" + String(sec).padStart(2, "0");
  }

  function _toggleAudio(uid) {
    const wrap = document.getElementById(uid);
    if (!wrap) return;
    const audio = wrap.querySelector("audio");
    const btn = wrap.querySelector(".play-btn");
    if (audio.paused) { audio.play(); btn.innerHTML = icon("pause"); }
    else { audio.pause(); btn.innerHTML = icon("play"); }
    if (!audio._bound) {
      audio._bound = true;
      audio.addEventListener("timeupdate", () => {
        const bar = wrap.querySelector(".progress-bar");
        const label = wrap.querySelector(".time-label");
        if (audio.duration) {
          bar.value = (audio.currentTime / audio.duration) * 100;
          label.textContent = _fmtTime(audio.currentTime) + " / " + _fmtTime(audio.duration);
        }
      });
      audio.addEventListener("ended", () => { btn.innerHTML = icon("play"); });
    }
  }

  function _seekAudio(uid, pct) {
    const wrap = document.getElementById(uid);
    if (!wrap) return;
    const audio = wrap.querySelector("audio");
    if (audio.duration) audio.currentTime = (pct / 100) * audio.duration;
  }

  function _cycleSpeed(uid) {
    const wrap = document.getElementById(uid);
    if (!wrap) return;
    const audio = wrap.querySelector("audio");
    const btn = wrap.querySelector(".speed-btn");
    const speeds = [0.75, 1, 1.25, 1.5];
    const cur = speeds.indexOf(audio.playbackRate);
    const next = speeds[(cur + 1) % speeds.length];
    audio.playbackRate = next;
    btn.textContent = next + "x";
  }

  // ===== echarts 就绪保障 (RC1: 根治 load 竞态致图表静默空白) =====
  // echarts.min.js 1MB 本地脚本; 个别环境(慢盘/缓存重验)首帧未就绪 → 旧 if(window.echarts) 静默跳过=空白。
  // 此处轮询等就绪 (默认 5s), 返回 bool; 调用方就绪才渲、未就绪显式报错 (D0诚实: 真失败不冒充空白)。
  async function ensureECharts(timeoutMs) {
    const limit = timeoutMs || 5000;
    let waited = 0;
    while (!window.echarts && waited < limit) {
      await new Promise(r => setTimeout(r, 60));
      waited += 60;
    }
    return !!window.echarts;
  }
  // 单一安全图表初始化 (RC1 根因锁): getInstanceByDom 复用当前容器实例, 仅新容器才 init →
  //   根治"重访 tab 陈旧实例渲到已销毁 DOM 致空白"。全前端 echarts 图必经此; raw echarts.init 仅本文件。
  function initChart(el) {
    if (!el || !window.echarts) return null;
    return window.echarts.getInstanceByDom(el) || window.echarts.init(el);
  }
  // ===== 考点共现网络 单一渲染口径 (图谱tab + 讲课C' 共用, 防配色/交互漂移) =====
  // 维度→{标签,色}: 体裁=红(accent) / 主题语境·主题群=金(warn族) / 设问思维=蓝(down)。锚令牌族。
  const COOCCUR_DIM = {
    genre:           { label: "体裁",     color: "#BE3A2B" },
    theme_context:   { label: "主题语境", color: "#9A6A00" },
    theme_l2:        { label: "主题群",   color: "#C98A2B" },
    cognitive_skill: { label: "设问思维", color: "#1F5F94" },
  };
  const _coDim = d => COOCCUR_DIM[d] || { label: d || "维度", color: "#B4B2A9" };
  // 渲染考点共现力导向图。el=容器, pairs=cooccurrence.pairs ({a_dim,a_label,b_dim,b_label,co_n});
  // opts: {strongMin?: 滤 co_n≥N (留则用强边), srEl?: sr-only 表容器, eraLabel?: 标题}。
  // 点考点节点 → GZ.openPopup(exam_point:dim:label) 真题下钻。返回 echarts 实例 (调用方管 dispose)。
  function renderCooccurNetwork(el, pairs, opts) {
    opts = opts || {};
    if (!el || !window.echarts || !pairs || !pairs.length) return null;
    let used = pairs;
    if (opts.strongMin) { const s = pairs.filter(p => p.co_n >= opts.strongMin); if (s.length) used = s; }
    const nodeMap = {}, deg = {}, dims = [];
    used.forEach(p => {
      [[p.a_dim, p.a_label], [p.b_dim, p.b_label]].forEach(([dim, label]) => {
        const id = `exam_point:${dim}:${label}`;
        if (!nodeMap[id]) { nodeMap[id] = { id, name: label, dim }; if (dims.indexOf(dim) < 0) dims.push(dim); }
        deg[id] = (deg[id] || 0) + p.co_n;
      });
    });
    const nodes = Object.values(nodeMap);
    const inst = initChart(el);
    inst.setOption({
      tooltip: {
        formatter: p => p.dataType === "edge"
          ? `${p.data.source.split(":").pop()} × ${p.data.target.split(":").pop()}<br/><span style="color:#76716A">同题共现 ${p.data.value} 次</span>`
          : `${p.data.name}<br/><span style="color:#76716A;font-size:11px">${_coDim(p.data.dim).label} · 关联强度 ${p.data.value}</span>`,
      },
      legend: [{ data: dims.map(d => _coDim(d).label), bottom: 0, textStyle: { fontSize: 11 }, icon: "circle", itemWidth: 10, itemHeight: 10 }],
      series: [{
        type: "graph", layout: "force", roam: true, draggable: true,
        categories: dims.map(d => ({ name: _coDim(d).label, itemStyle: { color: _coDim(d).color } })),
        force: { repulsion: 360, edgeLength: [70, 170], gravity: 0.05, friction: 0.35 },
        label: { show: true, fontSize: 11.5, color: "#45413A", position: "right" },
        lineStyle: { color: "#CFC9BD", curveness: 0.04, opacity: 0.75 },
        emphasis: { focus: "adjacency", lineStyle: { color: "#BE3A2B" }, label: { fontWeight: "bold" } },
        data: nodes.map(n => ({ id: n.id, name: n.name, dim: n.dim, value: deg[n.id] || 0, category: dims.indexOf(n.dim), symbolSize: Math.min(18 + (deg[n.id] || 0) / 3, 56) })),
        links: used.map(p => ({ source: `exam_point:${p.a_dim}:${p.a_label}`, target: `exam_point:${p.b_dim}:${p.b_label}`, value: p.co_n, lineStyle: { width: Math.min(1 + p.co_n / 6, 8) } })),
      }],
    });
    inst.off("click");
    inst.on("click", p => { if (p.dataType === "node" && window.GZ && window.GZ.openPopup) window.GZ.openPopup(p.data.id); });
    setTimeout(() => inst.resize(), 60);
    // a11y: aria-label 概览 + 可选 sr-only 数据表 (复用已算 nodes/used, 不重算)
    const top = [...used].sort((a, b) => b.co_n - a.co_n).slice(0, 3).map(p => `${p.a_label}×${p.b_label} 同题${p.co_n}次`).join("、");
    el.setAttribute("role", "img");
    el.setAttribute("aria-label", `考点共现网络${opts.eraLabel ? "(" + opts.eraLabel + ")" : ""}: ${nodes.length}考点/${used.length}共现对, 关联最强 ${top}。题材/主题为模型推断方向性标注。`);
    const sr = opts.srEl && (typeof opts.srEl === "string" ? document.querySelector(opts.srEl) : opts.srEl);
    if (sr) {
      const rows = [...used].sort((a, b) => b.co_n - a.co_n).map(p => `<tr><td>${p.a_label}(${_coDim(p.a_dim).label})</td><td>${p.b_label}(${_coDim(p.b_dim).label})</td><td>${p.co_n}</td></tr>`).join("");
      sr.innerHTML = `<table><caption>考点同题共现(${nodes.length}节点/${used.length}对; 题材/主题维度为模型推断方向性标注, 共现=同题出现非因果)</caption><thead><tr><th>考点A</th><th>考点B</th><th>同题共现次数</th></tr></thead><tbody>${rows}</tbody></table>`;
    }
    // 可见诚实口径 (RC1 根因#4): 题材/主题=双模型推断方向性, 共现≠因果。主受众=老师看屏, 不只藏 aria/sr-only。
    // helper 层统一插一次, graph + jiangke 复用本渲染器即自动获得一致可见 caveat (防逐 tab 文案漂移)。
    if (el.parentNode && !el.parentNode.querySelector(".cooccur-caveat")) {
      const cv = document.createElement("p");
      cv.className = "muted cooccur-caveat";
      cv.style.cssText = "font-size:11px;margin:6px 0 0;";
      cv.textContent = "注 体裁/主题维度为双模型推断(方向性, 非真值); 边=同题共现次数, 非因果。";
      el.insertAdjacentElement("afterend", cv);
    }
    return inst;
  }

  // 图表载入失败时在容器显式报错 (取代静默空白)。
  function chartLoadError(el) {
    if (el) el.innerHTML = '<div class="error-state" style="margin:0"><div class="es-title">图表组件未能载入</div>'
      + '<div class="es-msg">ECharts 渲染库加载失败 (非数据问题)。<button class="es-retry" type="button" onclick="location.reload()">重新载入</button></div></div>';
  }

  // ===== 内联 SVG 图标 (替代 emoji; 全局禁 emoji, Tabler 风格 currentColor) =====
  const _ICONS = {
    download: '<path d="M12 3v12"/><path d="m7 11 5 5 5-5"/><path d="M4 21h16"/>',
    printer: '<path d="M6 9V3h12v6"/><path d="M6 18H4a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-2"/><rect x="7" y="14" width="10" height="7" rx="1"/>',
    play: '<path d="M7 5v14l11-7z" fill="currentColor" stroke="none"/>',
    pause: '<rect x="7" y="5" width="3.4" height="14" rx="1" fill="currentColor" stroke="none"/><rect x="13.6" y="5" width="3.4" height="14" rx="1" fill="currentColor" stroke="none"/>',
    grid: '<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>',
    gear: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 8 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 3.6 15a1.65 1.65 0 0 0-1.51-1H2a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 3.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 8 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
    close: '<path d="M6 6l12 12"/><path d="M18 6 6 18"/>',
  };
  function icon(name, cls) {
    const p = _ICONS[name] || "";
    return `<svg class="gz-ic ${cls || ""}" viewBox="0 0 24 24" aria-hidden="true">${p}</svg>`;
  }

  // expose
  // ===== 导出/打印共享 helper (#5: 跨研判/词典/K12 把分析产物带进教研会/打印, 一次建解多区) =====
  function _downloadURL(url, filename) {
    const a = document.createElement("a");
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); a.remove();
  }
  // ECharts 图 → PNG 下载 (驾驶舱命题迁移图/词汇热力等研判图)
  // PNG 自包含 (设计规范 P2): 导出时临时注入 title (卡名) + subtext (来源/日期), 离开页面独立可读; 导出后还原。
  function exportChartPNG(chart, filename, meta) {
    if (!chart || typeof chart.getDataURL !== "function") return false;
    const title = meta && meta.title;
    if (title) {
      chart.setOption({ title: { text: title, subtext: (meta.sub || "辽宁 K12 英语 · 数据来自辽宁真题与课标"),
        left: 4, top: 2, textStyle: { fontSize: 14, fontWeight: 650, color: "#1C1A17" },
        subtextStyle: { fontSize: 10, color: "#76716A" } }, grid: { top: 64 } });
    }
    _downloadURL(chart.getDataURL({ type: "png", pixelRatio: 2, backgroundColor: "#fff" }), filename || "chart.png");
    if (title) chart.setOption({ title: { text: "", subtext: "" }, grid: { top: undefined } });
    return true;
  }
  // 表格 rows → CSV 下载 (词典词表/越纲清单带走; rows=对象数组, columns=[{key,label}]; BOM 兜 Excel 中文)
  function exportCSV(rows, columns, filename) {
    const esc = v => `"${String(v == null ? "" : v).replace(/"/g, '""')}"`;
    const head = columns.map(c => esc(c.label)).join(",");
    const body = (rows || []).map(r => columns.map(c => esc(r[c.key])).join(",")).join("\n");
    const blob = new Blob(["﻿" + head + "\n" + body], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    _downloadURL(url, filename || "export.csv");
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  }

  // 打印保图 (RC1): echarts canvas 默认不进打印 → 打印前把各图 getDataURL 注入 <img>, 打印后还原。
  function printWithCharts() {
    if (!window.echarts) { window.print(); return; }
    const restores = [];
    document.querySelectorAll("[_echarts_instance_]").forEach(d => {
      const inst = window.echarts.getInstanceByDom(d);
      if (!inst) return;
      let url;
      try { url = inst.getDataURL({ type: "png", pixelRatio: 2, backgroundColor: "#fff" }); } catch (e) { return; }
      const img = document.createElement("img");
      img.className = "gz-print-img"; img.src = url;
      img.style.cssText = "width:100%;height:auto;max-width:" + (d.offsetWidth || 640) + "px;";
      d.style.display = "none";
      d.insertAdjacentElement("afterend", img);
      restores.push(() => { d.style.display = ""; img.remove(); });
    });
    let done = false;
    const cleanup = () => { if (done) return; done = true; restores.forEach(f => f()); };
    window.addEventListener("afterprint", cleanup, { once: true });
    try { window.print(); } finally { setTimeout(cleanup, 1500); }
  }

  // 微缩学段 DNA 带 (设计规范 P2-6, 单渲染点三处回响: ①结论卡/④覆盖旁/③词典卡)。
  // d = /api/k12/tested_word_stage 响应; 120×14 纯 CSS, 无标签 (title 带全构成), 段色循 §02 规范。
  const _MINI_SEG = { "小学": "var(--down)", "初中": "var(--down-2)", "义务教育": "var(--down-3)",
    "高中必修": "var(--accent-ink)", "高中选修": "var(--accent)",
    "未分类": "repeating-linear-gradient(-45deg, var(--data-gray), var(--data-gray) 2px, #C9C7BF 2px, #C9C7BF 4px)" };
  function stageMiniBand(d) {
    if (!d || !d.stages) return "";
    const t = d.stages.map(s => `${s.stage} ${s.pct}%`).join(", ");
    const segs = d.stages.map(s =>
      `<span style="width:${s.pct}%;background:${_MINI_SEG[s.raw_stage || s.stage] || "var(--data-gray)"}"></span>`).join("");
    return `<span class="gz-miniband" role="img" title="考查词学段构成: ${t}" aria-label="考查词学段构成: ${t}">${segs}</span>`;
  }

  // 统一无色块 masthead (设计规范: 全站页头单渲染点, 防形态漂移; 样式 .sc-head 见 app.css)。
  // kicker = 板块上下文(纯文本) / title = 学习者问题句 / lead = 这页回答什么 / right = 可选右槽 HTML(打印钮等)。
  function pageHead(kicker, title, lead, right) {
    return `<header class="sc-head"><div>` +
      (kicker ? `<div class="sc-badge">${kicker}</div>` : "") +
      `<h1 class="sc-title">${title}</h1>` +
      (lead ? `<p class="sc-lead">${lead}</p>` : "") +
      `</div>${right ? `<div class="sc-right">${right}</div>` : ""}</header>`;
  }

  return {
    $, $$, fetchJSON, fetchSafe, isErr, errorBox, tagChip, renderTable, formToQs,
    mountLayout, conceptLink, mdToHtml, NAV, icon, pageHead, stageMiniBand,
    audioPlayer, _toggleAudio, _seekAudio, _cycleSpeed,
    exportChartPNG, exportCSV, printWithCharts, ensureECharts, chartLoadError, initChart, renderCooccurNetwork,
  };
})();
