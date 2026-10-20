"""A shape for a UI tutoring session: agree a goal, a short warm-up recall question on an earlier topic, practice
towards the goal, and a one-line wrap-up when the pupil finishes.

The plan is conversation state (kept next to the transcript), built from the first briefing; the map still owns
everything about the pupil. Harness turns have no conversation, so they never get a session block and their prompt is
unchanged. The session block ranks below agreed adjustments, the scope rule and what the pupil has just asked.
"""
import json
import re
from dataclasses import asdict, dataclass, field

from .config import Settings
from .transcripts import ID_RE

PHASES = ("goal", "warm_up", "practice", "wrap_up")
WARM_UP_WINDOW = 4      # turns in which the warm-up may be asked before we give up on it
OFFER_WRAP_UP_AFTER = 6  # answers, or twice as many turns


@dataclass
class Session:
    goal: str | None
    goal_id: str | None
    goal_is_preview: bool
    recall_topic: str | None
    next_topic: str | None
    turns: int = 0
    answers: int = 0
    correct: int = 0
    recall_asked: bool = False
    recall_pending: bool = False
    recall_result: str | None = None   # "right" | "partly" | "not yet"
    finished: bool = False
    log: list[dict] = field(default_factory=list)  # one line per answer, for the wrap-up

    @property
    def phase(self) -> str:
        if self.finished:
            return "wrap_up"
        if self.turns == 0:
            return "goal"
        if self.recall_topic and not self.recall_asked and self.turns < WARM_UP_WINDOW:
            return "warm_up"
        return "practice"

    def view(self) -> dict:
        return {"goal": self.goal, "goal_is_preview": self.goal_is_preview, "phase": self.phase,
                "recall_topic": self.recall_topic, "recall_result": self.recall_result, "answers": self.answers,
                "correct": self.correct, "next_topic": self.next_topic, "finished": self.finished}


# ---------------------------------------------------------------- planning from the briefing
def _strip_week(item: str) -> tuple[int | None, str]:
    m = re.match(r"Wk(\d+)\s+(.*)", item)
    return (int(m.group(1)), m.group(2)) if m else (None, item)


def pick_recall(b: dict) -> str | None:
    """An earlier, taught topic the pupil has some hold on: retrieval practice that also primes today's goal.
    Prefer a prerequisite of the focus, then a secure topic, then the earliest taught topic. Never the focus itself,
    never something not yet taught."""
    cls, lr, focus = b.get("class") or {}, b.get("learner") or {}, (b.get("focus") or {}).get("label")
    taught = {label: wk for wk, label in map(_strip_week, cls.get("taught_so_far") or [])}

    def ok(label: str) -> bool:
        return label in taught and label != focus

    prereqs = sorted((p for p in lr.get("prerequisites") or [] if p.get("status") in ("secure", "developing", "no evidence")),
                     key=lambda p: (p.get("status") != "secure", -(p.get("strength") or 0)))
    for p in prereqs:
        if ok(p["label"]):
            return p["label"]
    secure = [o["topic"] for o in lr.get("overview") or [] if o.get("status") == "secure" and ok(o["topic"])]
    if secure:
        return min(secure, key=lambda t: taught[t] or 99)
    rest = [label for label in taught if ok(label)]
    return min(rest, key=lambda t: taught[t] or 99) if rest else None


def plan(b: dict) -> Session:
    focus, cls, ns = b.get("focus") or {}, b.get("class") or {}, (b.get("guidance") or {}).get("next_step") or {}
    preview = cls.get("focus_taught") is False
    goal = focus.get("label") or (ns.get("concept") or {}).get("label")
    nxt = (ns.get("after_that") or {}).get("label") if ns.get("action") == "consolidate" else None
    return Session(goal=goal, goal_id=focus.get("id"), goal_is_preview=preview, recall_topic=pick_recall(b),
                   next_topic=nxt)


