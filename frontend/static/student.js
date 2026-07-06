/* student.js — 学生端 (从 student.html 抽, Rule 5). */
const { $, $$, fetchJSON, fetchSafe, isErr } = GZ;
const CITY_TO_VER = { "外研版": "waiyan", "人教版": "renjiao" };
let activeVersion = "waiyan";
let activeCity = "沈阳";

// 坑(2026-07-06 数据关联设计审查批次6, 用户选定"最小闭环"方案): 学生端答题原来只在浏览器本地
// 计分从不写库, weakness画像永远吃不到真实作答。补最小身份模型(不建账号系统): 首次访问生成
// 'real-'前缀student_id存localStorage, 与既有5个demo学生(sy-2024-*)物理隔离, 不需要登录态。
function _getIdentity() {
  let id = localStorage.getItem("gz_student_id");
  let name = localStorage.getItem("gz_student_name");
  if (!id) {
    name = (window.prompt("首次使用, 请输入你的姓名(用于记录你的练习情况):") || "").trim() || "同学";
    id = "real-" + Math.random().toString(36).slice(2, 10);
    localStorage.setItem("gz_student_id", id);
    localStorage.setItem("gz_student_name", name);
  }
  return { id, name };
}

async function loadCities() {
  const rows = await fetchJSON("/api/liaoning/city_choice");
  $("#city-pick").innerHTML = rows.map(r =>
    `<button data-pub="${r.publisher_short}" data-city="${r.city}">${r.city}<span style="font-size:10px;opacity:0.6">(${r.publisher_short})</span></button>`).join("");
  $$("#city-pick button").forEach(b => b.addEventListener("click", () => pickCity(b)));
  pickCity($('[data-city="沈阳"]'));
}
function pickCity(b) {
  $$("#city-pick button").forEach(x => x.classList.remove("active"));
  b.classList.add("active");
  const pub = b.dataset.pub;
  activeVersion = CITY_TO_VER[pub] || "waiyan";
  activeCity = b.dataset.city || activeCity;
  // 坑(2026-07-05 根因审计): 原 `${pub} (${activeVersion})` 把内部教材版本 key(waiyan/renjiao) 冗余
  // 拼在已翻译好的中文出版社名旁边(如"外研版 (waiyan)"), 对学生/老师零信息增量。
  $("#cur-version").textContent = pub;
  loadUnits();
}
async function loadUnits() {
  const rows = await fetchJSON(`/api/units?version=${activeVersion}`);
  $("#stu-unit").innerHTML = rows.map(r =>
    `<option value="unit:${r.version_key}/${r.volume_key}/U${r.unit_number}">${r.volume_key} / Unit ${r.unit_number} — ${r.title_en || ""}</option>`).join("");
}
async function startQuiz() {
  const unit = $("#stu-unit").value;
  const d = await fetchJSON(`/api/exercise/l1?unit=${encodeURIComponent(unit)}&n=5`);
  $("#stu-quiz-card").style.display = "block";
  $("#stu-score").style.display = "none";
  if (d.error) { $("#stu-quiz").innerHTML = `<em>${d.error}</em>`; return; }
  window.__quiz = d; window.__answers = {};
  $("#stu-quiz").innerHTML = d.questions.map(q => `
    <div class="quiz-q" data-seq="${q.seq}" data-answer="${q.answer}">
      <p><b>${q.seq}.</b> ${q.stem}</p>
      <ul class="quiz-opts">
        ${q.options.map(o => `<li data-label="${o.label}"><b>${o.label}.</b> ${o.text}</li>`).join("")}
      </ul>
    </div>`).join("") +
    `<button id="stu-submit" class="btn-primary" style="margin-top:10px">交卷</button>`;
  $$(".quiz-opts li").forEach(li => {
    li.addEventListener("click", () => {
      const q = li.closest(".quiz-q");
      q.querySelectorAll("li").forEach(x => x.style.background = "");
      li.style.background = "#e0eaf2";
      window.__answers[q.dataset.seq] = li.dataset.label;
    });
  });
  $("#stu-submit").addEventListener("click", submitQuiz);
}
async function submitQuiz() {
  let correct = 0;
  const answers = [];
  window.__quiz.questions.forEach(q => {
    const ans = window.__answers[q.seq];
    const ok = ans === q.answer;
    const elQ = document.querySelector(`.quiz-q[data-seq="${q.seq}"]`);
    elQ.querySelectorAll("li").forEach(li => {
      if (li.dataset.label === q.answer) li.style.background = "#d6e9d6";
      else if (li.dataset.label === ans) li.style.background = "#f9d4d4";
    });
    if (ok) correct++;
    // word_concept 来自题目 evidence(生成时已挂), 供后端归到真实考点做弱点计算(找不到就诚实存None)
    answers.push({ word_concept: (q.evidence && q.evidence.word_concept) || null, choice: ans || null, is_correct: ok });
  });
  const n = window.__quiz.questions.length;
  $("#stu-score").style.display = "block";
  $("#stu-score").innerHTML = `成绩: <b>${correct}/${n}</b> (${Math.round(100 * correct / n)}%)`;
  // 坑(2026-07-06 数据关联设计审查批次6): 交卷原来只在本地计分, 从不写库。补写入闭环, 失败要
  // 显式告知(D0诚实, 不静默吞错)——但不阻塞学生已经看到的本地成绩展示。
  const { id, name } = _getIdentity();
  const resp = await fetchSafe("/api/student_answers", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ student_id: id, name, city: activeCity, answers }),
  }).catch(() => ({ __err: "network error" }));
  const saveNote = document.createElement("p");
  saveNote.style.cssText = "font-size:12px;margin-top:6px;";
  if (isErr(resp)) {
    saveNote.style.color = "var(--accent-ink, #9C2C20)";
    saveNote.textContent = "本次练习记录未能保存(网络或服务异常), 成绩仅本地展示。";
  } else {
    saveNote.style.color = "var(--ink-3, #76716A)";
    saveNote.textContent = `已记录本次练习 (${name})。`;
  }
  $("#stu-score").appendChild(saveNote);
}

document.addEventListener("DOMContentLoaded", () => {
  GZ.mountLayout("/student");
  loadCities();
  $("#stu-go").addEventListener("click", startQuiz);
});
