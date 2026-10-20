# Claude Code prompt: build spaced retrieval in the Curriculum Map

Paste the text below into Claude Code, run from a checkout of `ragpark/h2-curriculum-context-poc`. It is self-contained;
the full rationale is in `map-spaced-retrieval.md` next to this file.

---

Add spaced retrieval to this Curriculum Map, so each briefing can tell a tutor which earlier topics a pupil is due to
recall. Work in small conventional commits on a new branch. British English in all prose, comments and UI copy. Use the
map's own names: briefing, condition, agreed adjustments, scheme of work, evidence, learner state.

Context: tutors call `POST /api/context` (and MCP `get_learning_context`) at the start of each turn and get one briefing
built by `context._with_h2`. Evidence is append-only (`evidence` table); `learner.project` replays it to rebuild
`learner_state`. Process events go through `behaviour.ingest` using the vocabulary in `seed/behaviours.yaml`. Nothing
in the map currently models time: `learner_state` never fades, and every synthetic event is stamped "now".

Before writing code, read `app/learner.py`, `app/context.py`, `app/behaviour.py`, `app/adjustments.py`, `app/db.py`,
`app/seed.py`, `app/main.py`, `app/mcp_server.py`, `seed/behaviours.yaml` and the seed fixtures. Then show me a short
plan (files to touch, new tables and routes, the exact briefing JSON you will add) and wait for my go-ahead. Stop and
ask if anything below disagrees with the code.

Build, in this order:

1. **A clock you can set.** Add `app/clock.py` with `now()` and `today()`: real time plus an offset in days stored in
   `meta` (`clock_offset_days`, default 0).
   - Admin routes: `GET /api/admin/clock`, and `POST /api/admin/clock` with `{"advance_days": n}`, `{"set": "YYYY-MM-DD"}`
     or `{"reset": true}`. Follow the existing admin routes' conventions.
   - Route every "now" through it. `learner.record` must insert `ts` explicitly from `clock.now()`;
     `adjustments.profile` must use `clock.today()`. Grep for any others.
   - Add `"as_of": clock.today()` to the briefing.

2. **Backdated synthetic histories.** Let seed evidence and scenario steps take an optional `days_ago`, written as
   `ts = clock.now() - days_ago`.
   - Give Amara, Ben and Priya histories spread over 3–6 weeks, consistent with their current learner state. Amara
     should have secured one- and two-step equations in week 1 and not seen them since. Ben should include one lapse.
   - Existing briefings for these pupils must not change apart from the new keys. Show me a before/after diff of
     Amara's briefing to prove it.

3. **Retention projection.** Add `app/retention.py` with a pure function `schedule(events, now) -> dict[concept, state]`
   (no database access), plus a `review_state` table rebuilt from evidence whenever `learner.project` runs. Columns:
   `learner, concept, level, interval_days, last_success, last_seen, due_at, lapses, reviews`.
   - Leitner-style intervals `INTERVALS = [1, 3, 7, 14, 30, 60]` days.
   - Only direct evidence on a concept counts, never inferred prerequisite credit.
   - First evidence: level 1 on success (`outcome >= 0.5`), 0 on failure.
   - Success after `due_at`: level + 1 (capped) and reviews + 1.
   - Success before `due_at`: last_seen updates, level does not change.
   - Failure: level 0, lapses + 1.
   - `due_at = last_success + INTERVALS[level]`.

4. **A `retrieval` process event.** Add `{type: retrieval, fields: [concept, prompted_by]}` to the process vocabulary in
   `seed/behaviours.yaml`, where `prompted_by` is `tutor`, `quiz` or `teacher`. Make sure `behaviour.ingest` stores it.
   Derive no indicators from it yet.

5. **Tutor provenance.** `POST /api/evidence` and MCP `record_evidence` accept an optional `provenance: "tutor"`. With
   `concepts`, store `concept_provenance = "tutor"`. In `learner.project`, weight it between the alignment service and
   a teacher: `w = 0.8`, `base = 0.4`, as named constants beside `SECURE`/`DEVELOPING`. Without the field, behaviour is
   unchanged.

6. **`due_for_review` in the briefing.** In `context._with_h2`, after `how_to_support`, add:
   ```json
   "due_for_review": {"rule": "Advisory. Use at most one, as a short warm-up recall question, and only when it doesn't get in the way of what the pupil asked. Never describe the pupil by these.",
                      "as_of": "YYYY-MM-DD",
                      "items": [{"id": "...", "label": "...", "taught_week": 1, "last_success": "YYYY-MM-DD",
                                 "interval_days": 14, "overdue_days": 27, "why": "..."}]}
   ```
   - Eligible topics:
     - taught to the class (in `taught_so_far`)
     - at least one piece of direct evidence
     - `due_at <= clock.now()`
     - not the focus
     - learner status `secure` or `developing` (never `gap`)
   - Rank by `overdue_days / interval_days`. Multiply by 1.5 for prerequisites of the focus or of `next_step`. Break
     ties in favour of a different scheme week from the focus.
   - At most 3 items; `items: []` when none.
   - Keep `why` short and about the topic, never a label for the pupil.
   - For fairness between conditions, add a relative time such as "(5 weeks ago)" to each `recent_activity` line in the
     raw pack (`_without_h2`). The `none` condition is unchanged.

7. **Inspection.**
   - `GET /api/learners/{id}/review`: full review state, due items first.
   - MCP tool `get_review_schedule(learner_id)`, with the same content.
   - A small "Due for review" list on the learner view of the web UI, if it is a small change. Otherwise skip it and
     tell me.

8. **Tests.** The repo has no test suite: add `tests/` with pytest, plus a `requirements-dev.txt` if needed. Write
   database-free unit tests for:
   - `retention.schedule`: every rule above, plus the interval cap and that inferred credit is ignored
   - eligibility and ranking
   - clock arithmetic

   Then run this end-to-end check against a local Postgres and paste me the output:
   1. Reset and seed.
   2. Advance the clock 21 days.
   3. `POST /api/context` for `pupil:amara` with "can you give me a question to practise?". `due_for_review.items[0]`
      should be one- and two-step equations.
   4. Record a correct answer with `provenance: "tutor"`, that concept and a `retrieval` process event. That item
      should leave the list and its interval grow.
   5. Advance the clock past the new interval. It should return.

9. **Docs.** Update the README and the in-app help:
   - the new briefing block and its eligibility and ranking rules
   - the clock and its admin routes
   - the `retrieval` event and `tutor` provenance
   - that h2 briefings are now about 60–120 tokens longer, so evaluation baselines from before the change aren't
     strictly comparable. Bump `graph_version` or add a `briefing_version`, and say which.

Constraints:
- Everything is additive. Tutors that ignore the new key, field and event type must behave exactly as before.
- `review_state` is a derived projection: it must be rebuildable from the evidence log alone, like `learner_state`.
- Do not add decay to `learner_state.mastery`. Retention lives in its own projection.
- Do not change the evaluation harness, suites or judge.
- All pupil data stays synthetic.

When done, give me:
- the final briefing JSON for Amara with the clock advanced 21 days
- the list of commits
- the four decisions I still need to make:
  - the tutor provenance weight
  - whether `developing` topics qualify
  - clock scope: global, or per class
  - whether the raw-pack timestamps ship now