# ---------------------------------------------------------------- the prompt block
def render(s: Session, finishing: bool = False) -> str:
    head = ("# This session\n"
            "A plan for this conversation. It ranks below agreed adjustments, the scope rule and what the pupil has just "
            "asked: if they conflict, follow those and come back to the plan later.\n")
    goal = s.goal or "whatever the pupil wants help with"
    if s.goal_is_preview:
        goal = f"a short, clearly flagged first look at {goal} (not yet taught to the class)"
    lines = [f"Session goal: {goal}."]
    phase = "wrap_up" if finishing else s.phase
    if phase == "goal":
        lines.append("Stage: start. Answer what the pupil asked first. Then, in one short sentence, say what you will "
                     "work on together today (the session goal), in words a pupil would use.")
    elif phase == "warm_up":
        lines.append(f"Stage: warm-up. When the pupil's current question is dealt with, ask one quick recall question "
                     f"on \"{s.recall_topic}\" (taught earlier), to bring it back to mind. Say it is a quick warm-up. "
                     f"One question only, no teaching unless they get it wrong. If they are mid-problem, finish that "
                     f"first. Set \"recall_asked\": true in your assessment block in the reply where you ask it.")
    elif phase == "practice":
        lines.append("Stage: practice. Work towards the goal one question at a time, using the class's method and the "
                     "teacher's practice materials where they fit. Each question should need the pupil to do the "
                     "thinking.")
        if s.answers >= OFFER_WRAP_UP_AFTER or s.turns >= 2 * OFFER_WRAP_UP_AFTER:
            lines.append("They have done a good amount: after this question, offer to wrap up (they can press Finish).")
    else:
        record = "; ".join(f"{e['topic']}: {e['result']}" for e in s.log[-8:]) or "no answers this session"
        lines.append("Stage: wrap-up. The pupil is finishing. Reply in at most three short sentences: one line on what "
                     "they did this session (from the record below, praising a specific thing they did), one thing to "
                     "remember, and what comes next" + (f" ({s.next_topic})" if s.next_topic else "") +
                     ". Ask no new question.")
        lines.append(f"Session record: {s.answers} answer(s), {s.correct} right. {record}.")
    if s.recall_pending:
        lines.append(f"Your last reply asked the warm-up question on \"{s.recall_topic}\"; the pupil's message is "
                     f"probably their answer to it.")
    return head + "\n".join(lines)


# ---------------------------------------------------------------- after the turn
def _result(score: float) -> str:
    return "right" if score >= 1 else "partly" if score > 0 else "not yet"


def answer_topic(s: Session, briefing: dict | None) -> str | None:
    """Which topic this turn's answer was about: the warm-up topic if we were waiting for it, else the focus."""
    if s.recall_pending and s.recall_topic:
        return s.recall_topic
    return ((briefing or {}).get("focus") or {}).get("label") or s.goal


def update(s: Session, assessment: dict | None, briefing: dict | None, finishing: bool) -> None:
    a = assessment or {}
    score = a.get("score")
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        score = 1.0 if a.get("correct") is True else 0.0 if a.get("correct") is False else None
    if a.get("answered") is True and score is not None:
        topic = answer_topic(s, briefing)
        s.answers += 1
        s.correct += score >= 1
        s.log.append({"topic": topic, "result": _result(score)})
        if s.recall_pending:
            s.recall_result = _result(score)
    if s.recall_pending:
        s.recall_pending = False
    if a.get("recall_asked") is True and s.recall_topic and not s.recall_asked:
        s.recall_asked = s.recall_pending = True
    s.turns += 1
    s.finished = finishing


# ---------------------------------------------------------------- storage, next to the transcript
def _path(settings: Settings, conversation_id: str):
    if not ID_RE.match(conversation_id):
        raise ValueError("bad conversation id")
    d = settings.data_dir / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{conversation_id}.json"


def load(settings: Settings, conversation_id: str) -> Session | None:
    p = _path(settings, conversation_id)
    return Session(**json.loads(p.read_text())) if p.exists() else None


def save(settings: Settings, conversation_id: str, s: Session) -> None:
    _path(settings, conversation_id).write_text(json.dumps(asdict(s), ensure_ascii=False))
