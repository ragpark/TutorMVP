# Change proposal: spaced retrieval in the Curriculum Map

**For:** `ragpark/h2-curriculum-context-poc` (the Curriculum Map)
**From:** tutor-experience
**Status:** proposed, 2026-10-20
**Summary:** add a `due_for_review` block to the briefing, so a tutor can open a session with a warm-up recall question
on a topic the pupil is due to revisit. Retention becomes a derived projection rebuilt from the evidence log, alongside
`learner_state`. A clock you can set makes it testable with synthetic pupils.

## 1. Why

Spaced retrieval (recalling something from memory after a gap that grows each time you succeed) is one of the most
robust findings in learning science. tutor-experience already asks one warm-up recall question per session. Today it
picks the topic from the current briefing alone: a taught, secure prerequisite of the focus. That is retrieval, but not
*spaced* retrieval. Choosing what is *due* needs each pupil's history over time.

That history belongs to the map. The tutor could work it out from `GET /api/learners/{id}`, but that would put a
learner model in the tutor, which the integration rules forbid. It would also be capped at 60 evidence entries and could
disagree with the map's own view of the pupil.

## 2. What the map has today, and what's missing

| Need | Today | Gap |
| --- | --- | --- |
| When each topic was last evidenced | `evidence.ts` (DB default `now()`), with `concepts` | Not in the briefing; no per-topic summary |
| Whether a topic is fading | `learner_state.mastery`, rebuilt by replaying evidence in order (`learner.project`) | No time in the model: secure stays secure for ever |
| What counts as a recall attempt | Process events (`attempt`, `hint_requested`, …) in `behaviours.yaml` | No way to say "retrieved from memory after a gap" |
| Which topic a tutor's warm-up was about | Activity title tagged by the alignment service at reduced weight | The tutor knows the topic exactly, but has no provenance level between "claude" and "teacher" |
| Testing with synthetic pupils | Evidence is stamped at insert time; `adjustments.py` uses `date.today()` | Every synthetic event happens "now", so nothing is ever due |

## 3. Proposed changes

### 3.1 A clock you can set (`app/clock.py`)

- `clock.now()` / `clock.today()` return real time plus an offset stored in `meta` (`clock_offset_days`, default 0).
- `POST /api/admin/clock {"advance_days": 7}` or `{"set": "2026-11-15"}`; `GET /api/admin/clock`;
  `POST /api/admin/clock {"reset": true}`.
- Every "now" in the map goes through it:
  - `learner.record` inserts `ts` explicitly from `clock.now()` instead of relying on the column default
  - `adjustments.profile` uses `clock.today()` for review dates
  - scheme "current week", if derived from dates anywhere
- The briefing gains `"as_of": "<clock.today()>"`, so a reader can tell when the clock is not real time.

### 3.2 Backdated synthetic histories

- Seed evidence and scenario steps accept an optional `days_ago` (or `on: YYYY-MM-DD`). The seeder writes
  `ts = clock.now() - days_ago`.
- Give a few synthetic pupils histories spread over 3–6 weeks, so `due_for_review` is non-empty out of the box:
  - Amara: one- and two-step equations secured in week 1, not seen since
  - Priya: context topics from week 1
  - Ben: a mix, including one lapse

### 3.3 Retention projection (`app/retention.py`)

A new derived projection, `review_state`, rebuilt from the evidence log the same way `learner.project` rebuilds
`learner_state`. Rebuild it in `learner.project`, or right after it.

```
review_state(learner, concept, level int, interval_days real, last_success timestamptz, last_seen timestamptz,
             due_at timestamptz, lapses int, reviews int, primary key (learner, concept))
```

**Rule: Leitner-style expanding intervals.** It is a pure function, `schedule(events, now) -> per-concept state`, with
no database access, so it can be unit-tested.

- Intervals by level: `[1, 3, 7, 14, 30, 60]` days (`INTERVALS` constant).
- Walk direct evidence for each concept in time order. Inferred credit (prerequisite propagation) does not count.
- Success (`outcome >= 0.5`):
  - **after** `due_at`: level + 1 (capped); counts as a review
  - **before** `due_at`: last seen is updated, but the level does not change, so cramming doesn't move a topic up
- Failure (`outcome < 0.5`) at any time: level drops to 0 and the lapse count goes up.
- First direct evidence sets level 0 on failure or 1 on success.
- `due_at = last_success + INTERVALS[level]`.
- Evidence with a `retrieval` process event (§3.4) is marked as such for analytics. Scheduling treats all direct
  evidence the same: the rule looks at gaps, not labels.

**Why not FSRS or SM-2 now:** Leitner intervals are easy to explain to teachers, easy to test, and good enough for a
proof of concept. The pure-function seam lets a better rule replace it later without touching anything else.

### 3.4 Marking a recall attempt (`retrieval` process event)

- Add `{type: retrieval, fields: [concept, prompted_by]}` to the process vocabulary in `seed/behaviours.yaml`.
  `prompted_by` is `"tutor" | "quiz" | "teacher"`.
