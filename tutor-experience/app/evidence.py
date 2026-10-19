"""Write a pupil's answer back to the map after a turn in which they answered a question.

We send activity + score only, never concept IDs: the map treats concept-tagged evidence as a teacher's mark (full
weight), whereas an activity title is tagged by the map's own alignment service at reduced weight. That is the right
weight for a tutor's in-chat judgement. The focus label goes into the activity title so the alignment has something to
go on.
"""
import httpx

from .map_client import MapClient

SOURCE = "tutor-experience"


def should_record(*, from_harness: bool, condition: str, ui_switch: bool, harness_flag: bool) -> bool:
    """On by default in the UI (the pupil can switch it off); off for the harness unless h2 and the flag allows it."""
    if from_harness:
        return condition == "h2" and harness_flag
    return ui_switch


def _clip(s: str, n: int) -> str:
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def build_payload(pupil_id: str, assessment: dict | None, briefing: dict | None,
                  allowed_misconceptions: list[str] | None = None, elapsed_s: float | None = None) -> dict | None:
    """The POST /api/evidence body, or None when there is nothing to record."""
    if not assessment or assessment.get("answered") is not True:
        return None
    answer = str(assessment.get("answer") or "").strip()
    if not answer:
        return None
    score = assessment.get("score")
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        correct = assessment.get("correct")
        score = 1.0 if correct is True else 0.0 if correct is False else None
    if score is None:
        return None  # an answer we could not judge carries no information for the map
    score = max(0.0, min(1.0, float(score)))

    focus = ((briefing or {}).get("focus") or {}).get("label")
    question = _clip(assessment.get("question") or "", 160)
    title = "Tutor chat"
    if focus:
        title += f" — {focus}"
    if question:
        title += f": {question}"
    payload = {"learner": pupil_id, "source": SOURCE, "activity": title, "score": round(score, 3),
               "response": _clip(answer, 400)}

    mc = assessment.get("misconception_id")
    if mc and score < 1.0 and mc in (allowed_misconceptions or []):
        payload["misconception"] = mc

    attempt = {"type": "attempt", "answer": _clip(answer, 200), "correct": score >= 1.0}
    if elapsed_s is not None and elapsed_s >= 0:
        attempt["t"] = int(round(elapsed_s))
    payload["process"] = [attempt]
    return payload


async def record(client: MapClient, payload: dict) -> dict:
    """Send the payload. Returns a small result for the turn log; never raises into the turn."""
    try:
        r = await client.evidence(payload)
        rec = (r or {}).get("recorded") or {}
        return {"ok": True, "evidence_id": rec.get("evidence_id"), "outcome": rec.get("outcome"),
                "concepts": rec.get("concepts"), "concept_provenance": rec.get("concept_provenance")}
    except httpx.HTTPStatusError as e:
        return {"ok": False, "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except httpx.HTTPError as e:
        return {"ok": False, "error": type(e).__name__}
