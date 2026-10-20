"""Enforce agreed adjustments on widgets in code, and audit the reply text against them.

The briefing's support_profile carries only the instruction text ({"do": "..."}), not adjustment IDs, so adjustments
are recognised by a key phrase from the map's fixed vocabulary (seed/adjustments.yaml in the map's source). An
instruction we don't recognise is reported as such, so a wording change on the map side shows up in the turn logs
rather than silently switching enforcement off.

Widgets are changed (trimmed or dropped), never added: code can stop a widget breaking an adjustment, but cannot
supply a missing visual or worked example. The reply text is audited only; the prompt is what shapes it.
"""
import re

KEY_PHRASES = {
    "one-step": "give exactly one step",
    "one-question": "ask at most one question",
    "processing-time": "do not prompt again",
    "repeat-back": "say back what they have just done",
    "short-sentences": "keep every sentence under 15 words",
    "plain-words": "when you use a technical term",
    "minimal-text": "keep the whole reply under 60 words",
    "worked-example-first": "show a complete worked example first",
    "no-hint-before-attempt": "do not give a hint or the first step until the pupil has attempted",
    "smallest-hint": "give the smallest one that lets the pupil continue",
    "name-the-error": "say exactly which step was wrong",
    "concrete-first": "use a concrete example with numbers",
    "visual-support": "every explanation must include a visual",
    "class-method-only": "use only the method the class teacher uses",
    "may-go-beyond": "may be taught topics the class has not reached",
    "stretch-first": "move to a harder or new problem straight away",
    "stay-within": "never mention a topic the class has not been taught",
    "effort-praise": "praise a specific thing the pupil did",
    "no-rhetorical": "every question you ask must be a real question",
    "normalise-errors": "say plainly that this is a common error",
}
VISUAL_TYPES = ("balance", "bar_model", "number_line", "function_machine")


def recognise(support_profile: dict | None) -> tuple[set[str], list[str]]:
    """(recognised adjustment keys, instructions we could not recognise)."""
    keys, unknown = set(), []
    for a in (support_profile or {}).get("adjustments") or []:
        text = " ".join(str(a.get("do", "")).lower().split())
        hit = [k for k, phrase in KEY_PHRASES.items() if phrase in text]
        keys.update(hit)
        if not hit and text:
            unknown.append(a.get("do"))
    return keys, unknown


def enforce_widgets(widgets: list[dict], keys: set[str], *, attempted: bool,
                    class_method: str | None = None) -> tuple[list[dict], list[str]]:
    """Trim or drop widgets that would break an adjustment. Returns (widgets, what was changed and why)."""
    out, changes = [], []
    for w in widgets:
        w, t = dict(w), w["type"]
        if t in ("hints", "steps") and "no-hint-before-attempt" in keys and not attempted:
            changes.append(f"dropped {t}: no hint or first step before the pupil has attempted")
            continue
        if t == "balance" and "no-hint-before-attempt" in keys and not attempted and "result_left" in w:
            w.pop("result_left"), w.pop("result_right")
            changes.append("removed balance result: it shows the first step before an attempt")
        if t == "steps" and ("smallest-hint" in keys or "minimal-text" in keys):
            why = "smallest hint only, never the full method" if "smallest-hint" in keys else "minimal text"
            changes.append(f"dropped steps: {why}")
            continue
        if t == "steps" and "one-step" in keys and len(w["steps"]) > 1:
            w["steps"] = w["steps"][:1]
            changes.append("trimmed steps to one: one step at a time")
        if t == "hints" and ("smallest-hint" in keys or "minimal-text" in keys) and len(w["hints"]) > 1:
            w["hints"] = w["hints"][:1]
            changes.append("trimmed hints to the first, smallest one")
        if t == "confidence" and "one-question" in keys:
            changes.append("dropped confidence check: one question per reply")
            continue
        if t == "quote" and "one-question" in keys and w.get("question"):
            w.pop("question")
            changes.append("removed the quotation card's question: one question per reply")
        if t == "balance" and "class-method-only" in keys and class_method and "balance" not in class_method.lower():
            changes.append("dropped balance: the class does not use the balance method")
            continue
        out.append(w)
    if "minimal-text" in keys and len(out) > 1:
        changes.append(f"kept 1 of {len(out)} widgets: minimal text")
        out = out[:1]
    return out, changes


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def audit_text(reply: str, keys: set[str], widgets: list[dict]) -> list[str]:
    """Flags for the turn log where the reply text appears to break an adjustment. Advisory: nothing is rewritten."""
    flags = []
    words = len(reply.split())
    if "minimal-text" in keys and words > 60:
        flags.append(f"minimal-text: reply is {words} words (limit 60)")
    if "short-sentences" in keys:
        long = [s for s in _sentences(reply) if len(s.split()) >= 15]
        if long:
            flags.append(f"short-sentences: {len(long)} sentence(s) of 15+ words")
    if "one-question" in keys and reply.count("?") > 1:
        flags.append(f"one-question: {reply.count('?')} question marks")
    if "visual-support" in keys and not any(w["type"] in VISUAL_TYPES for w in widgets):
        flags.append("visual-support: no visual widget (check the reply describes one)")
    return flags
