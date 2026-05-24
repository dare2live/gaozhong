/* student.js — 学生端 (从 student.html 抽, Rule 5). */
const { $, $$, fetchJSON } = GZ;
const CITY_TO_VER = { "外研版": "waiyan", "人教版": "renjiao" };
let activeVersion = "waiyan";

async function loadCities() {
  const rows = await fetchJSON("/api/liaoning/city_choice");
  $("#city-pick").innerHTML = rows.map(r =>
    `<button data-pub="${r.publisher_short}" data-city="${r.city}">${r.city}<span style="font-size:10px;opacity:0.6"> (${r.publisher_short})</span></button>`).join("");
  $$("#city-pick button").forEach(b => b.addEventListener("click", () => pickCity(b)));
  pickCity($('[data-city="沈阳"]'));
}
function pickCity(b) {
  $$("#city-pick button").forEach(x => x.classList.remove("active"));
  b.classList.add("active");
  const pub = b.dataset.pub;
  activeVersion = CITY_TO_VER[pub] || "waiyan";
  $("#cur-version").textContent = `${pub} (${activeVersion})`;
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
function submitQuiz() {
  let correct = 0;
  window.__quiz.questions.forEach(q => {
    const ans = window.__answers[q.seq];
    const elQ = document.querySelector(`.quiz-q[data-seq="${q.seq}"]`);
    elQ.querySelectorAll("li").forEach(li => {
      if (li.dataset.label === q.answer) li.style.background = "#d6e9d6";
      else if (li.dataset.label === ans) li.style.background = "#f9d4d4";
    });
    if (ans === q.answer) correct++;
  });
  const n = window.__quiz.questions.length;
  $("#stu-score").style.display = "block";
  $("#stu-score").innerHTML = `成绩: <b>${correct}/${n}</b> (${Math.round(100 * correct / n)}%)`;
}

document.addEventListener("DOMContentLoaded", () => {
  GZ.mountLayout("/student");
  loadCities();
  $("#stu-go").addEventListener("click", startQuiz);
});
