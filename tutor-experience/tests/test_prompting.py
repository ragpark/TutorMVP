"""Prompt construction from real briefings captured from the map."""
import json

import pytest

from app.prompting import FIXED_RULES, build_prompt, render_briefing
from tests.conftest import load


@pytest.fixture
def ben():
    return load("briefing_maths_ben_adjustments.json")


@pytest.fixture
def priya():
    return load("briefing_english_priya.json")


def section_order(system: str) -> list[str]:
    return [line[3:] for line in system.splitlines() if line.startswith("## ")]


# ---------------------------------------------------------------- maths, with agreed adjustments
def test_adjustments_are_required_verbatim_and_first(ben):
    p = build_prompt("maths", "h2", ben, "how do I do 3(x + 2) = 15")
    assert section_order(p.system)[0] == "Agreed adjustments — REQUIRED"
    for a in ben["support_profile"]["adjustments"]:
        assert f"- {a['do']}" in p.system
    assert ben["support_profile"]["rule"] in p.system
    assert "the agreed adjustments win" in p.system


def test_sections_follow_order_of_authority(ben):
    order = section_order(build_prompt("maths", "h2", ben, "hi").system)
    assert order == ["Agreed adjustments — REQUIRED", "Scope", "What the pupil is asking about", "How to teach it",
                     "The pupil"]


def test_scope_flags_untaught_focus(ben):
    s = build_prompt("maths", "h2", ben, "how do I do 3(x + 2) = 15").system
    assert ben["guidance"]["scope_rule"] in s
    assert '"Solve linear equations involving brackets", is NOT yet taught — planned for week 5.' in s
    assert "Not yet taught: Wk5 Expand a single bracket" in s


def test_class_method_and_avoid(ben):
    s = build_prompt("maths", "h2", ben, "x").system
    assert "Method: Balance method — do the same to both sides." in s
    assert "Representation: Function machine diagram." in s
    assert "Avoid: “Change side, change sign” rule" in s
    assert "Check first: Expand a single bracket; Calculate with negative numbers" in s


def test_answer_the_question_first_rule_precedes_briefing(ben):
    s = build_prompt("maths", "h2", ben, "x").system
    rule = s.index("First, respond to what the pupil actually asked")
    assert rule < s.index("# Briefing for this turn")
    assert "Never ignore the question to jump to a weakness." in s


def test_internal_fields_not_rendered(ben):
    s = render_briefing(ben)
    for leak in ("cc:maths", "shared:ks3", "dfe-gcse", "claude:claude", "0.193", "mastery", "(synthetic)",
                 "(fictional)", "approx_tokens", "SENCO", "2026-12-18"):
        assert leak not in s, leak
    assert "First name: Ben" in s
    assert "Class teacher: Ms Okafor." in s


def test_misconception_ids_offered_only_for_assessment(ben):
    p = build_prompt("maths", "h2", ben, "x")
    assert p.misconception_ids == ["mc:maths/alg/partial-expansion", "mc:maths/num/neg-times-neg"]
    assert p.system.count("mc:maths/alg/partial-expansion") == 1
    assert p.system.index("mc:maths/alg/partial-expansion") > p.system.index("<assessment>")


def test_no_adjustments_section_without_support_profile():
    amara = load("briefing_maths_amara.json")
    s = build_prompt("maths", "h2", amara, "x").system
    assert "Agreed adjustments" not in s.split("# Briefing for this turn")[1]
    assert "## Teacher's materials" in s
    assert "Common mistake: why the sign changes (week 4)" in s
    assert "is taught (week 4)." in s
    assert "## Recent patterns" not in s  # how_to_support has no patterns yet: left out


# ---------------------------------------------------------------- english
def test_english_briefing(priya):
    p = build_prompt("english", "h2", priya, "Why does Lady Macbeth call on the spirits to unsex her?")
    s = p.system
    assert "Subject: English: Macbeth." in s
    assert "## Agreed adjustments" not in s
    assert priya["guidance"]["scope_rule"] in s
    assert "Studied so far: Act 1, Act 2, Act 3, Act 4." in s
    assert "Coming up: Act 5 (week 6)." in s
    assert "Method: Drama and hot-seating." in s
    assert "Representation" not in s.split("## How to teach it")[1].split("##")[0]
    assert '- "Come, you spirits / That tend on mortal thoughts, unsex me here" — Lady Macbeth, 1.5' in s
    assert "Diagnosis: Matches this pupil's repeated error pattern: Retells the plot instead of analysing." in s
    assert "Developing: Analyse words and methods for their effect" in s
    assert "Hot-seating Lady Macbeth (week 2)" in s
    assert p.misconception_ids == ["mc:english/retelling"]
    assert p.messages == [{"role": "user", "content": "Why does Lady Macbeth call on the spirits to unsex her?"}]


# ---------------------------------------------------------------- none condition
def test_none_condition_carries_only_name_and_year():
    ctx = load("context_none_amara.json")
    p = build_prompt("maths", "none", ctx, "how do I solve 3x + 5 = x + 13?")
    assert "You are tutoring Amara, Year 10." in p.system
    assert "# Briefing" not in p.system and "## " not in p.system
    assert "Known misconceptions you may name: none" in p.system
    assert p.misconception_ids == []
    # the fixed rules are identical across conditions
    assert p.system.startswith(FIXED_RULES.format(subject_label="Maths: linear equations"))


def test_raw_condition_is_verbatim_json():
    pack = {"mode": "without_h2", "pupil": {"name": "Ben (synthetic)", "class": "10X"},
            "teacher_notes": ["Teacher's note: one step at a time."], "recent_activity": [], "materials": []}
    s = build_prompt("maths", "raw", pack, "x").system
    assert json.dumps(pack, indent=1, ensure_ascii=False) in s
    assert "## Agreed adjustments" not in s


def test_history_precedes_new_message(ben):
    hist = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "Hello Ben."}]
    p = build_prompt("maths", "h2", ben, "3x + 2", hist)
    assert p.messages == hist + [{"role": "user", "content": "3x + 2"}]


def test_unknown_condition_rejected(ben):
    with pytest.raises(ValueError):
        build_prompt("maths", "map", ben, "x")
