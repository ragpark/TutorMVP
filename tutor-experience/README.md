# tutor-experience

An AI tutoring experience for UK secondary pupils, built to test the
[Curriculum Map](https://h2-app-production.up.railway.app) service
([source](https://github.com/ragpark/h2-curriculum-context-poc)). **The tutor is the thing under test; the map is a
fixed external dependency.** At the start of every turn the tutor asks the map for a briefing — the pupil's focus
topic, what they are secure, developing or have a gap on, what the class has and hasn't been taught, the class's method,
the teacher's materials, any agreed adjustments and guidance — and replies from it.

All pupil data comes from the map and is synthetic. This project holds no pupil state of its own: only conversation
transcripts and per-turn logs.

## How a turn works

```
pupil message ─▶ briefing.py ─▶ prompting.py ─▶ model.py ─▶ evidence.py ─▶ reply
                 POST /api/context   system prompt     one Claude call   POST /api/evidence
                 (UI turns only)     + messages        logged to disk    (if switched on)
```

| Module | Job |
| --- | --- |
| `app/briefing.py` | Fetch the briefing for (pupil, message). If the map can't be reached, the turn runs with no context and the reply says so. Nothing is invented. |
| `app/prompting.py` | Turn the briefing into the system prompt (see [`docs/system-prompt.md`](docs/system-prompt.md)). Agreed adjustments (`support_profile`) come first and are REQUIRED; `how_to_support` is advisory. |
| `app/model.py` | One Claude call per turn. The full prompt and response are written to `data/turns/<date>/<turn_id>.json`. |
| `app/evidence.py` | When the pupil answered a question, write it back as `activity` + `score` with `source: "tutor-experience"`. |
| `app/turn.py` | The two entry points: UI turns and harness turns. |
| `app/main.py` | FastAPI routes: `/` (chat UI), `/api/pupils`, `/api/turn`, `/webhook/tutor`, `/health`. |

## The three integration routes

The map offers three routes. This tutor uses the first two and can be registered through the third.

1. **REST** — what the tutor uses at runtime.
   - `GET /api/pupils` fills the pupil picker. The subject follows the pupil's class.
   - `POST /api/context` `{"learner": "pupil:amara", "message": "...", "concept": null}` → the briefing, at the start of every UI turn.
   - `POST /api/evidence` `{"learner", "source", "activity", "score", "misconception"?, "process"?}` after a turn in which the pupil answered a question.
   - `GET /api/subjects`, `GET /api/classes`, `GET /api/graph?subject=maths` and `GET /api/graph/node?id=...` are there for browsing the map; `app/map_client.py` wraps the first two.
2. **MCP** (streamable HTTP at `/mcp`) — `get_learning_context`, `get_prerequisites`, `find_teacher_materials`,
   `align_text` and `record_evidence`. `get_learning_context` returns the same briefing as `POST /api/context`. The
   fixtures in `tests/fixtures/` were captured through it.
3. **Tutor webhook** — so the map's evaluation harness can drive this tutor blind (see below).

## Run locally against the live map

Requires Python 3.12.

```sh
cp .env.example .env        # set ANTHROPIC_API_KEY; MAP_BASE_URL already points at the live map
make install
make run                    # http://localhost:8000
make test                   # no network: the map and the model are both mocked
```

Pick a pupil, then type as them. Each tutor reply shows which topic the map's briefing focused on and whether the
answer was recorded. The **Record answers** switch (on by default) controls write-back. Ben and Farah are the pupils
with agreed adjustments.

| Variable | Meaning |
| --- | --- |
| `MAP_BASE_URL` | The map. Default `https://h2-app-production.up.railway.app`. |
| `ANTHROPIC_API_KEY` | Needed for any reply. Never commit it. |
| `TUTOR_SECRET` | If set, the webhook requires a matching `X-Tutor-Secret` header. |
| `MODEL` | Default `claude-sonnet-4-5`. |
| `EVIDENCE_FROM_HARNESS` | `true` lets harness turns in the `h2` condition write evidence. Default `false`. |
| `WEBHOOK_BUDGET_S` | Time allowed for a whole harness turn. Default 50 (the harness waits 60). |
| `DATA_DIR` | Where turn logs and transcripts go. Default `./data` (git-ignored). |
| `TUTOR_PUBLIC_URL` | This deployment's public URL, for `make register`. |

## Register for evaluation

The harness POSTs `{turn_id, subject, arm, pupil, message, context}` to `/webhook/tutor` and expects
`{"reply": "..."}` (JSON, 2xx) within 60 s. The `arm` field names the condition:

| Condition | `context` contains | What the tutor does |
| --- | --- | --- |
| `h2` | the map's briefing | renders it exactly as for a UI turn |
| `raw` | an unorganised pack | passes it to the model verbatim as JSON |
| `none` | `{pupil: {name, year}}` | uses only the name and year |

The tutor honours the condition: **on harness turns it never calls `/api/context`**, so the control conditions
aren't contaminated. It writes evidence only in the `h2` condition, and only if `EVIDENCE_FROM_HARNESS=true`. If a
turn overruns the budget, the webhook returns 504 rather than a made-up reply, so the harness records an error.

Deploy (Railway: `railway.toml` builds the `Dockerfile`; set the variables above as service variables), then:

```sh
TUTOR_PUBLIC_URL=https://<your-deployment> TUTOR_SECRET=<shared secret> make register
make ping TUTOR_ID=<id printed by register>
```

`register` calls `POST /api/tutors {"label", "kind": "webhook", "url": "<TUTOR_PUBLIC_URL>/webhook/tutor", "secret"}`.

## Design notes

### Decisions made

- **The briefing is rendered, not dumped.** In the `h2` condition the prompt has named sections in order of authority:
  agreed adjustments, scope, what the pupil asked, how to teach it, the pupil, quotations, materials, then advisory
  patterns. IDs, mastery numbers, crosswalks, retrieval scores and who agreed the adjustments are left out (they are
  still in the turn log).
- **The `raw` pack is passed verbatim.** Reorganising it would test our renderer rather than the map's organisation.
- **The same fixed rules apply in every condition**, including the hidden assessment instruction, so conditions differ
  only in the context they carry.
- **Answer the question first.** The fixed rules tell the tutor to deal with what the pupil asked or answered before
  steering to the weakest skill. This addresses a known failure mode. Agreed adjustments still outrank it: for Ben,
  "no hint before an attempt" wins over "answer the question".
- **One call, with a hidden assessment block.** Alongside the reply, the model emits an `<assessment>{…}</assessment>`
  JSON block judging whether the pupil answered a question, and how well. It is stripped before anything is shown or
  returned. This keeps it to one call per turn and works on models without structured outputs. If the block is
  malformed or missing, nothing is recorded.
- **Evidence is `activity` + `score`, never concept IDs.** The map treats concept-tagged evidence as a teacher's mark
  (full weight). An activity title is tagged by the map's alignment service at reduced weight, which suits a tutor's
  in-chat judgement. The focus topic goes into the activity title so the alignment has something to go on. A
  misconception is sent only if it is one the briefing listed. One `attempt` process event is sent, timed from the
  tutor's previous reply when the UI knows it.
- **If the map is unreachable, the reply says so.** It opens with a fixed sentence saying the map couldn't be reached,
  the model is told it knows nothing about the class, and no evidence is written.
- **The webhook fails loudly.** A bad secret gets 401, a malformed body 422, a model failure 502, and an overrun 504.
  It never returns a placeholder reply for the harness to score.
- **The map is mocked at the HTTP transport** (`httpx.MockTransport`) and the model at the call seam. Tests use the
  real briefing fixtures.

### Left open deliberately

- **Streaming replies** in the UI. Turns are short, and a single JSON response keeps the webhook and UI paths identical.
- **Pupil-facing safeguarding and moderation** beyond the model's own behaviour. This needs a policy decision before
  any real pupil sees it.
- **Multi-turn harness scenarios.** The harness sends single turns with no history, so the webhook keeps none.
- **Using the `concept` field** of `POST /api/context` (pinning a topic from the UI), and MCP as a runtime route.
  REST is enough for v0.1.
- **Tuning the 140-word limit, the model and `max_tokens`.** These wait for the first evaluation run.
- **Whether `how_to_support` should be shown when it is empty but `based_on` is non-zero.** At present it is omitted
  unless it has patterns or strengths.
- **Retention of `data/`.** On Railway it is ephemeral unless a volume is attached.

## Licence

MIT — see [LICENSE](LICENSE).
