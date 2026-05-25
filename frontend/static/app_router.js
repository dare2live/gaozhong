/* SPA hash router — 7 tab (第五阶段 5.1).
   每 tab 一个 mount() 函数, 注册到 ROUTES dict. (M2 插件式 dispatch) */

(function () {
  const { $, $$, fetchJSON, mdToHtml } = window.GZ;
  const CONTENT = $("#content");

  // -- 注册表 (M2)
  const TABS = {};
  function register(name, mount) { TABS[name] = mount; }

  // -- router
  function route() {
    const hash = (location.hash || "#/teaching").slice(2);  // strip "#/"
    const name = (hash.split("/")[0] || "teaching").toLowerCase();
    $$(".tabnav a").forEach(a => a.classList.toggle("active", a.dataset.tab === name));
    const mount = TABS[name];
    if (mount) {
      mount().catch(err => {
        CONTENT.innerHTML = `<p style="color:#c00">tab ${name} 出错: ${err.message}</p>`;
      });
    } else {
      CONTENT.innerHTML = `<p>未知 tab: ${name}</p>`;
    }
  }
  window.addEventListener("hashchange", route);
  window.addEventListener("DOMContentLoaded", () => { if (!location.hash) location.hash = "#/teaching"; route(); });

  // ===================================================================
  // A. 工作台
  // ===================================================================
  register("workbench", async () => {
    const [stats, cs, classes, audit] = await Promise.all([
      fetchJSON("/api/stats"),
      fetchJSON("/api/course/stats"),
      fetchJSON("/api/students/classes").catch(() => ({ count: 0, classes: [] })),
      fetchJSON("/api/audit/findings").catch(() => []),
    ]);
    const findings = Array.isArray(audit) ? audit : (audit.findings || []);
    const fail = findings.filter(f => f.severity === "FAIL").length;
    const warn = findings.filter(f => f.severity === "WARN").length;
    const sevColor = fail > 0 ? "G_FINAL" : (warn > 4 ? "G3" : "G1");
    const totalStudents = (classes.classes || []).reduce((a, c) => a + (c.n_students || 0), 0);
    CONTENT.innerHTML = `
      <h2>A. 工作台 · 今日概览</h2>
      <div class="course-grid">
        <div class="course-card ${sevColor}">
          <strong>📊 数据健康</strong>
          <div class="block"><strong>${fail} FAIL · ${warn} WARN</strong> (共 ${findings.length} audit)</div>
          <div class="block"><a href="#/data">→ D 数据管理</a> 查详</div>
        </div>
        <div class="course-card G_FINAL">
          <strong>📚 40 节课程</strong>
          <div class="block">G1:${cs.by_layer?.G1 ?? 0} · G2:${cs.by_layer?.G2 ?? 0} · G3:${cs.by_layer?.G3 ?? 0} · G_FINAL:${cs.by_layer?.G_FINAL ?? 0}</div>
          <div class="block">materials: ${cs.total_materials ?? 0} 行 · <a href="#/teaching">→ B 教学</a></div>
        </div>
        <div class="course-card">
          <strong>🎓 学生 + 班级</strong>
          <div class="block">${totalStudents} 学生 / ${classes.count || 0} 班</div>
          <div class="block"><a href="#/students">→ E 学生档案</a></div>
        </div>
        <div class="course-card">
          <strong>📝 题库</strong>
          <div class="block">${stats.question_bank ?? "-"} 题 / ${stats.question_tags ?? "-"} 标签</div>
          <div class="block"><a href="#/qbank">→ C 题库 + 组卷</a></div>
        </div>
        <div class="course-card">
          <strong>🌐 知识图谱</strong>
          <div class="block">${stats.nodes ?? "-"} nodes · ${stats.edges ?? "-"} edges</div>
          <div class="block"><a href="#/graph">→ F 图谱 + 趋势</a></div>
        </div>
        <div class="course-card">
          <strong>📂 教材资源</strong>
          <div class="block">${stats.textbooks ?? "-"} 教材 · ${stats.cefr_vocab ?? "-"} 课标词</div>
          <div class="block">${stats.exam_questions ?? "-"} 真题 · ${stats.theme_contexts ?? "-"} 主题</div>
        </div>
      </div>
      <h3 style="margin-top:1.5rem">最近 audit 异常 (${fail + warn} 条, 前 5)</h3>
      <ul class="gz-qlist" style="background:#fff;padding:0.5rem 2rem;border-radius:4px">
        ${findings.filter(f => f.severity !== "OK").slice(0, 5).map(f =>
          `<li><strong style="color:${f.severity === 'FAIL' ? '#E3120B' : '#f4a261'}">${f.severity}</strong>
           <code>${f.audit_kind}</code> ${f.target || ""}: ${(f.actual || "").slice(0, 100)}</li>`
        ).join("") || "<li>无</li>"}
      </ul>`;
  });

  // ===================================================================
  // B. 教学 ⭐ — 40 节按 layer 分组 + 点击查讲义
  // ===================================================================
  register("teaching", async () => {
    CONTENT.innerHTML = `<h2>B. 教学 — 40 节分层课程</h2><p>载入中...</p>`;
    const data = await fetchJSON("/api/course/list");
    const groups = { G1: [], G2: [], G3: [], G_FINAL: [] };
    for (const c of data.courses) groups[c.layer]?.push(c);
    const layerMeta = {
      G1: "高一系统课 · ~1200 词",
      G2: "高二系统课 · ~2200 词",
      G3: "高三上学期 · ~3000 词",
      G_FINAL: "高考前突击 · ~3500 词 · 真题密集",
    };
    let html = `<h2>B. 教学 — 40 节分层课程</h2>`;
    for (const layer of ["G1", "G2", "G3", "G_FINAL"]) {
      const items = groups[layer];
      html += `<section class="layer-section">
        <h3>${layer} <span class="layer-meta">${layerMeta[layer]} · ${items.length} 节</span></h3>
        <div class="course-grid">`;
      for (const c of items) {
        html += `<div class="course-card ${c.layer}" onclick="window._openHandout(${c.course_id})">
          <span class="cid">#${c.course_id}</span>
          <span class="layer-badge">${c.block_kind}</span>
          <div><strong>${c.title.replace(/^[GFINAL\d_·]+·/, "")}</strong></div>
          <div class="block">主题: ${c.themes_main || "(待补)"}</div>
        </div>`;
      }
      html += `</div></section>`;
    }
    html += `<div id="handout-modal" onclick="if(event.target===this)this.classList.remove('open')">
      <div class="modal-body">
        <span class="close-btn" onclick="document.getElementById('handout-modal').classList.remove('open')">✕</span>
        <button class="print-btn" onclick="window.print()">🖨️ 打印 / PDF</button>
        <div id="handout-md">载入中 ...</div>
      </div>
    </div>`;
    CONTENT.innerHTML = html;
  });

  // -- 讲义分段元数据 (Phase 7.1)
  const SEG_META = [
    { key: "header",    icon: "📖", label: "" },
    { key: "hook",      icon: "🎯", label: "开场 hook", match: "hook" },
    { key: "review",    icon: "🔄", label: "上节复习",  match: "复习" },
    { key: "core",      icon: "🔑", label: "核心教学",  match: "核心" },
    { key: "relations", icon: "🔗", label: "关联拓展",  match: "关联" },
    { key: "exam",      icon: "📝", label: "真题溯源",  match: "真题" },
    { key: "practice",  icon: "💡", label: "场景练习",  match: "场景" },
    { key: "homework",  icon: "📋", label: "课后作业",  match: "作业" },
    { key: "summary",   icon: "📌", label: "总结收束",  match: "总结" },
  ];

  function _classifySegment(text) {
    const first = text.split("\n").find(l => l.trim()) || "";
    for (let i = 1; i < SEG_META.length; i++) {
      if (first.includes(SEG_META[i].match)) return SEG_META[i];
    }
    return SEG_META[0];
  }

  function _renderSegments(raw) {
    const parts = raw.split(/\n---\n/);
    if (parts.length < 2) return mdToHtml(raw);
    let html = '<div class="handout-segments">';
    for (const part of parts) {
      const trimmed = part.trim();
      if (!trimmed) continue;
      const meta = _classifySegment(trimmed);
      const segLabel = meta.label || trimmed.split("\n")[0].replace(/^#+\s*/, "");
      html += `<div class="handout-seg seg-${meta.key}">`;
      html += `<div class="handout-seg-head"><span class="seg-icon">${meta.icon}</span> ${segLabel}</div>`;
      html += `<div class="handout-seg-body">${mdToHtml(trimmed)}</div>`;
      html += `</div>`;
    }
    html += '</div>';
    html += _renderPrinciples();
    return html;
  }

  function _renderPrinciples() {
    return `<div style="text-align:right">
      <span class="principles-toggle" onclick="this.nextElementSibling.classList.toggle('open')">
        ℹ️ 生成规则 (R2/R5/D0)
      </span>
      <div class="principles-body">
        <dl>
          <dt>R2 · 不拷教材</dt><dd>10-gram 不与教材原文重叠 — 用自己语言重述</dd>
          <dt>R5 · 词汇层约束</dt><dd>所有英语词 ⊆ 对应年级词表 (G1 ~1200 / G2 ~2200 / G3 ~3000 / G_FINAL ~3500)</dd>
          <dt>R1 · 关联 ≥3</dt><dd>每节核心知识点至少 3 个关联 (语义网络 / 词族 / 搭配)</dd>
          <dt>R4 · 作业对齐</dt><dd>作业 tag 100% ⊆ 本节知识点</dd>
          <dt>D0 · 准确率 100%</dt><dd>任何数据 + 关联准确率必须 100%, 18 章 audit 全绿</dd>
        </dl>
      </div>
    </div>`;
  }

  // 全局: 打开讲义 modal
  window._openHandout = async (cid) => {
    const modal = $("#handout-modal");
    const md = $("#handout-md");
    modal.classList.add("open");
    md.textContent = "载入中 ...";
    try {
      const data = await fetchJSON("/api/course/handout?id=" + cid);
      const raw = data.md || "";
      let html = raw.includes("\n---\n") ? _renderSegments(raw) : mdToHtml(raw);
      html += _renderQuizButton(cid);
      md.innerHTML = html || `<pre>${JSON.stringify(data, null, 2)}</pre>`;
    } catch (err) {
      md.innerHTML = "讲义载入失败: " + err.message;
    }
  };

  function _renderQuizButton(cid) {
    return `<div style="text-align:center;margin:1.5rem 0">
      <button class="gz-quiz-btn" onclick="window._startQuiz(${cid})">📝 课后测验</button>
    </div><div id="quiz-area"></div>`;
  }

  window._startQuiz = async (cid) => {
    const area = document.getElementById("quiz-area");
    if (!area) return;
    area.innerHTML = "<p>载入题目...</p>";
    try {
      const data = await fetchJSON("/api/course/quiz?id=" + cid);
      if (!data.questions || data.questions.length === 0) {
        area.innerHTML = "<p style='color:#888'>本节暂无测验题</p>";
        return;
      }
      let html = `<div class="gz-quiz"><h3>课后测验 · ${data.title} (${data.count} 题)</h3>`;
      data.questions.forEach((q, i) => {
        html += `<div class="gz-quiz-q" data-qid="${q.qb_id}" data-answer="${(q.answer||'').trim()}">
          <p><strong>${i+1}.</strong> <span class="gz-quiz-type">${q.question_type}</span>
             <span class="gz-quiz-diff">${q.difficulty}</span></p>
          <div class="gz-quiz-stem">${(q.stem||'').replace(/\n/g,'<br>')}</div>`;
        const opts = _parseOptions(q.options_json, q.stem);
        if (opts.length) {
          html += `<ul class="gz-quiz-opts">`;
          opts.forEach(o => {
            html += `<li data-label="${o.label}" onclick="window._selectOpt(this)">${o.label}. ${o.text}</li>`;
          });
          html += `</ul>`;
        } else {
          html += `<input type="text" class="gz-quiz-input" placeholder="输入答案" data-qid="${q.qb_id}">`;
        }
        html += `<div class="gz-quiz-feedback" style="display:none"></div></div>`;
      });
      html += `<div style="text-align:center;margin:1rem 0">
        <button class="gz-quiz-btn" onclick="window._submitQuiz()">提交批改</button>
      </div><div id="quiz-result"></div></div>`;
      area.innerHTML = html;
      area._quizData = data;
    } catch (err) {
      area.innerHTML = `<p style="color:#c00">载入失败: ${err.message}</p>`;
    }
  };

  function _parseOptions(optJson, stem) {
    if (optJson) {
      try { return JSON.parse(optJson); } catch (_) {}
    }
    const m = (stem||'').match(/([A-D])\.\s*(.+?)(?=\s+[A-D]\.|$)/gs);
    if (!m) return [];
    return m.map(s => { const p = s.match(/([A-D])\.\s*(.*)/s); return p ? {label:p[1],text:p[2].trim()} : null; }).filter(Boolean);
  }

  window._selectOpt = (li) => {
    const q = li.closest(".gz-quiz-q");
    q.querySelectorAll(".gz-quiz-opts li").forEach(x => x.classList.remove("selected"));
    li.classList.add("selected");
  };

  window._submitQuiz = () => {
    const area = document.getElementById("quiz-area");
    if (!area || !area._quizData) return;
    let correct = 0, total = 0;
    area.querySelectorAll(".gz-quiz-q").forEach(qEl => {
      total++;
      const expected = (qEl.dataset.answer || "").toUpperCase();
      const selLi = qEl.querySelector(".gz-quiz-opts li.selected");
      const inputEl = qEl.querySelector(".gz-quiz-input");
      const given = selLi ? selLi.dataset.label.toUpperCase() : (inputEl ? inputEl.value.trim().toUpperCase() : "");
      const fb = qEl.querySelector(".gz-quiz-feedback");
      fb.style.display = "block";
      if (given === expected) {
        correct++;
        fb.innerHTML = `<span style="color:#2a9d8f">✅ 正确</span>`;
        fb.className = "gz-quiz-feedback correct";
      } else {
        fb.innerHTML = `<span style="color:#c1272d">❌ 正确答案: ${expected}</span>`;
        fb.className = "gz-quiz-feedback wrong";
      }
      const qData = (area._quizData.questions||[]).find(q => q.qb_id === +qEl.dataset.qid);
      if (qData && qData.analysis) {
        fb.innerHTML += `<div class="gz-quiz-analysis">${qData.analysis}</div>`;
      }
    });
    const pct = total > 0 ? (correct / total * 100).toFixed(0) : 0;
    document.getElementById("quiz-result").innerHTML =
      `<div class="gz-quiz-result"><strong>得分: ${correct}/${total} (${pct}%)</strong></div>`;
  };

  // ===================================================================
  // C. 题库 + 组卷
  // ===================================================================
  register("qbank", async () => {
    CONTENT.innerHTML = `<h2>C. 题库 + 组卷</h2><p>载入中...</p>`;
    const [stats, listening] = await Promise.all([
      fetchJSON("/api/stats"),
      fetchJSON("/api/listening/list"),
    ]);
    let html = `<h2>C. 题库 + 组卷</h2>
      <p>当前题库: <strong>${stats.question_bank ?? "-"}</strong> 题 / <strong>${stats.question_tags ?? "-"}</strong> 标签</p>
      <p>详细组卷器: <a href="/teacher#compose" target="_blank">/teacher tab "组卷"</a> (兼容旧 UI)</p>

      <section class="layer-section">
        <h3>🎧 听力练习 <span class="layer-meta">${listening.count} 题 · 高考 30 分</span></h3>
        <div style="display:flex;gap:0.5rem;margin:0.5rem 0 0.7rem">
          <button class="gz-qfilter active" data-section="all" onclick="window._filterListening('all',this)">全部 (${listening.count})</button>
          <button class="gz-qfilter" data-section="听力短对话" onclick="window._filterListening('听力短对话',this)">短对话</button>
          <button class="gz-qfilter" data-section="听力长对话" onclick="window._filterListening('听力长对话',this)">长对话</button>
          <button class="gz-qfilter" data-section="听力独白" onclick="window._filterListening('听力独白',this)">独白</button>
        </div>
        <div id="listening-list">`;
    for (const q of listening.questions) {
      html += _renderListeningCard(q);
    }
    html += `</div></section>`;
    CONTENT.innerHTML = html;
    window._listeningData = listening.questions;
  });

  function _renderListeningCard(q) {
    const audioSrc = q.audio_id ? `/data/audio/${q.audio_id}.mp3` : "";
    return `<div class="listening-card" data-qtype="${q.question_type}" style="background:#fff;border:1px solid #e8e6e0;border-left:4px solid #0a4d75;border-radius:4px;padding:0.7rem 1rem;margin-bottom:0.5rem">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <strong>#${q.qb_id} · ${q.question_type}</strong>
        <span style="color:#888;font-size:0.85em">${q.difficulty} · ${q.audio_duration || "?"}s</span>
      </div>
      ${GZ.audioPlayer(null, q.audio_duration)}
      <div style="margin:0.4rem 0;font-size:0.9em">${(q.stem_preview || "").replace(/\n/g, "<br>")}</div>
      <span class="gz-transcript-toggle" onclick="window._showTranscript(${q.qb_id}, this)">显示原文</span>
      <div class="gz-transcript" id="transcript-${q.qb_id}" style="display:none">载入中...</div>
    </div>`;
  }

  window._filterListening = (section, btn) => {
    const list = document.getElementById("listening-list");
    if (!list) return;
    document.querySelectorAll(".gz-qfilter").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    list.querySelectorAll(".listening-card").forEach(card => {
      card.style.display = (section === "all" || card.dataset.qtype === section) ? "" : "none";
    });
  };

  window._showTranscript = async (qbId, toggleEl) => {
    const div = document.getElementById("transcript-" + qbId);
    if (!div) return;
    if (div.style.display === "none") {
      div.style.display = "block";
      toggleEl.textContent = "隐藏原文";
      if (div.textContent === "载入中...") {
        try {
          const d = await fetchJSON("/api/listening/detail?id=" + qbId);
          let html = "";
          if (d.transcript) {
            const lines = d.transcript.split("\n").filter(l => l.trim());
            html = lines.map(l => {
              const m = l.match(/^([A-Z]):\s*(.*)/);
              if (m) {
                const sp = (d.speakers || []).find(s => s.id === m[1]);
                return `<div><span class="speaker">${sp ? sp.label : m[1]}:</span> ${m[2]}</div>`;
              }
              return `<div>${l}</div>`;
            }).join("");
          }
          if (d.answer) html += `<div style="margin-top:0.5rem;padding-top:0.4rem;border-top:1px solid #ddd"><strong>答案:</strong> ${d.answer}</div>`;
          if (d.analysis) html += `<div style="color:#666;font-size:0.9em">${d.analysis}</div>`;
          div.innerHTML = html || "(无原文)";
        } catch (err) {
          div.innerHTML = `<span style="color:#c00">载入失败: ${err.message}</span>`;
        }
      }
    } else {
      div.style.display = "none";
      toggleEl.textContent = "显示原文";
    }
  };

  // ===================================================================
  // D. 数据管理
  // ===================================================================
  register("data", async () => {
    CONTENT.innerHTML = `<h2>D. 数据管理</h2><p>载入中...</p>`;
    const [stats, audit, cst] = await Promise.all([
      fetchJSON("/api/stats"),
      fetchJSON("/api/audit/findings").catch(() => ({findings: []})),
      fetchJSON("/api/constitution/list").catch(() => ({rules: [], by_type: {}})),
    ]);
    const f = audit.findings || [];
    const fail = f.filter(x => x.severity === "FAIL").length;
    const warn = f.filter(x => x.severity === "WARN").length;
    const rules = cst.rules || [];
    const principles = rules.filter(r => r.rule_type === "principle");
    const ironLaws = rules.filter(r => r.rule_type === "iron_law");
    const violations = rules.filter(r => r.rule_type === "violation");

    CONTENT.innerHTML = `
      <h2>D. 数据管理 + 设计宪法</h2>
      <div class="course-grid">
        <div class="course-card ${fail > 0 ? 'G_FINAL' : 'G1'}">
          <strong>审计概览</strong>
          <div class="block">FAIL: ${fail} / WARN: ${warn}</div>
        </div>
        <div class="course-card">
          <strong>知识图谱</strong>
          <div class="block">${stats.nodes ?? "-"} nodes / ${stats.edges ?? "-"} edges</div>
        </div>
        <div class="course-card">
          <strong>教材 + 课标</strong>
          <div class="block">${stats.textbooks ?? "-"} 教材 / ${stats.cefr_vocab ?? "-"} 课标词</div>
        </div>
        <div class="course-card">
          <strong>题库 + 课程</strong>
          <div class="block">${stats.question_bank ?? "-"} 题 / 40 课 / ${stats.course_materials ?? "-"} 关联</div>
        </div>
      </div>

      <section class="layer-section" style="margin-top:1.5rem">
        <h3>📜 设计宪法 <span class="layer-meta">${rules.length} 条 (${principles.length} 原则 + ${ironLaws.length} 铁律 + ${violations.length} 禁止)</span></h3>
        <p style="color:#666;font-size:0.85em">模型驱动内容生成最高原则 — 任何题目/教案/教程必须遵守. 入库强制执行.</p>

        <h4 style="color:#0a4d75;margin-top:1rem">六大原则</h4>
        <div class="course-grid">${principles.map(r => `
          <div class="course-card" style="border-left-color:#0a4d75">
            <strong>${r.rule_id}: ${r.title}</strong>
            <div class="block">${r.description}</div>
            ${r.enforcement ? `<div class="block" style="color:#2a9d8f">执行: ${r.enforcement}</div>` : ""}
          </div>`).join("")}
        </div>

        <h4 style="color:#E3120B;margin-top:1rem">正向铁律 (P1-P15)</h4>
        <div class="course-grid">${ironLaws.map(r => `
          <div class="course-card G_FINAL">
            <strong>${r.rule_id}: ${r.title}</strong>
            <div class="block">${r.description}</div>
          </div>`).join("")}
        </div>

        <h4 style="color:#888;margin-top:1rem">违宪清单 (V1-V8)</h4>
        <ul style="background:#fff;padding:0.5rem 2rem;border-radius:4px;font-size:0.9em">
          ${violations.map(r => `<li><strong style="color:#c1272d">${r.rule_id}</strong> ${r.title} → <em>${r.description}</em></li>`).join("")}
        </ul>
      </section>`;
  });

  // ===================================================================
  // E. 学生档案 (#39 真接入)
  // ===================================================================
  register("students", async () => {
    CONTENT.innerHTML = `<h2>E. 学生档案</h2><p>载入中...</p>`;
    const [list, classes] = await Promise.all([
      fetchJSON("/api/students/list"),
      fetchJSON("/api/students/classes"),
    ]);
    let html = `<h2>E. 学生档案 (${list.count} 学生 · ${classes.count} 班)</h2>

      <section class="layer-section">
        <h3>🎯 新学生入测 · 摸底测验</h3>
        <p style="color:#666;font-size:0.9em">巧妙 9-11 题快速摸清水平 → 自动推送对应 layer 课节 + 弱点</p>
        <div style="display:flex;gap:0.5rem;margin:0.5rem 0">
          <button onclick="window._startPlacement('G1')" style="padding:0.4rem 1rem;background:#2a9d8f;color:#fff;border:0;border-radius:3px;cursor:pointer">G1 入测 (9 题)</button>
          <button onclick="window._startPlacement('G2')" style="padding:0.4rem 1rem;background:#f4a261;color:#fff;border:0;border-radius:3px;cursor:pointer">G2 入测 (10 题)</button>
          <button onclick="window._startPlacement('G3')" style="padding:0.4rem 1rem;background:#e76f51;color:#fff;border:0;border-radius:3px;cursor:pointer">G3 入测 (11 题)</button>
        </div>
      </section>

      <section class="layer-section">
        <h3>班级 <span class="layer-meta">${classes.count}</span></h3>
        <div class="course-grid">`;
    for (const c of classes.classes) {
      html += `<div class="course-card">
        <strong>${c.name}</strong>
        <div class="block">${c.school} · ${c.grade}</div>
        <div class="block">学生: ${c.n_students}</div>
      </div>`;
    }
    html += `</div></section>
      <section class="layer-section">
        <h3>学生列表 <span class="layer-meta">点击查弱点 + 推送课节</span></h3>
        <div class="course-grid">`;
    for (const s of list.students) {
      html += `<div class="course-card" onclick="window._openStudent('${s.student_id}')">
        <strong>${s.name}</strong> <span class="layer-badge">${s.grade}</span>
        <div class="block">学号: ${s.student_id}</div>
        <div class="block">${s.school} · ${s.city}</div>
      </div>`;
    }
    html += `</div></section>
      <div id="student-modal" onclick="if(event.target===this)this.classList.remove('open')">
        <div class="modal-body">
          <span class="close-btn" onclick="document.getElementById('student-modal').classList.remove('open')">✕</span>
          <div id="student-content">载入中...</div>
        </div>
      </div>`;
    CONTENT.innerHTML = html;
  });

  // 摸底测验流程 — D2 用户 2026-05-25
  window._startPlacement = async (grade) => {
    CONTENT.innerHTML = `<h2>📝 ${grade} 摸底测验</h2><p>载入题目 ...</p>`;
    try {
      const paper = await fetchJSON("/api/placement/generate?grade=" + grade);
      let html = `<h2>📝 ${grade} 摸底测验 (${paper.total_actual} 题)</h2>
        <p style="color:#666">答完点"提交"自动评分 + 推送对应课节. 不会的题留空.</p>
        <form id="placement-form" style="background:#fff;padding:1rem;border-radius:4px;max-width:700px">`;
      let i = 0;
      for (const blk of paper.blocks) {
        html += `<h3 style="border-bottom:1px solid #ddd">${blk.kind} (${blk.type}) — ${blk.n_actual} 题</h3>`;
        for (const q of blk.questions) {
          i++;
          html += `<div style="margin:0.7rem 0;padding:0.5rem;background:#fafafa;border-left:3px solid #ddd">
            <strong>${i}.</strong> <small style="color:#888">[#${q.qb_id}, ${q.difficulty}]</small>
            <div style="margin:0.3rem 0">${(q.stem || "").slice(0, 200)}</div>
            <input type="text" name="ans_${q.qb_id}" placeholder="答案 (eg A/B/C/D 或文本)" style="width:300px;padding:0.3rem">
          </div>`;
        }
      }
      html += `<button type="submit" style="background:#E3120B;color:#fff;border:0;padding:0.6rem 1.5rem;border-radius:3px;cursor:pointer">提交评分</button>
        <button type="button" onclick="window.location.hash='#/students'" style="margin-left:0.5rem;padding:0.6rem 1rem">取消</button>
        </form>
        <div id="placement-result" style="margin-top:1rem"></div>`;
      CONTENT.innerHTML = html;

      document.getElementById("placement-form").onsubmit = async (ev) => {
        ev.preventDefault();
        const form = ev.target;
        const answers = {};
        for (const blk of paper.blocks) for (const q of blk.questions) {
          const v = form[`ans_${q.qb_id}`].value.trim();
          if (v) answers[q.qb_id] = v;
        }
        const resp = await fetch("/api/placement/score?grade=" + grade, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ answers }),
        });
        const result = await resp.json();
        const rd = document.getElementById("placement-result");
        const verdict = (result.layer_recommendation || {}).verdict;
        if (verdict === "consolidate" || verdict === "below") {
          await _runFollowup(rd, result, paper, grade);
        } else {
          _showFinalResult(rd, result);
        }
      };
    } catch (err) {
      CONTENT.innerHTML = `<h2>载入失败</h2><p style="color:#c00">${err.message}</p>`;
    }
  };

  function _showFinalResult(rd, result) {
    rd.innerHTML = `<div style="background:#fff;padding:1rem;border-left:4px solid #E3120B;border-radius:4px">
      <h3>评分结果</h3>
      <p><strong>正确率: ${((result.combined_accuracy || result.accuracy) * 100).toFixed(1)}%</strong>
        ${result.phase1_accuracy != null ? `(一阶段 ${(result.phase1_accuracy * 100).toFixed(1)}% + 二阶段 ${(result.phase2_accuracy * 100).toFixed(1)}%)` : `(${result.n_correct}/${result.n_total})`}</p>
      <p><strong>${result.layer_recommendation.msg}</strong></p>
      <h4>弱点 (${result.weak_concepts.length})</h4>
      <ul>${result.weak_concepts.slice(0, 8).map(w => `<li>${GZ.conceptLink(w.concept_id, w.concept_id)}</li>`).join("")}</ul>
      <h4>推送课节 (${result.recommended_courses.length})</h4>
      <ul>${result.recommended_courses.map(c => `<li><a href="#" onclick="window._openHandout(${c.course_id});return false">#${c.course_id} [${c.layer}] ${c.title}</a> &larr; ${c.weak_concept}</li>`).join("")}</ul>
    </div>`;
  }

  async function _runFollowup(rd, firstResult, paper, grade) {
    const allQids = [];
    const wrongQids = [];
    const form = document.getElementById("placement-form");
    for (const blk of paper.blocks) for (const q of blk.questions) {
      allQids.push(q.qb_id);
      const studentAns = (form[`ans_${q.qb_id}`] ? form[`ans_${q.qb_id}`].value.trim().toUpperCase() : "");
      const correctAns = (q.answer || "").trim().toUpperCase();
      if (!studentAns || studentAns !== correctAns) wrongQids.push(q.qb_id);
    }
    rd.innerHTML = `<div style="background:#fffbe6;padding:1rem;border-left:4px solid #faad14;border-radius:4px">
      <h3>一阶段结果: ${(firstResult.accuracy * 100).toFixed(1)}% — ${firstResult.layer_recommendation.msg}</h3>
      <p>正在加载追问题 (3-5 题深挖弱点) ...</p>
    </div>`;
    try {
      const fuResp = await fetch("/api/placement/followup", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ wrong_qids: wrongQids, all_qids: allQids, grade }),
      });
      const fuData = await fuResp.json();
      if (!fuData.questions || fuData.questions.length === 0) {
        _showFinalResult(rd, firstResult);
        return;
      }
      let html = `<div style="background:#fffbe6;padding:1rem;border-left:4px solid #faad14;border-radius:4px;margin-bottom:1rem">
        <h3>一阶段: ${(firstResult.accuracy * 100).toFixed(1)}% — 需追问确认</h3>
        <p>针对弱点 ${fuData.weak_tags_targeted.slice(0,3).join(", ")} 追问 ${fuData.n_questions} 题</p>
      </div>
      <form id="followup-form" style="background:#fff;padding:1rem;border-radius:4px;max-width:700px">`;
      fuData.questions.forEach((q, i) => {
        html += `<div style="margin:0.7rem 0;padding:0.5rem;background:#fafafa;border-left:3px solid #faad14">
          <strong>追${i+1}.</strong> <small style="color:#888">[#${q.qb_id}, ${q.difficulty}]</small>
          <div style="margin:0.3rem 0">${(q.stem || "").slice(0, 200)}</div>
          <input type="text" name="fu_${q.qb_id}" placeholder="答案" style="width:300px;padding:0.3rem">
        </div>`;
      });
      html += `<button type="submit" style="background:#E3120B;color:#fff;border:0;padding:0.6rem 1.5rem;border-radius:3px;cursor:pointer">提交追问</button>
        </form><div id="followup-result"></div>`;
      rd.innerHTML = html;
      document.getElementById("followup-form").onsubmit = async (ev2) => {
        ev2.preventDefault();
        const f2 = ev2.target;
        const fuAnswers = {};
        for (const q of fuData.questions) {
          const v = f2[`fu_${q.qb_id}`].value.trim();
          if (v) fuAnswers[q.qb_id] = v;
        }
        const finalResp = await fetch("/api/placement/final_score", {
          method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({ first_result: firstResult, followup_answers: fuAnswers, followup_questions: fuData.questions }),
        });
        const finalResult = await finalResp.json();
        _showFinalResult(document.getElementById("followup-result"), finalResult);
      };
    } catch (err) {
      rd.innerHTML += `<p style="color:#c00">追问载入失败: ${err.message}</p>`;
      _showFinalResult(rd, firstResult);
    }
  }

  window._openStudent = async (sid) => {
    const modal = document.getElementById("student-modal");
    const cont = document.getElementById("student-content");
    modal.classList.add("open");
    modal.id = "handout-modal";  // reuse 样式
    cont.innerHTML = "载入中...";
    try {
      const [info, weak, rec] = await Promise.all([
        fetchJSON("/api/students/get?id=" + sid),
        fetchJSON("/api/students/weakness?id=" + sid),
        fetchJSON("/api/students/recommend?id=" + sid),
      ]);
      let h = `<h2 style="margin:0">${info.student.name} (${sid})</h2>`;
      h += `<p>${info.student.school} · ${info.student.grade} · 答题 ${info.answers.total} 题 (正确 ${info.answers.correct})</p>`;
      h += `<h3>弱点 (${weak.count})</h3><ul>`;
      for (const w of weak.weakness) {
        h += `<li>[${w.kind}] <strong>${w.concept_id}</strong> — 弱化度 ${w.score} (样本 ${w.sample_n})</li>`;
      }
      h += `</ul><h3>推送课节 (${rec.count})</h3><ul>`;
      for (const r of rec.recommendations) {
        h += `<li><a href="#" onclick="window._openHandout(${r.course_id});return false">#${r.course_id} [${r.layer}] ${r.title}</a> ← ${r.weak_concept}</li>`;
      }
      h += `</ul>`;
      cont.innerHTML = h;
    } catch (err) {
      cont.innerHTML = "载入失败: " + err.message;
    }
  };

  // ===================================================================
  // F. 知识图谱 (复用 /teacher 的图谱 tab, iframe 嵌)
  // ===================================================================
  register("graph", async () => {
    CONTENT.innerHTML = `<h2>F. 知识图谱</h2><p>载入中 ...</p>`;
    const [gstats, trend] = await Promise.all([
      fetchJSON("/api/graph/stats").catch(() => ({})),
      fetchJSON("/api/trend/summary").catch(() => ({})),
    ]);
    // /api/graph/stats 实际字段: {nodes, edges, total_nodes, total_edges}
    // nodes 是 {kind: count}, edges 是 {relation: count}
    const nodeKinds = gstats.nodes || gstats.by_node_type || {};
    const relations = gstats.edges || gstats.by_relation || {};
    CONTENT.innerHTML = `
      <h2>F. 知识图谱 · 探索入口</h2>
      <p style="color:#666">点任一节点 → 弹联通图 + 真题 (graph_popup 全局浮窗). 此 tab 列入口节点 + 命题趋势.</p>

      <h3>图谱概览</h3>
      <div class="course-grid">
        <div class="course-card"><strong>nodes by type</strong>
          ${Object.entries(nodeKinds).map(([k, v]) => `<div class="block">${k}: ${v}</div>`).join("")}
        </div>
        <div class="course-card"><strong>edges by relation (top 6)</strong>
          ${Object.entries(relations).slice(0, 6).map(([k, v]) => `<div class="block">${k}: ${v}</div>`).join("")}
        </div>
      </div>

      <h3>探索入口 — 点任一概念弹联通图 + 真题</h3>
      <div id="graph-explore" style="background:#fff;padding:1rem;border-radius:4px">
        <p>载入热门 concept ...</p>
      </div>

      <h3>命题趋势</h3>
      <div class="course-grid">
        <div class="course-card G_FINAL"><strong>📈 近年高频上升词</strong>
          ${(trend.top_words || trend.rising_words || []).slice(0, 8)
            .map(w => `<div class="block">${GZ.conceptLink("word:" + (w.word || w.label || w), w.word || w.label || w)} ${w.recent_freq ? `(${w.recent_freq})` : ""}</div>`).join("") || "<div class='block'>无</div>"}
        </div>
        <div class="course-card"><strong>📊 题型年趋势</strong>
          ${Object.entries(trend.type_distribution_by_year || {}).slice(-3).map(
            ([y, types]) => `<div class="block">${y}: ${Object.keys(types).slice(0, 3).join(" / ")}</div>`
          ).join("") || "<div class='block'>无</div>"}
        </div>
      </div>

      <p style="margin-top:1rem;color:#888">老 /teacher 图谱保留为兼容 → <a href="/teacher" target="_blank">/teacher</a></p>`;

    // 异步载热门 concept (high exam_status=core word 前 20)
    try {
      const top = await fetchJSON("/api/recommend/top_exam_words?limit=20").catch(() => ([]));
      const items = Array.isArray(top) ? top : (top.words || top.items || []);
      const explore = document.getElementById("graph-explore");
      if (items.length) {
        explore.innerHTML = items.map(it => {
          const w = it.word || it.label || it.id || it;
          const cid = w.startsWith && w.startsWith("word:") ? w : "word:" + w;
          return GZ.conceptLink(cid, w.replace(/^word:/, ""));
        }).join("&nbsp; ");
      } else {
        explore.innerHTML = "<p>无 top exam words 数据.</p>";
      }
    } catch (err) {
      document.getElementById("graph-explore").innerHTML = `<p>载入失败: ${err.message}</p>`;
    }
  });

  // ===================================================================
  // G. 扫描 OCR (占位 4.7.C)
  // ===================================================================
  register("scan", async () => {
    CONTENT.innerHTML = `<h2>G. 扫描 OCR</h2><p>载入中 ...</p>`;
    const [list, students] = await Promise.all([
      fetchJSON("/api/scan/list").catch(() => []),
      fetchJSON("/api/students/list").catch(() => ({ students: [] })),
    ]);
    const rows = Array.isArray(list) ? list : (list.rows || []);
    const studentOpts = (students.students || [])
      .map(s => `<option value="${s.student_id}">${s.name} (${s.student_id})</option>`).join("");
    CONTENT.innerHTML = `
      <h2>G. 扫描 OCR · 学生卷面上传</h2>
      <p style="color:#666">PDF: 自动 pypdf 抽文字 / 图片: 留 PaddleOCR 后续.</p>

      <section class="layer-section">
        <h3>上传新扫描</h3>
        <form id="scan-form" style="background:#fff;padding:1rem;border-radius:4px;max-width:500px">
          <div style="margin:0.5rem 0">
            <label>学生 (可选):
              <select name="student_id" style="width:100%">
                <option value="">--- 未关联 ---</option>
                ${studentOpts}
              </select>
            </label>
          </div>
          <div style="margin:0.5rem 0">
            <label>类型:
              <select name="kind" style="width:100%">
                <option value="answer_sheet">答题卡</option>
                <option value="homework">作业</option>
                <option value="essay">作文</option>
              </select>
            </label>
          </div>
          <div style="margin:0.5rem 0">
            <label>文件 (PDF 优先):
              <input type="file" name="file" accept=".pdf,.jpg,.jpeg,.png" required>
            </label>
          </div>
          <button type="submit" style="background:#E3120B;color:#fff;border:0;padding:0.5rem 1rem;border-radius:3px;cursor:pointer">上传</button>
          <div id="scan-result" style="margin-top:0.7rem;color:#1a5e1a"></div>
        </form>
      </section>

      <section class="layer-section">
        <h3>已上传 (${rows.length})</h3>
        <table style="width:100%;background:#fff;border-collapse:collapse">
          <thead><tr style="background:#1a1a1a;color:#fff">
            <th style="padding:0.4rem;text-align:left">upload_id</th>
            <th style="padding:0.4rem">学生</th>
            <th style="padding:0.4rem">类型</th>
            <th style="padding:0.4rem">OCR 状态</th>
            <th style="padding:0.4rem">时间</th>
          </tr></thead>
          <tbody>
            ${rows.length ? rows.map(r => `<tr style="border-bottom:1px solid #eee">
              <td style="padding:0.3rem"><code>${r.upload_id || r[0]}</code></td>
              <td style="padding:0.3rem">${r.student_id || r[1] || "-"}</td>
              <td style="padding:0.3rem">${r.upload_kind || r[3] || "-"}</td>
              <td style="padding:0.3rem"><span class="${(r.ocr_status||r[5])==='done'?'gz-type-grammar':'gz-type-theme'}">${r.ocr_status || r[5] || "-"}</span></td>
              <td style="padding:0.3rem"><small>${(r.uploaded_at || r[4] || "").slice(0,19).replace('T',' ')}</small></td>
            </tr>`).join("") : `<tr><td colspan="5" style="padding:1rem;color:#888;text-align:center">无上传记录</td></tr>`}
          </tbody>
        </table>
      </section>`;

    document.getElementById("scan-form").onsubmit = async (ev) => {
      ev.preventDefault();
      const form = ev.target;
      const file = form.file.files[0];
      const resultDiv = document.getElementById("scan-result");
      if (!file) { resultDiv.innerHTML = `<span style="color:#c00">请选文件</span>`; return; }
      resultDiv.textContent = "上传中 ...";
      const params = new URLSearchParams({
        student_id: form.student_id.value,
        kind:       form.kind.value,
        filename:   file.name,
      });
      try {
        const resp = await fetch("/api/scan/upload?" + params, {
          method: "POST",
          headers: { "Content-Type": "application/octet-stream" },
          body: file,
        });
        const data = await resp.json();
        if (resp.ok) {
          resultDiv.innerHTML = `✅ 上传成功 <code>${data.upload_id}</code>; sha=${data.sha256}; OCR 状态=${data.ocr_status} (${data.text_chars} 字符)`;
          setTimeout(() => route(), 1500);  // 刷新清单
        } else {
          resultDiv.innerHTML = `<span style="color:#c00">❌ ${data.error || resp.statusText}</span>`;
        }
      } catch (err) {
        resultDiv.innerHTML = `<span style="color:#c00">❌ ${err.message}</span>`;
      }
    };
  });
})();
