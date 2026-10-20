// Chat client: pick a synthetic pupil, hold a guided conversation, render the tutor's widgets, and show the lesson the
// map's briefing describes. Process events (hints opened, confidence) ride along with the pupil's next message.
const $ = (id) => document.getElementById(id);
const { el } = window.Widgets;

const SUBJECTS = { maths: "Maths: linear equations", english: "English: Macbeth" };
const STARTERS = {
  maths: ["I'm stuck on an equation", "Give me a question to practise", "Can you check my answer?", "Explain the method again"],
  english: ["Help me analyse a quotation", "What should I know about Lady Macbeth?", "Give me a question to practise", "Check my paragraph"],
};
const QUICK = ["I'm stuck", "Show me an example", "Explain it another way", "Give me another one"];

let pupils = [];
let conversationId = newId();
let lastReplyAt = null;
let pending = []; // process events since the tutor's last reply
let busy = false;

function newId() {
  return Array.from(crypto.getRandomValues(new Uint8Array(12)), (b) => b.toString(16).padStart(2, "0")).join("");
}
const current = () => pupils.find((p) => p.id === $("pupil").value);
const firstName = (p) => (p ? p.name.replace(/\s*\(synthetic\)/, "").split(" ")[0] : "");
const secondsSinceReply = () => (lastReplyAt ? Math.round((Date.now() - lastReplyAt) / 1000) : 0);

// ---------------------------------------------------------------- text: a tiny, safe markdown subset
function inline(text) {
  const out = [];
  const rx = /\*\*(.+?)\*\*|\*(.+?)\*/g;
  let last = 0, m;
  while ((m = rx.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    out.push(m[1] ? el("strong", {}, m[1]) : el("em", {}, m[2]));
    last = rx.lastIndex;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

function richText(text) {
  const frag = document.createDocumentFragment();
  for (const block of text.split(/\n\s*\n/)) {
    const lines = block.split("\n").filter((l) => l.trim());
    if (!lines.length) continue;
    const bullets = lines.every((l) => /^\s*[-*•]\s+/.test(l));
    const numbers = lines.every((l) => /^\s*\d+[.)]\s+/.test(l));
    if (bullets || numbers) {
      const list = el(numbers ? "ol" : "ul");
      lines.forEach((l) => list.append(el("li", {}, inline(l.replace(/^\s*([-*•]|\d+[.)])\s+/, "")))));
      frag.append(list);
    } else {
      const p = el("p");
      lines.forEach((l, i) => { if (i) p.append(el("br")); p.append(...inline(l)); });
      frag.append(p);
    }
  }
  return frag;
}

// ---------------------------------------------------------------- speech
const voices = () => (window.speechSynthesis ? speechSynthesis.getVoices() : []);
function speak(text) {
  if (!window.speechSynthesis) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text.replace(/\*+/g, ""));
  u.lang = "en-GB";
  const v = voices().find((x) => x.lang === "en-GB") || voices().find((x) => x.lang.startsWith("en"));
  if (v) u.voice = v;
  u.rate = 0.95;
  speechSynthesis.speak(u);
}

function setupMic() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return;
  const mic = $("mic");
  mic.hidden = false;
  let rec = null;
  mic.addEventListener("click", () => {
    if (rec) { rec.stop(); return; }
    rec = new SR();
    rec.lang = "en-GB";
    rec.interimResults = true;
    const base = $("msg").value ? $("msg").value.trimEnd() + " " : "";
    rec.onresult = (e) => {
      $("msg").value = base + Array.from(e.results, (r) => r[0].transcript).join("");
      grow();
    };
    rec.onend = () => { rec = null; mic.classList.remove("listening"); mic.setAttribute("aria-label", "Speak your message"); };
    mic.classList.add("listening");
    mic.setAttribute("aria-label", "Stop listening");
    rec.start();
  });
}

// ---------------------------------------------------------------- messages
function scrollDown() { $("log").scrollTop = $("log").scrollHeight; }

function addPupil(text) {
  $("welcome").hidden = true;
  $("log").append(el("div", { class: "msg pupil" }, el("div", { class: "bubble" }, text)));
  scrollDown();
}

function addTyping() {
  const t = el("div", { class: "msg tutor typing", "aria-label": "Tutor is typing" },
    el("div", { class: "avatar", "aria-hidden": "true" }, "T"), el("div", { class: "bubble" }, el("i"), el("i"), el("i")));
  $("log").append(t);
  scrollDown();
  return t;
}

