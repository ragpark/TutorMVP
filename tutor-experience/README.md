# tutor-experience

An AI tutoring experience for UK secondary pupils, built to test the
[Curriculum Map](https://h2-app-production.up.railway.app) service. The tutor is the thing under test; the map is a
fixed external dependency that supplies a briefing at the start of every turn.

Status: v0.1 in progress. Real briefings from the live map are in `tests/fixtures/`; the proposed system prompt is in
`docs/system-prompt.md`. Full setup, integration and design notes follow once the turn pipeline lands.

All pupil data comes from the map and is synthetic.
