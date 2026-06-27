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
  function exportChartPNG(chart, filename) {
    if (!chart || typeof chart.getDataURL !== "function") return false;
    _downloadURL(chart.getDataURL({ type: "png", pixelRatio: 2, backgroundColor: "#fff" }), filename || "chart.png");
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

  return {
    $, $$, fetchJSON, tagChip, renderTable, formToQs,
    mountLayout, conceptLink, mdToHtml, NAV, icon,
    audioPlayer, _toggleAudio, _seekAudio, _cycleSpeed,
    exportChartPNG, exportCSV, printWithCharts, ensureECharts, chartLoadError,
  };
})();
