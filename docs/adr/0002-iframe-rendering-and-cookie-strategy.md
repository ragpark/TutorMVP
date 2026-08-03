# ADR-002: Iframe rendering and third-party cookie strategy

* Status: accepted
* Date: 2026-08-03

## Context and Problem Statement

`container-ui` renders learning objects inside a sandboxed `<iframe>` so the
platform controls CSP, sandbox flags, and message-passing regardless of what
a product team's tool does internally. Browsers increasingly restrict
cross-site storage available to content inside a third-party iframe
(cookies, `localStorage`, IndexedDB), which is exactly the position our
iframe-embedded tools are in relative to the platform's top-level origin —
and relative to whatever origin an external LMS embeds *us* under, when we
act as an LTI Tool.

Two distinct needs must be met without relying on unpartitioned third-party
cookies:

1. **Our own session/identity handoff** — the container needs to correlate
   the tool instance with the LTI launch (actor, resource link, registration)
   for save-state, resume, and telemetry stamping, across the lifetime of one
   iframe.
2. **A tool's own session**, if any — some tools (especially third-party or
   pre-existing SaaS tools) may have their own backend and want ordinary
   cookie-based session behavior inside the iframe, independent of our
   bridge.

This is called out as the highest-risk decision in this architecture because
browser third-party storage policy is inconsistent across engines, changes
over time, and a wrong default here degrades or breaks the product silently
for a subset of learners' browsers.

## Decision Drivers

* Must work today in Safari and Firefox, which already block unpartitioned
  third-party cookies by default (Safari ITP, Firefox ETP/Total Cookie
  Protection), not just in some future Chrome state.
* Must not depend on a browser-specific privacy-sandbox timeline that keeps
  moving — the platform's own identity/session handoff should not need
  third-party cookies **at all**, on any browser.
* Must degrade gracefully and visibly rather than silently losing learner
  progress (a tool that "works" but silently can't save state is worse than
  one that visibly asks the learner to open a new tab).
* Must not widen the iframe sandbox or grant storage access without an
  explicit, auditable step — this is a security boundary, not just a UX
  concern.

## Considered Options

* **A — Partitioned cookies (CHIPS)**: the tool's backend sets cookies with
  the `Partitioned` (and `Secure`) attribute; each top-level embedding site
  gets an independent, isolated cookie jar for that third-party origin. No
  user gesture required; degrades to "no cookie" (not an error) where
  unsupported.
* **B — Storage Access API**: the iframe calls
  `document.requestStorageAccess()` (or the still-emerging
  `requestStorageAccessFor()` on the top-level document) to ask for its
  ordinary unpartitioned first-party storage inside the third-party context.
  Requires a user gesture and is subject to per-browser heuristics/prompts.
* **C — Platform-side session storage keyed by `state`**: `launch-gateway`
  and `container-ui` keep the authoritative session server-side, keyed by
  the opaque `state` value already generated for the OIDC launch (Redis-backed,
  per ADR-001). Identity/session correlation is handed to the iframe via a
  short-lived, single-use, scoped launch token in the iframe's `src` URL
  and reinforced by the `bridge-protocol` `postMessage` handshake — no
  cross-site cookie of any kind is involved.
* **D — New-tab fallback**: abandon iframe embedding for a given launch;
  navigate the top-level browser window to the tool's launch URL instead.
  A top-level navigation is always first-party from the tool's perspective,
  so no third-party storage restriction applies; the learner returns to the
  platform via the ordinary LTI platform-return navigation.

## Decision Outcome

**Primary: Option C.** The launch identity and session handoff between
`container-ui` and the tool — the thing we actually control and that must
work for every learner, on every browser, on day one — is designed to need
**no third-party cookie at all**. The `id_token` is already delivered via
`form_post` (ADR-001), not a cookie; `container-ui` mints a short-lived,
single-use, scoped launch/session token bound to the Redis-backed `state`
record and passes it to the tool as a URL parameter on the iframe `src` (and
again over the `bridge-protocol` `ready` handshake), so the tool can call
back into `registry-api`/`xapi-gateway` with that token as a bearer
credential. This is deliberately boring and universally supported: it has no
dependency on evolving browser cookie policy, works identically in every
engine, and is the only option that doesn't degrade for some fraction of
learners by default.

