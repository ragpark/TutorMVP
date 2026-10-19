"""The turn pipeline: briefing → prompt → model → (evidence). Two entry points share prompting and the model call.

UI turns fetch the briefing themselves. Harness turns take the context from the request and never call /api/context,
otherwise the control conditions would be contaminated.
"""
import uuid
from dataclasses import dataclass

from . import evidence, transcripts
from .briefing import fetch_briefing
from .config import Settings
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


async def ui_turn(deps: Deps, *, pupil_id: str, subject: str, message: str, conversation_id: str,
                  record_evidence: bool = True, elapsed_s: float | None = None) -> UITurnResult:
    turn_id = "ui-" + uuid.uuid4().hex[:12]
    hist = transcripts.history(deps.settings, conversation_id)
    br = await fetch_briefing(deps.map, pupil_id, message)
    condition = "h2" if br.ok else "unavailable"
    prompt = build_prompt(subject, condition, br.briefing, message, hist)
    out = await run_model(deps.model, prompt, deps.settings, turn_id,
                          {"route": "ui", "pupil": pupil_id, "subject": subject, "conversation_id": conversation_id,
                           "briefing": br.briefing, "briefing_error": br.error})
    reply = out.reply if br.ok else f"{UNAVAILABLE_PREFIX}\n\n{out.reply}"

    ev = None
    if br.ok and evidence.should_record(from_harness=False, condition=condition, ui_switch=record_evidence,
                                        harness_flag=deps.settings.evidence_from_harness):
        payload = evidence.build_payload(pupil_id, out.assessment, br.briefing, prompt.misconception_ids, elapsed_s)
        if payload:
            ev = {"payload": payload, "result": await evidence.record(deps.map, payload)}
    append_to_log(out.log_path, final_reply=reply, evidence=ev)
    transcripts.append(deps.settings, conversation_id, pupil=pupil_id, turn_id=turn_id, user=message, assistant=reply)
    return UITurnResult(turn_id=turn_id, reply=reply, briefing_ok=br.ok, briefing_error=br.error,
                        focus=((br.briefing or {}).get("focus") or {}).get("label"), evidence=ev)


async def harness_turn(deps: Deps, *, turn_id: str, subject: str, arm: str, pupil: str, message: str,
                       context: dict) -> str:
    """One blind evaluation turn. Context comes from the harness; the map is touched only for an allowed write-back."""
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
