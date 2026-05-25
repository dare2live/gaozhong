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
    return `<a class="gz-concept" data-concept="${id.replace(/"/g, '&quot;')}">${safe}</a>`;
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

  function colorByTagKind(kind) {
    const map = {
      word: "#0a4d75", grammar: "#1c5d99", year: "#f4a261",
      question_type: "#c1272d", difficulty: "#2a9d8f",
      unit: "#7aa6c2", theme: "#2a9d8f",
    };
    return map[kind] || "#888";
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
        <button class="play-btn" disabled>▶</button>
        <div class="progress-wrap">
          <span class="time-label">无音频文件 (预估 ${duration || "?"}s) — 可用 TTS 合成</span>
        </div>
      </div>`;
    }
    return `<div class="gz-audio-player" id="${uid}">
      <audio preload="metadata" src="${audioSrc}"></audio>
      <button class="play-btn" onclick="GZ._toggleAudio('${uid}')">▶</button>
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
    if (audio.paused) { audio.play(); btn.textContent = "⏸"; }
    else { audio.pause(); btn.textContent = "▶"; }
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
      audio.addEventListener("ended", () => { btn.textContent = "▶"; });
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

  // expose
  return {
    $, $$, fetchJSON, tagChip, renderTable, formToQs,
    mountLayout, colorByTagKind, conceptLink, mdToHtml, NAV,
    audioPlayer, _toggleAudio, _seekAudio, _cycleSpeed,
  };
})();
