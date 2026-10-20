"""Build the system prompt and messages for one turn from whatever context the condition supplies.

Conditions (the map's evaluation harness calls them arms):
  h2          the briefing, rendered into named sections in order of authority (also what the UI uses)
  raw         the unorganised pack, passed verbatim as JSON so we test the map's organisation, not ours
  none        only {pupil: {name, year}}
  unavailable the UI could not reach the map; the tutor is told it has no context and must not guess

The fixed rules and the assessment instruction are identical in every condition, so the conditions differ only in
the context they carry.
"""
import json
import re
from dataclasses import dataclass, field

CONDITIONS = ("h2", "raw", "none", "unavailable")

SUBJECT_LABELS = {"maths": "Maths: linear equations", "english": "English: Macbeth"}

FIXED_RULES = """You are a patient tutor for a UK secondary pupil, working one to one in a chat. Subject: {subject_label}.

How to reply
- British English. Under 140 words unless an agreed adjustment sets a tighter limit.
- First, respond to what the pupil actually asked or said. Answer their question, or work with the answer they gave, before you suggest anything else. Only then, if useful, steer towards the next step in the briefing. Never ignore the question to jump to a weakness.
- One small step at a time. End with one question the pupil is expected to answer.
- Use the class's method and representation. Do not introduce a method listed under "Avoid".
- When the pupil gives an answer, say clearly whether it is right. If it is wrong, say which step went wrong and why. Never praise a wrong answer.
- Never describe the pupil with a label, and never mention the briefing, its fields, IDs, mastery scores, the platform, or that you have notes about them.
- Do not invent facts about the pupil, the class or the scheme of work. If the briefing does not say, you do not know.
- Use the teacher's materials where they fit; you may reuse their examples and wording.

Order of authority (highest first)
1. Agreed adjustments (if present). These are REQUIRED in every reply. If anything below conflicts with them, the agreed adjustments win.
2. Scope rule.
3. The pupil's message.
4. Guidance and teaching method.
5. Recent patterns ("how to support"), which are advisory only."""

WIDGET_RULES = """Optional interactive widgets
The pupil's screen can show up to 3 small interactive widgets under your reply. Your reply text must make complete sense without them: anything a widget shows (a diagram, the steps, the hint) must also be described or asked in your words. Widgets are part of your reply, so agreed adjustments, the scope rule and the class's method apply to them too (for example, a "steps" widget has one step if the pupil must get one step at a time, and there are no "hints" before the pupil has attempted the question if that is required). Use a widget only when it genuinely helps; most replies need none or one.
If you use any, add after your reply, on its own line, exactly one block:
<widgets>[ ... ]</widgets>
containing a JSON array of objects from this list only:
- {{"type": "answer", "prompt": "x =", "choices": []}}  a box for the pupil's answer to your question (choices optional, at most 5)
- {{"type": "hints", "hints": ["smallest hint", "a bigger hint"]}}  revealed one at a time when the pupil asks
- {{"type": "steps", "title": "...", "steps": ["...", "..."]}}  a worked example revealed one step at a time
- {{"type": "confidence", "prompt": "How sure are you?"}}  the pupil rates how sure they are
- {{"type": "balance", "left": "5x + 3", "right": "2x + 12", "operation": "subtract 2x from both sides", "result_left": "3x + 3", "result_right": "12"}}  maths: scales for the balance method (result optional)
- {{"type": "bar_model", "rows": [{{"label": "5x + 3", "segments": [{{"label": "x", "size": 1}}, {{"label": "3", "size": 0.6}}]}}], "caption": "..."}}  maths: bar model
- {{"type": "function_machine", "input": "x", "operations": ["× 3", "+ 2"], "output": "17"}}  maths: function machine
- {{"type": "number_line", "min": -5, "max": 5, "marks": [{{"value": -2, "label": "-2"}}], "caption": "..."}}  maths: number line
- {{"type": "quote", "text": "...", "speaker": "...", "act": "1.5", "focus_words": ["unsex"], "question": "..."}}  English: a quotation to look at closely
Prefer the class's own representation when it is listed."""

