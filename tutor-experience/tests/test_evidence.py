"""The evidence write-back payload, and when it is sent."""
import pytest

from app.evidence import SOURCE, build_payload, should_record
from tests.conftest import FakeMap, FakeModel, client_for, load

WRONG = {"answered": True, "question": "Solve 5x + 3 = 2x + 12", "answer": "7x = 15", "correct": False, "score": 0,
         "misconception_id": "mc:maths/alg/sign-transfer"}
AMARA_MCS = ["mc:maths/alg/sign-transfer"]


@pytest.fixture
def amara():
    return load("briefing_maths_amara.json")


def test_payload_for_a_wrong_answer(amara):
    p = build_payload("pupil:amara", WRONG, amara, AMARA_MCS, elapsed_s=41.6)
    assert p == {
        "learner": "pupil:amara",
        "source": SOURCE,
        "activity": "Tutor chat — Solve linear equations with the unknown on both sides: Solve 5x + 3 = 2x + 12",
        "score": 0.0,
        "response": "7x = 15",
        "misconception": "mc:maths/alg/sign-transfer",
        "process": [{"type": "attempt", "answer": "7x = 15", "correct": False, "t": 42}],
    }
    assert SOURCE == "tutor-experience"


def test_never_sends_concept_ids(amara):
    p = build_payload("pupil:amara", WRONG, amara, AMARA_MCS)
    assert "concepts" not in p and "item" not in p


def test_correct_answer(amara):
    a = WRONG | {"answer": "x = 3", "correct": True, "score": 1, "misconception_id": "mc:maths/alg/sign-transfer"}
    p = build_payload("pupil:amara", a, amara, AMARA_MCS)
    assert p["score"] == 1.0
    assert "misconception" not in p  # a right answer shows no misconception
    assert p["process"] == [{"type": "attempt", "answer": "x = 3", "correct": True}]  # no timing known: no t


def test_score_falls_back_to_correct_and_is_clamped(amara):
    assert build_payload("pupil:amara", WRONG | {"score": None}, amara)["score"] == 0.0
    assert build_payload("pupil:amara", WRONG | {"score": None, "correct": True}, amara)["score"] == 1.0
    assert build_payload("pupil:amara", WRONG | {"score": 7}, amara)["score"] == 1.0


def test_unknown_misconception_dropped(amara):
    p = build_payload("pupil:amara", WRONG | {"misconception_id": "mc:made/up"}, amara, AMARA_MCS)
    assert "misconception" not in p


@pytest.mark.parametrize("a", [None, {}, {"answered": False, "answer": "x"}, WRONG | {"answer": ""},
                               WRONG | {"score": None, "correct": None}, WRONG | {"answered": "yes"}])
def test_nothing_to_record(amara, a):
    assert build_payload("pupil:amara", a, amara, AMARA_MCS) is None


def test_switch():
    assert should_record(from_harness=False, condition="h2", ui_switch=True, harness_flag=False)
    assert not should_record(from_harness=False, condition="h2", ui_switch=False, harness_flag=True)
    assert not should_record(from_harness=True, condition="h2", ui_switch=True, harness_flag=False)
    assert should_record(from_harness=True, condition="h2", ui_switch=False, harness_flag=True)
    assert not should_record(from_harness=True, condition="raw", ui_switch=True, harness_flag=True)
    assert not should_record(from_harness=True, condition="none", ui_switch=True, harness_flag=True)


# ---------------------------------------------------------------- UI turns end to end (map and model mocked)
REPLY = ("That's a common slip: subtract 2x from both sides instead. What is 5x − 2x?\n<assessment>"
         '{"answered": true, "question": "Solve 5x + 3 = 2x + 12", "answer": "7x = 15", "correct": false, "score": 0, '
         '"misconception_id": "mc:maths/alg/sign-transfer"}</assessment>')


def turn(c, **kw):
    return c.post("/api/turn", json={"pupil": "pupil:amara", "subject": "maths", "message": "is it 7x = 15?",
                                     "conversation_id": "conv-test-0001", "elapsed_s": 30} | kw)


def test_ui_turn_fetches_briefing_then_records_answer(settings, amara):
    fm = FakeMap(amara)
    r = turn(client_for(settings, fm, FakeModel(REPLY)))
    assert r.status_code == 200
    assert fm.paths() == ["/api/context", "/api/evidence"]
    assert fm.requests[0][2] == {"learner": "pupil:amara", "message": "is it 7x = 15?", "concept": None}
    sent = fm.requests[1][2]
    assert sent["source"] == "tutor-experience" and sent["score"] == 0.0 and "concepts" not in sent
    assert sent["process"][0]["t"] == 30
    data = r.json()
    assert data["briefing_ok"] and data["evidence"]["ok"] and "<assessment>" not in data["reply"]


def test_ui_switch_off_sends_no_evidence(settings, amara):
    fm = FakeMap(amara)
    turn(client_for(settings, fm, FakeModel(REPLY)), record_evidence=False)
    assert fm.paths() == ["/api/context"]


def test_ui_turn_keeps_history(settings, amara):
    model = FakeModel(REPLY)
    c = client_for(settings, FakeMap(amara), model)
    turn(c)
    turn(c, message="5x − 2x = 3x")
    assert [m["role"] for m in model.prompts[1].messages] == ["user", "assistant", "user"]
    assert "<assessment>" not in model.prompts[1].messages[1]["content"]


def test_map_unreachable_says_so_and_invents_nothing(settings):
    fm, model = FakeMap(down=True), FakeModel(REPLY)
    data = turn(client_for(settings, fm, model)).json()
    assert data["briefing_ok"] is False and data["evidence"] is None
    assert data["reply"].startswith("I can't reach your class's curriculum map")
    assert model.prompts[0].condition == "unavailable"
    assert "# Briefing" not in model.prompts[0].system
    assert fm.paths() == ["/api/context"]  # no evidence write when there is no briefing
