"""Agreed adjustments enforced on widgets in code, and the reply text audited against them."""
import json

import pytest

from app.adjustments import KEY_PHRASES, audit_text, enforce_widgets, recognise
from tests.conftest import FakeMap, FakeModel, client_for, load

STEPS = {"type": "steps", "title": "Worked example", "steps": ["one", "two", "three"]}
HINTS = {"type": "hints", "hints": ["small", "bigger"]}
BALANCE = {"type": "balance", "left": "3x + 5", "right": "x + 13", "result_left": "2x + 5", "result_right": "13"}
ANSWER = {"type": "answer", "prompt": "x ="}
CONF = {"type": "confidence", "prompt": "How sure are you?"}
QUOTE = {"type": "quote", "text": "Fair is foul", "question": "What does it suggest?"}


def profile(*keys):
    return {"status": "REQUIRED", "adjustments": [{"do": KEY_PHRASES[k].capitalize() + "."} for k in keys]}


def test_recognises_bens_adjustments_from_the_real_briefing():
    keys, unknown = recognise(load("briefing_maths_ben_adjustments.json")["support_profile"])
    assert keys == {"one-step", "short-sentences", "no-hint-before-attempt", "name-the-error", "concrete-first",
                    "effort-praise"}
    assert unknown == []


def test_unrecognised_wording_is_reported_not_ignored():
    keys, unknown = recognise({"adjustments": [{"do": "Use green pen only."}]})
    assert keys == set() and unknown == ["Use green pen only."]
    assert recognise(None) == (set(), [])


def test_no_adjustments_no_changes():
    ws = [STEPS, HINTS, BALANCE]
    assert enforce_widgets(ws, set(), attempted=False) == (ws, [])


def test_no_hint_before_attempt():
    out, changes = enforce_widgets([STEPS, HINTS, BALANCE, ANSWER], {"no-hint-before-attempt"}, attempted=False)
    assert [w["type"] for w in out] == ["balance", "answer"]
    assert "result_left" not in out[0]  # the result would show the first step
    assert len(changes) == 3
    out, changes = enforce_widgets([STEPS, HINTS, BALANCE], {"no-hint-before-attempt"}, attempted=True)
    assert out == [STEPS, HINTS, BALANCE] and changes == []


def test_one_step_trims_worked_example():
    out, changes = enforce_widgets([STEPS], {"one-step"}, attempted=True)
    assert out[0]["steps"] == ["one"] and changes == ["trimmed steps to one: one step at a time"]
    assert STEPS["steps"] == ["one", "two", "three"]  # the input is not mutated


def test_smallest_hint():
    out, _ = enforce_widgets([STEPS, HINTS], {"smallest-hint"}, attempted=True)
    assert out == [{"type": "hints", "hints": ["small"]}]


def test_one_question():
    out, _ = enforce_widgets([ANSWER, CONF, QUOTE], {"one-question"}, attempted=True)
    assert [w["type"] for w in out] == ["answer", "quote"] and "question" not in out[1]


def test_minimal_text_keeps_one_widget():
    out, changes = enforce_widgets([ANSWER, HINTS, BALANCE], {"minimal-text"}, attempted=True)
    assert out == [ANSWER] and changes[-1] == "kept 1 of 3 widgets: minimal text"


def test_class_method_only():
    out, _ = enforce_widgets([BALANCE], {"class-method-only"}, attempted=True, class_method="Function machine")
    assert out == []
    out, _ = enforce_widgets([BALANCE], {"class-method-only"}, attempted=True,
                             class_method="Balance method — do the same to both sides")
    assert out == [BALANCE]


def test_text_audit():
    long = "This sentence is deliberately written to be far longer than fifteen words so that it is flagged."
    assert audit_text(long + " Is it? Or is it?", {"short-sentences", "one-question", "visual-support"}, []) == [
        "short-sentences: 1 sentence(s) of 15+ words", "one-question: 2 question marks",
        "visual-support: no visual widget (check the reply describes one)"]
    assert audit_text("word " * 61, {"minimal-text"}, []) == ["minimal-text: reply is 61 words (limit 60)"]
    assert audit_text(long, set(), []) == []


# ---------------------------------------------------------------- through a UI turn, with Ben's real briefing
BEN_REPLY = ("Brackets come in week 5, so this is a quick preview. Have a go first. What do you think 3(x + 2) is?\n"
             "<widgets>" + json.dumps([STEPS, HINTS, ANSWER]) + "</widgets>\n"
             '<assessment>{"answered": false}</assessment>')


def test_ui_turn_enforces_bens_adjustments(settings):
    ben = load("briefing_maths_ben_adjustments.json")
    data = client_for(settings, FakeMap(ben), FakeModel(BEN_REPLY)).post("/api/turn", json={
        "pupil": "pupil:ben", "subject": "maths", "message": "how do I do 3(x + 2) = 15",
        "conversation_id": "conv-ben-0001"}).json()
    assert [w["type"] for w in data["widgets"]] == ["answer"]
    assert "no-hint-before-attempt" in data["adjustments"]["applied"]
    assert len(data["adjustments"]["widget_changes"]) == 2
    log = json.loads(next((settings.data_dir / "turns").glob("*/*.json")).read_text())
    assert [w["type"] for w in log["widgets"]] == ["steps", "hints", "answer"]  # what the model asked for
    assert [w["type"] for w in log["widgets_shown"]] == ["answer"]              # what the pupil saw


@pytest.mark.parametrize("arm", ["h2", "none"])
def test_harness_unaffected(settings, arm):
    ctx = load("briefing_maths_ben_adjustments.json") if arm == "h2" else load("context_none_amara.json")
    r = client_for(settings, FakeMap(), FakeModel(BEN_REPLY)).post("/webhook/tutor", json={
        "turn_id": "t", "subject": "maths", "arm": arm, "pupil": "pupil:ben", "message": "x", "context": ctx})
    assert r.json() == {"reply": BEN_REPLY.split("\n<widgets>")[0]}


def test_no_briefing_keeps_only_the_answer_box(settings):
    reply = "Have a go.\n<widgets>" + json.dumps([HINTS, ANSWER]) + "</widgets>"
    data = client_for(settings, FakeMap(down=True), FakeModel(reply)).post("/api/turn", json={
        "pupil": "pupil:ben", "subject": "maths", "message": "help", "conversation_id": "conv-ben-0002"}).json()
    assert [w["type"] for w in data["widgets"]] == ["answer"]
