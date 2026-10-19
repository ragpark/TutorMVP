"""The harness contract: POST {turn_id, subject, arm, pupil, message, context} → {"reply": "..."} within 60 s."""
import json
import time

import pytest

from tests.conftest import FakeMap, FakeModel, client_for, load, with_

ANSWERED = ('Not quite: 3(x + 2) is 3x + 6, not 3x + 2. What is 3 × 2?\n'
            '<assessment>{"answered": true, "question": "Expand 3(x + 2)", "answer": "3x + 2", "correct": false, '
            '"score": 0, "misconception_id": "mc:maths/alg/partial-expansion"}</assessment>')


def body(arm="h2", context=None, **kw):
    if context is None:
        context = load("briefing_maths_ben_adjustments.json") if arm == "h2" else load("context_none_amara.json")
    return {"turn_id": "sc1:" + arm, "subject": "maths", "arm": arm, "pupil": "pupil:ben",
            "message": "3(x + 2) = 3x + 2?", "context": context, **kw}


@pytest.mark.parametrize("arm", ["none", "raw", "h2"])
def test_reply_shape_and_no_map_calls(settings, arm):
    fm, model = FakeMap(), FakeModel(ANSWERED)
    ctx = {"mode": "without_h2", "pupil": {"name": "Ben (synthetic)", "class": "10X"}} if arm == "raw" else None
    r = client_for(settings, fm, model).post("/webhook/tutor", json=body(arm, ctx))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    data = r.json()
    assert list(data) == ["reply"]
    assert data["reply"].startswith("Not quite")
    assert "<assessment>" not in data["reply"]
    assert fm.requests == []  # the harness supplies the context: never call /api/context, never write evidence
    assert model.prompts[0].condition == arm


def test_harness_context_is_what_the_model_sees(settings):
    model = FakeModel()
    client_for(settings, FakeMap(), model).post("/webhook/tutor", json=body("h2"))
    s = model.prompts[0].system
    assert "## Agreed adjustments — REQUIRED" in s
    assert model.prompts[0].messages == [{"role": "user", "content": "3(x + 2) = 3x + 2?"}]


def test_none_arm_prompt_has_no_briefing(settings):
    model = FakeModel()
    client_for(settings, FakeMap(), model).post("/webhook/tutor", json=body("none"))
    assert "# Briefing" not in model.prompts[0].system


def test_turn_is_logged(settings):
    client_for(settings, FakeMap(), FakeModel(ANSWERED)).post("/webhook/tutor", json=body("h2"))
    logs = list((settings.data_dir / "turns").glob("*/*.json"))
    assert len(logs) == 1
    rec = json.loads(logs[0].read_text())
    assert rec["route"] == "webhook" and rec["condition"] == "h2" and rec["turn_id"] == "harness-sc1:h2"
    assert rec["prompt"]["system"] and rec["response"]["text"] == ANSWERED
    assert rec["assessment"]["answer"] == "3x + 2" and rec["evidence"] is None


# ---------------------------------------------------------------- secret
def test_secret_required_when_configured(settings):
    s = with_(settings, tutor_secret="s3cret")
    c = client_for(s, FakeMap(), FakeModel())
    assert c.post("/webhook/tutor", json=body()).status_code == 401
    assert c.post("/webhook/tutor", json=body(), headers={"X-Tutor-Secret": "wrong"}).status_code == 401
    assert c.post("/webhook/tutor", json=body(), headers={"X-Tutor-Secret": "s3cret"}).status_code == 200


def test_no_secret_configured_accepts_unsigned(settings):
    assert client_for(settings, FakeMap(), FakeModel()).post("/webhook/tutor", json=body()).status_code == 200


# ---------------------------------------------------------------- validation
@pytest.mark.parametrize("bad", [{"arm": "map"}, {"subject": "history"}, {"message": ""}])
def test_rejects_malformed_requests(settings, bad):
    r = client_for(settings, FakeMap(), FakeModel()).post("/webhook/tutor", json=body() | bad)
    assert r.status_code == 422


# ---------------------------------------------------------------- 60 s budget
def test_default_budget_is_inside_harness_timeout(settings):
    assert settings.webhook_budget_s < 60


def test_slow_turn_fails_fast_instead_of_hanging(settings):
    s = with_(settings, webhook_budget_s=0.2)
    t0 = time.monotonic()
    r = client_for(s, FakeMap(), FakeModel(delay=5)).post("/webhook/tutor", json=body())
    assert time.monotonic() - t0 < 2
    assert r.status_code == 504  # non-2xx: the harness records an error rather than scoring a made-up reply
    assert "reply" not in r.json()


# ---------------------------------------------------------------- evidence switch for harness turns
def test_h2_evidence_only_with_flag(settings):
    fm = FakeMap()
    client_for(with_(settings, evidence_from_harness=True), fm, FakeModel(ANSWERED)).post("/webhook/tutor", json=body("h2"))
    assert fm.paths() == ["/api/evidence"]
    assert fm.requests[0][2]["source"] == "tutor-experience"


@pytest.mark.parametrize("arm", ["none", "raw"])
def test_control_conditions_never_write_evidence(settings, arm):
    fm = FakeMap()
    ctx = {"pupil": {"name": "Ben (synthetic)", "class": "10X"}} if arm == "raw" else None
    client_for(with_(settings, evidence_from_harness=True), fm, FakeModel(ANSWERED)).post(
        "/webhook/tutor", json=body(arm, ctx))
    assert fm.requests == []