ASSESSMENT_RULES = """After your reply, on a new line, add exactly one assessment block. The pupil never sees it.
<assessment>{{"answered": <true if the pupil's latest message gives an answer to a question (yours or one they are working on), else false>, "question": "<the question they answered, or empty>", "answer": "<their answer, verbatim, or empty>", "correct": <true, false, or null if it cannot be judged>, "score": <0 to 1, how much of the question they got right, or null>, "misconception_id": <one id from the list below if the wrong answer clearly shows it, else null>}}</assessment>
Known misconceptions you may name: {misconceptions}"""

UNAVAILABLE_NOTE = ("The school's curriculum map could not be reached for this turn, so you have no information about this "
                    "pupil, their class or what they have been taught. Help with what they asked in general terms, do "
                    "not guess at their class's scheme of work or method, and do not claim to know what they have studied.")


@dataclass
class Prompt:
    system: str
    messages: list[dict]
    condition: str
    misconception_ids: list[str] = field(default_factory=list)


def first_name(name: str | None) -> str:
    if not name:
        return "the pupil"
    return re.sub(r"\s*\(synthetic\)\s*$", "", name).strip().split(" ")[0] or "the pupil"


def _labels(xs) -> str:
    return "; ".join(x["label"] if isinstance(x, dict) else str(x) for x in (xs or []))


def _misconceptions(briefing: dict) -> list[dict]:
    lr = briefing.get("learner") or {}
    return [m for m in (lr.get("active_misconceptions") or []) + (lr.get("other_active_misconceptions") or []) if m.get("id")]


def render_briefing(b: dict) -> str:
    """The briefing as named sections, in order of authority. Absent or empty sections are left out."""
    out: list[str] = []
    focus, lr, cls, g = b.get("focus") or {}, b.get("learner") or {}, b.get("class") or {}, b.get("guidance") or {}
    english = bool(cls.get("text_studied_so_far") is not None or str(focus.get("id", "")).startswith("cc:english/"))

    sp = b.get("support_profile")
    if sp and sp.get("adjustments"):
        out.append("## Agreed adjustments — REQUIRED\n" + (sp.get("rule") or "") + "\n"
                   + "\n".join(f"- {a['do']}" for a in sp["adjustments"] if a.get("do")))

    scope = [g["scope_rule"]] if g.get("scope_rule") else []
    if cls.get("taught_so_far"):
        scope.append("Taught so far: " + "; ".join(cls["taught_so_far"]))
    if cls.get("not_yet_taught"):
        scope.append("Not yet taught: " + "; ".join(cls["not_yet_taught"]))
    if english:
        if cls.get("text_studied_so_far"):
            scope.append("Studied so far: " + ", ".join(cls["text_studied_so_far"]) + ".")
        if cls.get("text_coming_up"):
            scope.append("Coming up: " + ", ".join(cls["text_coming_up"]) + ".")
    if focus.get("label") and "focus_taught" in cls:
        week = cls.get("focus_week")
        if cls["focus_taught"]:
            scope.append(f'This question\'s topic, "{focus["label"]}", is taught' + (f" (week {week})." if week else "."))
        else:
            scope.append(f'This question\'s topic, "{focus["label"]}", is NOT yet taught' + (f" — planned for week {week}." if week else "."))
    if scope:
        out.append("## Scope\n" + "\n".join(scope))

    req = b.get("request") or {}
    asking = []
    if focus.get("label"):
        asking.append(f"Topic: {focus['label']}" + (f" (intent: {req['intent']})" if req.get("intent") else ""))
    mentions = req.get("mentions") or {}
    if mentions.get("parts_of_text") or mentions.get("quotations"):
        asking.append("Parts of the text / quotations they mentioned: "
                      + "; ".join(map(str, (mentions.get("parts_of_text") or []) + (mentions.get("quotations") or []))))
    if asking:
        out.append("## What the pupil is asking about\n" + "\n".join(asking))

    tw = g.get("teach_with") or {}
    teach = []
    head = []
    if cls.get("teacher"):
        head.append("Class teacher: " + re.sub(r"\s*\(fictional\)", "", cls["teacher"]) + ".")
    if tw.get("method"):
        head.append(f"Method: {tw['method']['label']}.")
    if tw.get("representation"):
        head.append(f"Representation: {tw['representation']['label']}.")
    if head:
        teach.append(" ".join(head))
    if g.get("avoid_methods"):
        teach.append("Avoid: " + _labels(g["avoid_methods"]))
    if g.get("diagnosis"):
        teach.append(f"Diagnosis: {g['diagnosis']}")
    ns = g.get("next_step") or {}
    check = g.get("check_prerequisites_first") or ns.get("check_first") or []
    if ns.get("check_first") and g.get("check_prerequisites_first"):
        seen = {c.get("id") for c in g["check_prerequisites_first"]}
        check = g["check_prerequisites_first"] + [c for c in ns["check_first"] if c.get("id") not in seen]
    if check:
        teach.append("Check first: " + _labels(check))
    if ns.get("action"):
        teach.append(f"Next step: {ns['action']}" + (f" — {ns['why']}" if ns.get("why") else ""))
    if teach:
        out.append("## How to teach it\n" + "\n".join(teach))

    pupil = [f"First name: {first_name(lr.get('name'))}"]
    if lr.get("status"):
        pupil.append(f"On this topic: {lr['status']}")
    act = lr.get("active_misconceptions") or []
    other = lr.get("other_active_misconceptions") or []
    if act or other:
        line = "Known misconceptions: " + "; ".join(
            m["label"] + (f" — {m['description']}" if m.get("description") else "") for m in act)
        if other:
            line += ("; also: " if act else "") + _labels(other)
        pupil.append(line)
    if lr.get("prerequisites"):
        pupil.append("Prerequisites: " + "; ".join(f"{p['label']}: {p.get('status', '?')}" for p in lr["prerequisites"]))
    by_status: dict[str, list[str]] = {}
    for o in lr.get("overview") or []:
        by_status.setdefault(o.get("status", "unknown"), []).append(o["topic"])
    for st in ("secure", "developing", "gap"):
        if by_status.get(st):
            pupil.append(f"{st.capitalize()}: " + "; ".join(by_status[st]))
    if lr.get("related_topics"):
        pupil.append("Related topics: " + "; ".join(f"{t['topic']} ({t.get('status', '?')})" for t in lr["related_topics"]))
    out.append("## The pupil\n" + "\n".join(pupil))

    if b.get("key_quotations"):
        out.append("## Key quotations\n" + "\n".join(
            f"- \"{q['text']}\" — {q.get('speaker', '')}, {q.get('act', '')}".rstrip(", ") for q in b["key_quotations"]))

    if b.get("materials"):
        out.append("## Teacher's materials\n" + "\n".join(
            f"- {m.get('heading', 'Material')}" + (f" (week {m['week']})" if m.get("week") else "") + f": {m.get('excerpt', '')}"
            for m in b["materials"]))

    hs = b.get("how_to_support") or {}
    if hs.get("patterns_to_support") or hs.get("strengths"):
        lines = [hs.get("rule", "")]
        if hs.get("patterns_to_support"):
            lines.append("Patterns to support: " + _labels(hs["patterns_to_support"]))
        if hs.get("strengths"):
            lines.append("Strengths: " + _labels(hs["strengths"]))
        out.append("## Recent patterns — advisory\n" + "\n".join(l for l in lines if l))

    return "\n\n".join(out)


