// Minimal chat client: pick a synthetic pupil, hold a conversation, show what the map supplied each turn.
const $ = (id) => document.getElementById(id);
const SUBJECTS = { maths: "Maths: linear equations", english: "English: Macbeth" };
let pupils = [];
let conversationId = newId();
let lastReplyAt = null;

function newId() {
  return Array.from(crypto.getRandomValues(new Uint8Array(12)), (b) => b.toString(16).padStart(2, "0")).join("");
}

function current() {
  return pupils.find((p) => p.id === $("pupil").value);
}

function add(role, text, meta, warn) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  if (meta) {
    const m = document.createElement("div");
    m.className = "meta" + (warn ? " warn" : "");
    m.textContent = meta;
    div.appendChild(m);
  }
  $("log").appendChild(div);
  div.scrollIntoView({ block: "end" });
}

function reset() {
  conversationId = newId();
  lastReplyAt = null;
  $("log").replaceChildren();
  const p = current();
  $("subject").textContent = p ? `${p.class} · ${SUBJECTS[p.subject] || p.subject}` : "";
}

async function loadPupils() {
  try {
    const r = await fetch("/api/pupils");
    if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
    pupils = await r.json();
    $("pupil").replaceChildren(...pupils.map((p) => {
      const o = document.createElement("option");
      o.value = p.id;
      o.textContent = `${p.name.replace(/\s*\(synthetic\)/, "")} — ${p.class}`;
      return o;
    }));
    $("pupil").disabled = false;
    reset();
  } catch (e) {
    $("pupil").replaceChildren(new Option("Pupils unavailable"));
    add("tutor", `Could not load pupils from the curriculum map: ${e.message}`, null, true);
  }
}

async function send(ev) {
  ev.preventDefault();
  const p = current();
  const message = $("msg").value.trim();
  if (!p || !message) return;
  add("pupil", message);
  $("msg").value = "";
  $("send").disabled = true;
  const elapsed = lastReplyAt ? (Date.now() - lastReplyAt) / 1000 : null;
  try {
    const r = await fetch("/api/turn", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ pupil: p.id, subject: p.subject, message, conversation_id: conversationId,
                             record_evidence: $("evidence").checked, elapsed_s: elapsed }),
    });
    const body = await r.json();
    if (!r.ok) throw new Error(body.detail || r.statusText);
    const bits = [];
    if (body.briefing_ok) bits.push(`Briefing: ${body.focus || "no focus"}`);
    if (body.evidence) bits.push(body.evidence.ok ? `Answer recorded (score ${body.evidence.score})` : "Answer not recorded (map error)");
    add("tutor", body.reply, body.briefing_ok ? bits.join(" · ") : `No briefing: ${body.briefing_error}`, !body.briefing_ok);
    lastReplyAt = Date.now();
  } catch (e) {
    add("tutor", `Something went wrong: ${e.message}`, null, true);
  } finally {
    $("send").disabled = false;
    $("msg").focus();
  }
}

$("pupil").addEventListener("change", reset);
$("new").addEventListener("click", reset);
$("form").addEventListener("submit", send);
$("msg").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("form").requestSubmit(); }
});
loadPupils();
