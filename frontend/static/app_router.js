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
        <pre id="handout-md">载入中 ...</pre>
      </div>
    </div>`;
    CONTENT.innerHTML = html;
  });

  // 全局: 打开讲义 modal
  window._openHandout = async (cid) => {
    const modal = $("#handout-modal");
    const md = $("#handout-md");
    modal.classList.add("open");
    md.textContent = "载入中 ...";
    try {
      const data = await fetchJSON("/api/course/handout?id=" + cid);
      md.innerHTML = mdToHtml(data.md || "") || `<pre>${JSON.stringify(data, null, 2)}</pre>`;
    } catch (err) {
      md.innerHTML = "讲义载入失败: " + err.message;
    }
  };

  // ===================================================================
  // C. 题库 + 组卷
  // ===================================================================
  register("qbank", async () => {
    const [stats, st] = await Promise.all([fetchJSON("/api/stats"), fetchJSON("/api/course/stats").catch(()=>({}))]);
    CONTENT.innerHTML = `
      <h2>C. 题库 + 组卷</h2>
      <p>当前题库: <strong>${stats.question_bank ?? "-"}</strong> 题 / <strong>${stats.question_tags ?? "-"}</strong> 标签 / <strong>${stats.tag_dictionary ?? "-"}</strong> 标签字典</p>
      <p>听力题 (has_audio): 复用 /api/listening (待 #5.5.B 数据导入)</p>
      <p>详细组卷器: <a href="/teacher#compose" target="_blank">/teacher tab "组卷"</a> (兼容旧 UI)</p>
      <p style="margin-top:1.5rem;color:#888">/api/qb/* /api/paper/* /api/listening/* — 接口齐全, 此 tab UI 待迁移</p>`;
  });

  // ===================================================================
  // D. 数据管理
  // ===================================================================
  register("data", async () => {
    const [stats, audit] = await Promise.all([fetchJSON("/api/stats"), fetchJSON("/api/audit/findings").catch(()=>({findings:[]}))]);
    const f = audit.findings || [];
    const fail = f.filter(x => x.severity === "FAIL").length;
    const warn = f.filter(x => x.severity === "WARN").length;
    CONTENT.innerHTML = `
      <h2>D. 数据管理</h2>
      <p>14 数据集 + 自动审计</p>
      <div class="course-grid">
        <div class="course-card ${fail > 0 ? 'G_FINAL' : 'G1'}">
          <strong>审计概览</strong>
          <div class="block">FAIL: ${fail} / WARN: ${warn}</div>
        </div>
        <div class="course-card">
          <strong>nodes / edges</strong>
          <div class="block">${stats.nodes ?? "-"} / ${stats.edges ?? "-"}</div>
        </div>
        <div class="course-card">
          <strong>教材 / 课标</strong>
          <div class="block">textbooks: ${stats.textbooks ?? "-"} / curriculum vocab: ${stats.cefr_vocab ?? "-"}</div>
        </div>
        <div class="course-card">
          <strong>课程 (第五阶段)</strong>
          <div class="block">courses 40 / course_materials ${stats.course_materials ?? "-"}</div>
        </div>
      </div>
      <p style="margin-top:1.5rem"><a href="/teacher" target="_blank">详细数据 → /teacher</a></p>`;
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
    CONTENT.innerHTML = `
      <h2>G. 扫描 OCR</h2>
      <div class="tab-placeholder">
        <p>POST 通 (<code>/api/scan/upload</code>). UI 待 4.7.C 补:</p>
        <ul>
          <li>教师端上传 PDF / 图片</li>
          <li>已上传清单</li>
          <li>OCR review 队列 (人工校对)</li>
        </ul>
      </div>`;
  });
})();
