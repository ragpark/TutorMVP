"""Widgets: validated server-side, rendered by the UI, never returned to the harness."""
import json

from app import widgets as W
from app.evidence import build_payload, client_process
from app.lesson import lesson_view
from app.model import split_reply
from app.prompting import WIDGET_RULES, build_prompt
from tests.conftest import FakeMap, FakeModel, client_for, load

BALANCE = {"type": "balance", "left": "3x + 5", "right": "x + 13", "operation": "subtract x from both sides",
           "result_left": "2x + 5", "result_right": "13"}
REPLY = ("Take x from both sides. What is left on the left?\n"
         f"<widgets>{json.dumps([BALANCE, {'type': 'answer', 'prompt': 'Left side ='}])}</widgets>\n"
         '<assessment>{"answered": false}</assessment>')


# ---------------------------------------------------------------- validation
def test_known_widgets_pass_through():
    assert W.clean([BALANCE]) == [BALANCE]


def test_unknown_types_fields_and_excess_dropped():
    raw = [{"type": "video", "url": "http://x"}, {"type": "hints", "hints": ["a", "b"], "onclick": "evil()"},
           {"type": "confidence"}, {"type": "steps", "steps": ["1"]}, {"type": "answer", "prompt": "x ="}]
    out = W.clean(raw)
    assert [w["type"] for w in out] == ["hints", "confidence", "steps"]  # at most three
    assert out[0] == {"type": "hints", "hints": ["a", "b"]}


def test_malformed_widgets_rejected():
    assert W.clean("nope") == []
    assert W.clean([{"type": "balance", "left": "x"}]) == []                      # needs both sides
    assert W.clean([{"type": "number_line", "min": 0, "max": 500}]) == []          # range too wide to draw
    assert W.clean([{"type": "bar_model", "rows": [{"segments": [{"size": 1}]}]}]) == []  # segment needs a label
    assert W.clean([{"type": "balance", "left": "x", "right": "y", "result_left": "z"}]) == [
        {"type": "balance", "left": "x", "right": "y"}]                            # half a result is no result


def test_strings_are_clipped_and_quote_focus_words_must_appear():
    out = W.clean([{"type": "quote", "text": "Come, you spirits / That tend on mortal thoughts, unsex me here",
                    "focus_words": ["unsex", "dagger"], "act": "1.5"},
                   {"type": "steps", "steps": ["x" * 500]}])
    assert out[0]["focus_words"] == ["unsex"]
    assert len(out[1]["steps"][0]) == 200


# ---------------------------------------------------------------- splitting the model's output
def test_split_reply_separates_widgets_and_assessment():
    reply, assessment, widgets = split_reply(REPLY)
    assert reply == "Take x from both sides. What is left on the left?"
    assert assessment == {"answered": False}
    assert [w["type"] for w in widgets] == ["balance", "answer"]


def test_malformed_widgets_block_never_shown():
    reply, _, widgets = split_reply("Try again.\n<widgets>[{not json}]</widgets>")
    assert reply == "Try again." and widgets == []
    reply, _, _ = split_reply("Try again.\n<widgets>[{\"type\": \"hints\"")  # unclosed
    assert reply == "Try again."


# ---------------------------------------------------------------- one tutor across conditions
def test_widget_rules_identical_in_every_condition():
    amara = load("briefing_maths_amara.json")
    for cond, ctx in (("h2", amara), ("raw", {"pupil": {}}), ("none", load("context_none_amara.json")),
                      ("unavailable", None)):
        assert WIDGET_RULES.format() in build_prompt("maths", cond, ctx, "x").system
    assert "must make complete sense without them" in WIDGET_RULES
    assert "agreed adjustments, the scope rule and the class's method apply to them too" in WIDGET_RULES


def test_harness_reply_never_contains_widgets(settings):
    r = client_for(settings, FakeMap(), FakeModel(REPLY)).post("/webhook/tutor", json={
        "turn_id": "t1", "subject": "maths", "arm": "h2", "pupil": "pupil:amara", "message": "x",
        "context": load("briefing_maths_amara.json")})
    assert r.json() == {"reply": "Take x from both sides. What is left on the left?"}


# ---------------------------------------------------------------- UI turn
def test_ui_turn_returns_widgets_lesson_and_briefing(settings):
    amara = load("briefing_maths_amara.json")
    data = client_for(settings, FakeMap(amara), FakeModel(REPLY)).post("/api/turn", json={
        "pupil": "pupil:amara", "subject": "maths", "message": "I'm stuck", "conversation_id": "conv-widgets-1"}).json()
    assert [w["type"] for w in data["widgets"]] == ["balance", "answer"]
    assert data["lesson"]["topic"] == "Solve linear equations with the unknown on both sides"
    assert data["briefing"] == amara


def test_lesson_view_shows_class_facts_not_pupil_labels():
    v = lesson_view(load("briefing_maths_ben_adjustments.json"))
    assert v["topic_taught"] is False and v["topic_week"] == 5
    assert v["method"] == "Balance method — do the same to both sides"
    assert v["next"] is None  # the next step is the previewed focus itself, so nothing new to show
    assert {"week": 5, "label": "Solve linear equations involving brackets", "status": "coming", "focus": True} in v["scheme"]
    flat = json.dumps(v)
    for leak in ("gap", "secure", "mastery", "misconception", "adjust"):
        assert leak not in flat
    assert lesson_view(None) is None


# ---------------------------------------------------------------- process events from the UI
def test_client_events_validated():
    assert client_process([{"type": "hint_requested", "t": 12.4}, {"type": "confidence", "t": 20, "rating": 3},
                           {"type": "confidence", "rating": 9}, {"type": "affect", "t": 1}, {"type": "attempt"},
                           {"type": "hint_requested", "t": -5}, "junk"]) == [
        {"type": "hint_requested", "t": 12}, {"type": "confidence", "t": 20, "rating": 3},
        {"type": "hint_requested", "t": 0}]


def test_client_events_join_the_attempt_in_time_order():
    a = {"answered": True, "question": "q", "answer": "x = 4", "correct": True, "score": 1}
    p = build_payload("pupil:amara", a, load("briefing_maths_amara.json"), elapsed_s=30,
                      events=[{"type": "confidence", "t": 25, "rating": 2}, {"type": "hint_requested", "t": 8}])
    assert [e["type"] for e in p["process"]] == ["hint_requested", "confidence", "attempt"]


def test_ui_events_reach_the_map(settings):
    amara = load("briefing_maths_amara.json")
    fm = FakeMap(amara)
    answered = 'Right.\n<assessment>{"answered": true, "question": "q", "answer": "x = 3", "correct": true, "score": 1}</assessment>'
    client_for(settings, fm, FakeModel(answered)).post("/api/turn", json={
        "pupil": "pupil:amara", "subject": "maths", "message": "x = 3", "conversation_id": "conv-widgets-2",
        "elapsed_s": 40, "events": [{"type": "hint_requested", "t": 10}]})
    sent = fm.requests[-1][2]
    assert sent["process"] == [{"type": "hint_requested", "t": 10},
                               {"type": "attempt", "answer": "x = 3", "correct": True, "t": 40}]
