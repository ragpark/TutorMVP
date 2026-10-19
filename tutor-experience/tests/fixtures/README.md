# Fixtures

Real briefings captured from the live Curriculum Map on 2026-10-19, so the prompt builder is developed against the map's
actual shape. All pupils are synthetic.

| File | Learner | Message | Notes |
| --- | --- | --- | --- |
| `briefing_maths_amara.json` | `pupil:amara` (10X) | "I don't get how to solve 3x + 5 = x + 13, do I move the x first?" | Focus taught; no agreed adjustments. |
| `briefing_maths_ben_adjustments.json` | `pupil:ben` (10X) | "how do I do 3(x + 2) = 15" | Has a `support_profile` (agreed adjustments); focus **not yet taught** (week 5), so the scope rule applies. |
| `briefing_english_priya.json` | `pupil:priya` (11E) | "Why does Lady Macbeth call on the spirits to unsex her?" | English: Macbeth; has `key_quotations` and `text_studied_so_far`. |
| `context_none_amara.json` | `pupil:amara` | — | What the evaluation harness sends for the `none` condition (`{pupil: {name, year}}`), per `app/evals.py::_context` in the map's source. |

Captured through the map's MCP tool `get_learning_context`, which calls the same `context.assemble(..., facets=True)`
as `POST /api/context`; the REST host was not reachable from the capture environment. Whitespace was compacted;
content is unchanged.
