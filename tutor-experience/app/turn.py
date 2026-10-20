"""The turn pipeline: briefing → prompt → model → (evidence). Two entry points share prompting and the model call.

UI turns fetch the briefing themselves. Harness turns take the context from the request and never call /api/context,
otherwise the control conditions would be contaminated.
"""
import uuid
from dataclasses import dataclass

from . import adjustments, evidence, session, transcripts
from .briefing import fetch_briefing
from .config import Settings
from .lesson import lesson_view
from .map_client import MapClient
from .model import ModelCaller, append_to_log, run_model
from .prompting import build_prompt

UNAVAILABLE_PREFIX = ("I can't reach your class's curriculum map at the moment, so I don't know what your class has "
                      "covered. I'll help in general terms for now.")


@dataclass
class Deps:
    settings: Settings
    map: MapClient
    model: ModelCaller


@dataclass
class UITurnResult:
    turn_id: str
    reply: str
    briefing_ok: bool
    briefing_error: str | None
    focus: str | None
    evidence: dict | None
    widgets: list[dict]
    lesson: dict | None
    briefing: dict | None
    session: dict | None = None
    adjustments: dict | None = None


def _enforce(widgets: list[dict], briefing: dict | None, assessment: dict | None) -> tuple[list[dict], dict]:
    """Apply agreed adjustments to the model's widgets. Without a briefing we can't know the pupil's adjustments, so
    only the answer box survives."""
    if briefing is None:
        kept = [w for w in widgets if w["type"] == "answer"]
        dropped = [f"dropped {w['type']}: no briefing, so agreed adjustments are unknown" for w in widgets if w not in kept]
        return kept, {"applied": [], "unrecognised": [], "widget_changes": dropped}
    keys, unknown = adjustments.recognise(briefing.get("support_profile"))
    method = (((briefing.get("guidance") or {}).get("teach_with") or {}).get("method") or {}).get("label")
    attempted = (assessment or {}).get("answered") is True
    kept, changes = adjustments.enforce_widgets(widgets, keys, attempted=attempted, class_method=method)
    return kept, {"applied": sorted(keys), "unrecognised": unknown, "widget_changes": changes}


async def ui_turn(deps: Deps, *, pupil_id: str, subject: str, message: str, conversation_id: str,
                  record_evidence: bool = True, elapsed_s: float | None = None,
                  events: list[dict] | None = None, finish: bool = False) -> UITurnResult:
    turn_id = "ui-" + uuid.uuid4().hex[:12]
    hist = transcripts.history(deps.settings, conversation_id)
    br = await fetch_briefing(deps.map, pupil_id, message)
    condition = "h2" if br.ok else "unavailable"
    sess = session.load(deps.settings, conversation_id)
    if sess is None and br.ok:
        sess = session.plan(br.briefing)
    block = session.render(sess, finishing=finish) if sess else None
    prompt = build_prompt(subject, condition, br.briefing, message, hist, session_block=block)
    out = await run_model(deps.model, prompt, deps.settings, turn_id,
                          {"route": "ui", "pupil": pupil_id, "subject": subject, "conversation_id": conversation_id,
                           "briefing": br.briefing, "briefing_error": br.error,
                           "session_before": sess.view() if sess else None})
    reply = out.reply if br.ok else f"{UNAVAILABLE_PREFIX}\n\n{out.reply}"
    widgets, adj = _enforce(out.widgets, br.briefing, out.assessment)
    keys = set(adj["applied"])
    adj["text_flags"] = adjustments.audit_text(out.reply, keys, widgets) if keys else []

    ev = None
    if br.ok and evidence.should_record(from_harness=False, condition=condition, ui_switch=record_evidence,
                                        harness_flag=deps.settings.evidence_from_harness):
        topic = session.answer_topic(sess, br.briefing) if sess else None
        payload = evidence.build_payload(pupil_id, out.assessment, br.briefing, prompt.misconception_ids, elapsed_s,
                                         events, topic=topic)
        if payload:
            ev = {"payload": payload, "result": await evidence.record(deps.map, payload)}
    if sess:
        session.update(sess, out.assessment, br.briefing, finishing=finish)
        session.save(deps.settings, conversation_id, sess)
    append_to_log(out.log_path, final_reply=reply, evidence=ev, client_events=events or [], widgets_shown=widgets,
                  adjustments=adj, session_after=sess.view() if sess else None)
    transcripts.append(deps.settings, conversation_id, pupil=pupil_id, turn_id=turn_id, user=message, assistant=reply)
    return UITurnResult(turn_id=turn_id, reply=reply, briefing_ok=br.ok, briefing_error=br.error,
                        focus=((br.briefing or {}).get("focus") or {}).get("label"), evidence=ev,
                        widgets=widgets, lesson=lesson_view(br.briefing), briefing=br.briefing,
                        session=sess.view() if sess else None, adjustments=adj)


async def harness_turn(deps: Deps, *, turn_id: str, subject: str, arm: str, pupil: str, message: str,
                       context: dict) -> str:
    """One blind evaluation turn. Context comes from the harness; the map is touched only for an allowed write-back.
    Only the text reply is returned: widgets are a UI affordance and are never part of what the harness scores."""
    prompt = build_prompt(subject, arm, context, message)
    out = await run_model(deps.model, prompt, deps.settings, f"harness-{turn_id}",
                          {"route": "webhook", "pupil": pupil, "subject": subject, "context": context})
    ev = None
    if evidence.should_record(from_harness=True, condition=arm, ui_switch=False,
                              harness_flag=deps.settings.evidence_from_harness):
        payload = evidence.build_payload(pupil, out.assessment, context, prompt.misconception_ids)
        if payload:
            ev = {"payload": payload, "result": await evidence.record(deps.map, payload)}
    append_to_log(out.log_path, final_reply=out.reply, evidence=ev)
    return out.reply