def build_prompt(subject: str, condition: str, context: dict | None, message: str,
                 history: list[dict] | None = None) -> Prompt:
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition {condition!r}")
    context = context or {}
    parts = [FIXED_RULES.format(subject_label=SUBJECT_LABELS.get(subject, subject))]
    mcs: list[dict] = []
    if condition == "h2":
        parts.append("# Briefing for this turn\n\n" + render_briefing(context))
        mcs = _misconceptions(context)
    elif condition == "raw":
        parts.append("# Records from the school\n\n" + json.dumps(context, indent=1, ensure_ascii=False, default=str))
    elif condition == "none":
        p = context.get("pupil") or {}
        parts.append(f"You are tutoring {first_name(p.get('name'))}" + (f", Year {p['year']}." if p.get("year") else "."))
    else:
        parts.append(UNAVAILABLE_NOTE)
    parts.append(WIDGET_RULES.format())
    parts.append(ASSESSMENT_RULES.format(
        misconceptions="; ".join(f"{m['id']} ({m['label']})" for m in mcs) if mcs else "none"))
    messages = [{"role": m["role"], "content": m["content"]} for m in (history or []) if m.get("content")]
    messages.append({"role": "user", "content": message})
    return Prompt(system="\n\n".join(parts), messages=messages, condition=condition,
                  misconception_ids=[m["id"] for m in mcs])