function addTutor(body) {
  document.querySelectorAll(".msg.tutor:not(.stale)").forEach((m) => m.classList.add("stale"));
  const bubble = el("div", { class: "bubble" + (body.briefing_ok === false ? " warn" : "") }, richText(body.reply));
  const widgets = window.Widgets.render(body.widgets, { send: submit, event: queueEvent, speak });
  if (widgets) bubble.append(widgets);

  const meta = el("div", { class: "meta" });
  if (window.speechSynthesis) meta.append(el("button", { type: "button", onclick: () => speak(body.reply) }, "🔊 Listen"));
  if (body.evidence) {
    const s = body.evidence.score;
    const cls = !body.evidence.ok ? "" : s >= 1 ? "good" : s > 0 ? "part" : "bad";
    meta.append(el("span", { class: `tag ${cls}` }, body.evidence.ok ? (s >= 1 ? "Correct" : s > 0 ? "Partly right" : "Not yet") : "Answer not saved"));
  }
  if (body.briefing_ok === false) meta.append(el("span", { class: "tag part" }, "No briefing from the map"));
  if (body.focus) meta.append(el("span", { class: "tag tester-only" }, `Focus: ${body.focus}`));
  const adj = body.adjustments;
  if (adj && (adj.applied.length || adj.widget_changes.length)) {
    const notes = [...adj.widget_changes, ...(adj.text_flags || []).map((f) => `text: ${f}`),
                   ...adj.unrecognised.map((u) => `unrecognised adjustment: ${u}`)];
    meta.append(el("span", { class: "tag tester-only" }, `Adjustments: ${adj.applied.join(", ") || "none"}`));
    if (notes.length) meta.append(el("ul", { class: "audit tester-only" }, notes.map((n) => el("li", {}, n))));
  }
  bubble.append(meta);

  $("log").append(el("div", { class: "msg tutor" }, el("div", { class: "avatar", "aria-hidden": "true" }, "T"), bubble));
  scrollDown();
}

function addError(text) {
  $("log").append(el("div", { class: "msg tutor" }, el("div", { class: "avatar", "aria-hidden": "true" }, "!"),
    el("div", { class: "bubble warn" }, text)));
  scrollDown();
}

function queueEvent(type, extra) {
  pending.push({ type, t: secondsSinceReply(), ...(extra || {}) });
}

// ---------------------------------------------------------------- lesson panel
function renderLesson(lesson, briefing) {
  $("briefing").textContent = briefing ? JSON.stringify(briefing, null, 2) : "No briefing for this turn (the map could not be reached).";
  if (!lesson) return;
  $("topic").textContent = lesson.topic || "General help";
  $("topic").classList.toggle("muted", !lesson.topic);

  const when = $("topicWhen");
  when.hidden = !lesson.topic_week;
  when.className = "badge" + (lesson.topic_taught ? "" : " later");
  when.textContent = lesson.topic_taught ? `Taught in week ${lesson.topic_week}` : `Coming up in week ${lesson.topic_week}`;

  const m = $("method");
  m.replaceChildren();
  if (lesson.method) m.append(el("dt", {}, "Method"), el("dd", {}, lesson.method));
  if (lesson.representation) m.append(el("dt", {}, "Picture it"), el("dd", {}, lesson.representation));
  m.hidden = !m.childElementCount;

  $("nextUp").hidden = !lesson.next;
  $("nextUp").textContent = lesson.next ? `Next: ${lesson.next}` : "";

  const sc = $("scheme");
  sc.replaceChildren(...(lesson.scheme || []).map((s) => el("li",
    { class: `${s.status}${s.focus ? " focus" : ""}`, title: s.status === "taught" ? "Taught" : "Coming up" },
    el("span", { class: "wk" }, s.week ? `Wk${s.week}` : ""), el("span", {}, s.label))));
  const txt = $("text");
  txt.hidden = !(lesson.text_studied && lesson.text_studied.length);
  if (!txt.hidden) txt.textContent = `Studied so far: ${lesson.text_studied.join(", ")}.` + (lesson.text_coming && lesson.text_coming.length ? ` Coming up: ${lesson.text_coming.join(", ")}.` : "");
}

// ---------------------------------------------------------------- session shape
const STAGES = ["goal", "warm_up", "practice", "wrap_up"];

function renderSession(sess) {
  $("sessionBar").hidden = !sess;
  if (!sess) return;
  $("goal").textContent = sess.goal ? (sess.goal_is_preview ? `First look: ${sess.goal}` : sess.goal) : "Whatever you need";
  $("goal").title = $("goal").textContent;
  // stage shown is where the session is now: the server reports the stage for the next turn
  const now = STAGES.indexOf(sess.phase);
  document.querySelectorAll("#stages li").forEach((li) => {
    const i = STAGES.indexOf(li.dataset.stage);
    li.hidden = li.dataset.stage === "warm_up" && !sess.recall_topic;
    li.className = i < now ? "done" : i === now ? "now" : "";
    if (li.dataset.stage === "warm_up" && sess.recall_topic) li.title = `Warm-up: ${sess.recall_topic}`;
  });
  $("finish").disabled = sess.finished;
}