- `behaviour.ingest` stores it like other events. No indicators are derived from it yet.
- `record_evidence` (MCP) and `POST /api/evidence` already accept `process`, so there is no API change.

### 3.5 Tutor provenance for concept tags

Today a caller either sends `concepts` (stored as `teacher` provenance, weight 1.0) or an activity title (aligned by
Claude, weight 0.6 × confidence). Neither fits a tutor that knows exactly which topic it asked about, but whose marking
is an AI judgement.

- Accept `"provenance": "tutor"` on `POST /api/evidence` (and `record_evidence`). With `concepts`, store
  `concept_provenance = "tutor"`.
- In `learner.project`, give `tutor` a weight between the two, for example `w = 0.8`, `base = 0.4`. Make it a named
  constant next to `SECURE` and `DEVELOPING`.
- Without the field, behaviour is unchanged.

This is what lets tutor-experience tag warm-up answers precisely without them counting as a teacher's mark.

### 3.6 `due_for_review` in the briefing

In `context._with_h2`, after `how_to_support`:

```json
"due_for_review": {
  "rule": "Advisory. Use at most one, as a short warm-up recall question, and only when it doesn't get in the way of what the pupil asked. Never describe the pupil by these.",
  "as_of": "2026-11-15",
  "items": [
    {"id": "cc:maths/alg/lin-eq-simple", "label": "Solve one- and two-step linear equations",
     "taught_week": 1, "last_success": "2026-10-04", "interval_days": 14, "overdue_days": 27,
     "why": "secure in week 1, not recalled for 6 weeks; a prerequisite of today's topic"}
  ]
}
```

**Which topics qualify:**

- taught to the class (in `taught_so_far`)
- at least one piece of direct evidence
- `due_at <= clock.now()`
- not the focus
- status `secure` or `developing`, not `gap`: a gap needs teaching, not retrieval

**Ranking:**

1. Overdue ratio, `overdue_days / interval_days`, highest first.
2. Boost (×1.5) prerequisites of the focus or of `next_step`. Retrieval that primes today's work counts double.
3. Prefer topics from a different scheme week from the focus (interleaving).

At most 3 items. When nothing qualifies, `items: []`.

**Fairness to the evaluation conditions:**
- `raw`: the map's principle is that `raw` carries the same information, less organised. Add a relative time to each
  `recent_activity` line, such as "(5 weeks ago)", so the raw condition also knows when things happened.
- `none`: unchanged.

### 3.7 Inspection routes

- `GET /api/learners/{id}/review`: the full `review_state` for one pupil, due items first.
- MCP `get_review_schedule(learner_id)`, with the same content.
- Learner view in the map's web UI: a small "Due for review" list, if cheap to add.

## 4. What changes for tutors

- **Additive only:** a new briefing key, a new optional evidence field and a new process event type. Tutors that ignore
  them are unaffected.
- **h2 briefings grow by about 60–120 tokens.** Evaluation baselines taken before the change are not strictly
  comparable. Record the change in `graph_version` or a new `briefing_version`.
- **tutor-experience will:**
  - pick the warm-up from `due_for_review.items[0]`, falling back to its current rule when the list is empty
  - send warm-up answers with `provenance: "tutor"`, the concept ID and a `retrieval` process event
  - write no schedule of its own

## 5. Testing

The map has no test suite. This change adds one (`tests/`, pytest) for the pure parts, with no database needed:

- `retention.schedule`: success after due moves up a level; success before due doesn't; failure resets; intervals cap;
  inferred credit ignored; order independence of ties.
- Ranking and eligibility: not taught → excluded; gap → excluded; focus → excluded; prerequisite boost; at most 3.
- `clock`: offset maths; `today()` crosses midnight correctly.
- **End-to-end, against a local database:**
  1. Reset, then seed backdated histories.
  2. `advance_days: 21`.
  3. `POST /api/context` for Amara: `due_for_review.items[0]` is one- and two-step equations.
  4. Record a correct answer with a `retrieval` event; that item leaves the list and its interval grows.
  5. Advance the clock past the new interval; it returns.

## 6. Out of scope (for now)

- **Decay in `learner_state.mastery`.** Retention lives in its own projection, so mastery stays a measure of what has
  been shown, not of what has been forgotten.
- **Evaluating the learning gain of spacing.** The harness is single-turn. A multi-session simulation using the clock
  is a follow-up.
- **Per-pupil interval tuning (FSRS)** and teacher overrides of the schedule.

## 7. Decisions for the map owner

1. **The `tutor` provenance weight** (0.8 proposed), and whether it should also apply to the activity + score route.
2. **Whether `developing` topics qualify for review**, or only `secure` ones (proposed: both).
3. **Clock scope:** global (proposed, simplest) or per tenant/class.
4. **Whether the raw-pack timestamps (§3.6) ship in the same change**, so the conditions stay fair from day one
   (proposed: yes).
