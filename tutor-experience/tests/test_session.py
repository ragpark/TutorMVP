"""The session shape: goal, warm-up recall, practice, wrap-up. UI conversations only."""
import json

from app import session as S
from app.prompting import build_prompt
from tests.conftest import FakeMap, FakeModel, client_for, load


def amara():
    return load("briefing_maths_amara.json")


# ---------------------------------------------------------------- planning
def test_plan_from_amaras_briefing():
    s = S.plan(amara())
    assert s.goal == "Solve linear equations with the unknown on both sides" and not s.goal_is_preview
    assert s.recall_topic == "Solve one- and two-step linear equations"  # her strongest secure prerequisite
    assert s.next_topic == "Solve linear equations involving brackets"
    assert s.phase == "goal"


def test_plan_for_an_untaught_focus_is_a_preview_and_recalls_something_taught():
    s = S.plan(load("briefing_maths_ben_adjustments.json"))
    assert s.goal_is_preview
    assert s.recall_topic == "Solve linear equations with the unknown on both sides"  # not "Expand a single bracket"
    assert "clearly flagged first look" in S.render(s)


def test_recall_for_english_comes_from_taught_secure_topics():
    assert S.plan(load("briefing_english_priya.json")).recall_topic == "James I and the Divine Right of Kings"


def test_recall_never_the_focus_or_untaught():
    b = amara()
    b["learner"]["prerequisites"] = []
    b["learner"]["overview"] = []
    b["class"]["taught_so_far"] = ["Wk4 Solve linear equations with the unknown on both sides"]
    assert S.pick_recall(b) is None
    assert S.plan(b).view()["phase"] == "goal"


# ---------------------------------------------------------------- phases
def answered(score, **kw):
    return {"answered": True, "question": "q", "answer": "a", "correct": score >= 1, "score": score, **kw}


def test_phase_progression_and_recall_tracking():
    b = amara()
    s = S.plan(b)
    S.update(s, {"answered": False}, b, finishing=False)
    assert s.phase == "warm_up"
    S.update(s, {"answered": False, "recall_asked": True}, b, finishing=False)   # tutor asks the warm-up
    assert s.phase == "practice" and s.recall_pending
    assert S.answer_topic(s, b) == "Solve one- and two-step linear equations"
    S.update(s, answered(1), b, finishing=False)                                   # pupil answers it
    assert s.recall_result == "right" and not s.recall_pending
    S.update(s, answered(0), b, finishing=False)
    assert (s.answers, s.correct) == (2, 1)
    assert s.log[-1] == {"topic": "Solve linear equations with the unknown on both sides", "result": "not yet"}
    S.update(s, {"answered": False}, b, finishing=True)
    assert s.finished and s.phase == "wrap_up"


def test_warm_up_given_up_after_window():
    b = amara()
    s = S.plan(b)
    for _ in range(S.WARM_UP_WINDOW):
        S.update(s, {"answered": False}, b, finishing=False)
    assert s.phase == "practice" and not s.recall_asked


def test_wrap_up_offered_after_enough_answers():
    b = amara()
    s = S.plan(b)
    s.turns, s.answers, s.recall_asked = 7, S.OFFER_WRAP_UP_AFTER, True
    assert "offer to wrap up" in S.render(s)


def test_wrap_up_block_uses_the_session_record():
    b = amara()
    s = S.plan(b)
    s.turns, s.recall_asked = 5, True
    S.update(s, answered(1), b, finishing=False)
    block = S.render(s, finishing=True)
    assert "Stage: wrap-up" in block and "Ask no new question" in block
    assert "1 answer(s), 1 right" in block and "Solve linear equations involving brackets" in block


def test_session_block_ranks_below_adjustments_and_the_pupil():
    block = S.render(S.plan(amara()))
    assert "ranks below agreed adjustments, the scope rule and what the pupil has just asked" in block
    assert "Answer what the pupil asked first" in block


# ---------------------------------------------------------------- through the app
def turn(c, cid, **kw):
    return c.post("/api/turn", json={"pupil": "pupil:amara", "subject": "maths", "message": "hi",
                                     "conversation_id": cid} | kw).json()


def test_ui_turns_carry_the_session_block_and_harness_turns_do_not(settings):
    model = FakeModel()
    c = client_for(settings, FakeMap(amara()), model)
    data = turn(c, "conv-session-1")
    assert "# This session" in model.prompts[0].system and "Stage: start" in model.prompts[0].system
    assert data["session"]["phase"] == "warm_up" and data["session"]["goal"].startswith("Solve linear")
    turn(c, "conv-session-1")
    assert "Stage: warm-up" in model.prompts[1].system
    c.post("/webhook/tutor", json={"turn_id": "t", "subject": "maths", "arm": "h2", "pupil": "pupil:amara",
                                   "message": "hi", "context": amara()})
    assert "# This session" not in model.prompts[2].system
    assert model.prompts[2].system == build_prompt("maths", "h2", amara(), "hi").system


def test_finish_produces_a_wrap_up(settings):
    model = FakeModel()
    c = client_for(settings, FakeMap(amara()), model)
    turn(c, "conv-session-2")
    data = turn(c, "conv-session-2", message="I'd like to finish for today.", finish=True)
    assert "Stage: wrap-up" in model.prompts[1].system
    assert data["session"]["finished"] and data["session"]["phase"] == "wrap_up"
    assert json.loads((settings.data_dir / "sessions" / "conv-session-2.json").read_text())["finished"]


def test_warm_up_answer_is_recorded_against_the_warm_up_topic(settings):
    fm = FakeMap(amara())
    ask = 'Quick warm-up: solve 2x + 3 = 11.\n<assessment>{"answered": false, "recall_asked": true}</assessment>'
    reply = ('Yes, x = 4.\n<assessment>{"answered": true, "question": "Solve 2x + 3 = 11", "answer": "x = 4", '
             '"correct": true, "score": 1, "misconception_id": "mc:maths/alg/sign-transfer"}</assessment>')
    model = FakeModel(ask)
    c = client_for(settings, fm, model)
    turn(c, "conv-session-3")
    model.text = reply
    data = turn(c, "conv-session-3", message="x = 4")
    sent = fm.requests[-1][2]
    assert sent["activity"].startswith("Tutor chat — Solve one- and two-step linear equations")
    assert "misconception" not in sent
    assert data["session"]["recall_result"] == "right"


def test_no_session_until_there_is_a_briefing(settings):
    model = FakeModel()
    data = turn(client_for(settings, FakeMap(down=True), model), "conv-session-4")
    assert data["session"] is None and "# This session" not in model.prompts[0].system