**Fallback chain for a tool's own third-party session** (only relevant to
tools that maintain their own backend session independent of our bridge —
most learning objects built against `bridge-protocol` should not need this
at all):

1. **CHIPS (Option A)** where the tool's backend and browser support it.
   No user gesture, fails closed (silently absent cookie, not an error), so
   it is safe to attempt unconditionally. Known gap: partitioning means the
   tool gets a *different* cookie jar per embedding top-level site — this is
   a feature for us (isolation between tenants/platforms embedding the same
   tool), not a workaround for a single unified cross-site session.
2. **Storage Access API (Option B)** where CHIPS isn't available or the tool
   genuinely needs its pre-existing unpartitioned storage. Because this
   requires a user gesture, `container-ui` must not attempt it silently on
   load — the tool signals over `bridge-protocol` (a `state.restore`
   failure or an explicit "needs storage access" message,
   `TODO(spec): exact message shape to be defined when bridge-protocol
   is implemented in Phase 3`) and the container renders an explicit,
   visible "Continue" affordance whose click satisfies the gesture
   requirement before the tool calls `requestStorageAccess()`.
3. **New-tab fallback (Option D)** as the last resort, when neither A nor B
   establishes usable storage (detected via a bounded timeout on the
   `bridge-protocol` `ready`/`state.restore` handshake, or an explicit tool
   error). `container-ui` shows a clear degraded-mode UI explaining that the
   tool needs to open in a new tab, and re-launches the same LTI flow as a
   top-level navigation. This always works but breaks the single-page
   embedded experience and is subject to popup-blocker UX, so it is a
   fallback, never a default.

### Browser support assumptions

These are the assumptions the fallback chain is designed against. Browser
privacy policy is an actively moving target; **re-verify against current
browser release notes before Phase 3 implementation and again before each
major release** rather than trusting this table indefinitely.

* Safari and Firefox block unpartitioned third-party cookies **by default,
  today** — this is the baseline the design assumes, not an edge case.
* CHIPS is a Chromium-engine feature; Safari does not implement it.
  `TODO(spec): confirm current Firefox CHIPS support status at
  implementation time` — it has been in active development but support
  timing should be re-checked, not assumed.
* Storage Access API is implemented in Safari (where it originated as part
  of ITP), Firefox, and Chromium browsers, but grant heuristics (what counts
  as sufficient prior first-party interaction to auto-grant vs. prompt)
  differ per engine and are not part of the spec proper.
  `TODO(spec): validate current per-browser Storage Access API grant
  heuristics before relying on any auto-grant path; design for the
  prompt/explicit-gesture path as the baseline, not the auto-grant path.`
* Chrome's plans for deprecating unpartitioned third-party cookies by
  default have shifted more than once; the platform's design must not
  assume a specific enforcement date.
  `TODO(spec): re-check Chrome's current third-party cookie deprecation
  status before Phase 3, since this ADR intentionally avoids depending on
  it either way.`

### Consequences

* `bridge-protocol` (Phase 3) must define the message shapes for a tool to
  report "state could not be established" and to request the container
  escalate through the fallback chain — this is now a required part of that
  contract, not an afterthought.
* `container-ui` owns a visible degraded-mode UI; a tool must never be left
  in a silent broken state.
* The manifest's `security` block (`packages/manifest-schema`) should let a
  tool declare whether it needs third-party storage at all, so the
  container can skip straight to "no cookie needed" for the common case and
  only offer the CHIPS/Storage-Access/new-tab chain for tools that opt in.
* Because Option C avoids third-party cookies entirely for our own
  identity/session handoff, most learning objects built against
  `bridge-protocol` from the start should never need options A/B/D at all —
  those exist for interoperability with tools we don't fully control.

## More Information

* CHIPS (Cookies Having Independent Partitioned State) — `Partitioned`
  cookie attribute.
* Storage Access API — `document.requestStorageAccess()`.
* Safari Intelligent Tracking Prevention (ITP); Firefox Enhanced Tracking
  Protection / Total Cookie Protection.
* Related: ADR-001 (why the `id_token` itself never depends on a cookie).
