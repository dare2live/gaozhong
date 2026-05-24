/* SPA hash router — 7 tab (第五阶段 5.1).
   每 tab 一个 mount() 函数, 注册到 ROUTES dict. (M2 插件式 dispatch) */

(function () {
  const { $, $$, fetchJSON } = window.GZ;
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
    const [stats, cs] = await Promise.all([fetchJSON("/api/stats"), fetchJSON("/api/course/stats")]);
    CONTENT.innerHTML = `
      <h2>A. 工作台</h2>
      <div class="course-grid">
        <div class="course-card">
          <strong>数据健康</strong>
          <div class="block">nodes: ${stats.nodes ?? "-"} / edges: ${stats.edges ?? "-"}</div>
          <div class="block">question_bank: ${stats.question_bank ?? "-"} / tags: ${stats.question_tags ?? "-"}</div>
        </div>
        <div class="course-card G_FINAL">
          <strong>40 节课程</strong>
          <div class="block">G1: ${cs.by_layer?.G1 ?? 0} / G2: ${cs.by_layer?.G2 ?? 0} / G3: ${cs.by_layer?.G3 ?? 0} / G_FINAL: ${cs.by_layer?.G_FINAL ?? 0}</div>
          <div class="block">materials: ${cs.total_materials ?? 0}</div>
        </div>
        <div class="course-card">
          <strong>待补缺口</strong>
          <div class="block">学生档案 UI (#39 待做)</div>
          <div class="block">扫描 POST UI (4.7.C 待补)</div>
        </div>
      </div>`;
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
      md.textContent = data.md || JSON.stringify(data, null, 2);
    } catch (err) {
      md.textContent = "讲义载入失败: " + err.message;
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
    CONTENT.innerHTML = `
      <h2>F. 知识图谱</h2>
      <p>force-directed / 热力图 / 趋势 / 跨版本</p>
      <iframe src="/teacher" style="width:100%;height:80vh;border:1px solid #ddd;border-radius:4px"></iframe>`;
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