function addSummary(sess) {
  const rows = [["Goal", sess.goal || "—"], ["Answers", `${sess.correct} of ${sess.answers} right`]];
  if (sess.recall_topic) rows.push(["Warm-up", `${sess.recall_topic}: ${sess.recall_result || "not done"}`]);
  if (sess.next_topic) rows.push(["Next time", sess.next_topic]);
  $("log").append(el("section", { class: "summary", "aria-label": "Session summary" },
    el("h2", {}, "Session complete"),
    el("dl", {}, rows.flatMap(([k, v]) => [el("dt", {}, k), el("dd", {}, v)])),
    el("button", { type: "button", class: "primary", onclick: reset }, "Start a new session")));
  scrollDown();
}

function addProgress(ev) {
  if (!ev || !ev.ok) return;
  const s = ev.score;
  $("progress").append(el("span", { class: `dot ${s >= 1 ? "good" : s > 0 ? "part" : "bad"}`, title: ev.activity }));
  const n = $("progress").childElementCount;
  const right = $("progress").querySelectorAll(".dot.good").length;
  $("progressNote").textContent = `${right} of ${n} answer${n === 1 ? "" : "s"} right so far.`;
}

// ---------------------------------------------------------------- pupils and conversation
function setChips(container, labels) {
  container.replaceChildren(...labels.map((t) => el("button", { type: "button", onclick: () => submit(t) }, t)));
}

function reset() {
  conversationId = newId();
  lastReplyAt = null;
  pending = [];
  if (window.speechSynthesis) speechSynthesis.cancel();
  const p = current();
  const subject = p ? p.subject : "maths";
  document.body.dataset.subject = subject;
  $("log").replaceChildren($("welcome"));
  $("welcome").hidden = false;
  $("hello").textContent = p ? `Hello, ${firstName(p)}!` : "Hello!";
  $("subject").textContent = p ? `${p.class} · ${SUBJECTS[subject] || subject}` : "";
  setChips($("starters"), STARTERS[subject] || STARTERS.maths);
  setChips($("quick"), QUICK);
  $("quick").hidden = true;
  $("topic").textContent = "Send a message to start.";
  $("topic").classList.add("muted");
  ["topicWhen", "method", "nextUp", "text"].forEach((id) => { $(id).hidden = true; });
  $("scheme").replaceChildren(el("li", { class: "placeholder muted small" }, "Appears after your first message."));
  $("progress").replaceChildren();
  $("progressNote").textContent = "Answers you give will show here.";
  $("briefing").textContent = "No turn yet.";
  renderSession(null);
}

async function loadPupils() {
  try {
    const r = await fetch("/api/pupils");
    if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
    pupils = await r.json();
    $("pupil").replaceChildren(...pupils.map((p) => el("option", { value: p.id }, `${firstName(p)} · ${p.class}`)));
    $("pupil").disabled = false;
    reset();
  } catch (e) {
    $("pupil").replaceChildren(el("option", {}, "Pupils unavailable"));
    addError(`I couldn't load the pupils from the curriculum map: ${e.message}`);
  }
}

async function submit(text, finish = false) {
  const p = current();
  const message = (text ?? $("msg").value).trim();
  if (!p || !message || busy) return;
  busy = true;
  $("send").disabled = true;
  addPupil(message);
  $("msg").value = "";
  grow();
  const typing = addTyping();
  const events = pending;
  pending = [];
  try {
    const r = await fetch("/api/turn", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ pupil: p.id, subject: p.subject, message, conversation_id: conversationId,
                             record_evidence: $("evidence").checked, elapsed_s: lastReplyAt ? secondsSinceReply() : null,
                             events, finish }),
    });
    const body = await r.json();
    if (!r.ok) throw new Error(body.detail || r.statusText);
    typing.remove();
    addTutor(body);
    renderLesson(body.lesson, body.briefing);
    renderSession(body.session);
    if (finish && body.session) addSummary(body.session);
    addProgress(body.evidence);
    $("quick").hidden = false;
    lastReplyAt = Date.now();
  } catch (e) {
    typing.remove();
    addError(`Something went wrong: ${e.message}`);
    pending = events.concat(pending);
  } finally {
    busy = false;
    $("send").disabled = false;
    $("msg").focus();
  }
}

function grow() {
  const t = $("msg");
  t.style.height = "auto";
  t.style.height = Math.min(t.scrollHeight, 180) + "px";
}

// ---------------------------------------------------------------- wiring
$("pupil").addEventListener("change", reset);
$("new").addEventListener("click", reset);
$("finish").addEventListener("click", () => submit("I'd like to finish for today.", true));
$("form").addEventListener("submit", (e) => { e.preventDefault(); submit(); });
$("msg").addEventListener("input", grow);
$("msg").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
});
$("tester").addEventListener("change", (e) => document.body.classList.toggle("tester", e.target.checked));
$("lessonToggle").addEventListener("click", (e) => {
  const open = document.body.classList.toggle("lesson-open");
  e.currentTarget.setAttribute("aria-expanded", String(open));
});
setupMic();
loadPupils();
