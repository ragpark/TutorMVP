# ADR-001: Launch protocol is OIDC third-party login initiation, not a bare tool URL

* Status: accepted
* Date: 2026-08-03

## Context and Problem Statement

The registry must resolve a single, stable, product-team-facing identifier
(`GET /lo/{urn}` or `GET /lo/{urn}@{version}`) to a running instance of a
learning object, whether that object is hosted by us or by a third party.
Product teams want to build and deploy tools independently, with no shared
runtime and no build-time coupling to the platform. What should the platform
send the browser to when a learner (or an external LMS) launches a learning
object by URN?

## Decision Drivers

* Identity, role, and context (course, class, resource link) must travel with
  the launch — the tool cannot be trusted to look these up itself, and we do
  not want tools querying a platform API with ambient credentials.
* The learner cohort includes minors; we must not leak durable, re-identifiable
  personal data (name, email, a stable learner ID) to third-party tools by
  default.
* We must support both directions: we act as an LTI Platform launching tools
  we don't control, and we act as an LTI Tool launched by external LMSs
  (Google Classroom, Canvas, Moodle, Teams) that already speak LTI 1.3.
* The launch must be replay-resistant and must not depend on the tool
  performing its own login/session bootstrap.
* No bespoke protocol — product teams should be able to build against a
  spec that has existing client libraries, documentation, and prior art in
  the edtech ecosystem (1EdTech / IMS Global LTI Advantage).

## Considered Options

* **Bare tool URL** — `GET /lo/{urn}` 302-redirects straight to the tool's
  launch URL, optionally with query-string parameters (`userId`, `role`,
  `contextId`, ...) appended by the registry.
* **Signed platform-issued token in a query string or header** — a bespoke
  bearer token (e.g. a short-lived JWT) appended to the tool URL, verified by
  the tool against our JWKS.
* **LTI 1.3 OIDC third-party login initiation** — the resolver redirects the
  browser into the standard LTI 1.3 / IMS Security Framework OIDC
  third-party-initiated login flow: an OIDC Login Initiation request to the
  tool, an Authentication Request back to our Platform OIDC endpoint, and a
  signed `id_token` delivered to the tool's redirect URI via `form_post`.

## Decision Outcome

Chosen option: **LTI 1.3 OIDC third-party login initiation**, because it is
the only option that gives us identity, context, roles, resource link, and a
return path as first-class, spec-defined, cryptographically verifiable
concepts, while remaining interoperable with every LMS product teams will
eventually need to plug into (Google Classroom, Canvas, Moodle, Teams all
speak LTI 1.3 Advantage) and every tool a product team might buy or build.

### What is lost with a bare tool URL

A bare redirect (`GET /lo/{urn}` → `302 https://tool.example.com/launch?...`)
looks simpler, but silently drops everything a learning object actually
needs to behave correctly and safely:

* **No verifiable identity.** Any query parameter (`userId=123`) is just a
  string the tool must trust unauthenticated, or worse, that a learner can
  edit in the address bar. There is no signature, no audience binding, no
  expiry.
* **No context.** "Which course, which class, which assignment, which
  resource link is this?" has no standard shape. Every tool invents its own
  query parameters, which is exactly the shared-schema coupling this
  architecture exists to avoid.
* **No roles.** Whether the launching user is a learner, an instructor, or a
  TA — information the tool needs to decide what UI to render — has nowhere
  canonical to live.
* **No replay protection.** A bare URL with a static or predictable token can
  be bookmarked, shared, or replayed. There is no `nonce`, no single-use
  enforcement, no `state` round-trip to prove the redirect chain wasn't
  tampered with.
* **No return path.** LTI's `deep_link_return_url` / platform return
  navigation is a spec-defined concept; a bare URL has no standard way for
  the tool to say "the learner is done, send them back to the platform, with
  or without a score."
* **No AGS/NRPS wiring.** Grade passback and roster access are LTI Advantage
  services keyed off the launch (`ags` and `nrps` claims, line item and
  resource-link IDs). A bare launch has no place for these service endpoint
  URLs and scoped access tokens to be communicated.

Rejecting the bare URL is also why option 2 (bespoke bearer token) fails: it
re-invents a strict subset of LTI 1.3 — signed identity, replay protection —
badly, with no interoperability with any external LMS, and no reusable
client libraries. We would own a protocol nobody else in edtech speaks.

### How this plays out for the two directions

* **Platform role** (we launch internal or third-party tools): the stable
  `/lo/{urn}` URL is resolved by `registry-api`, which redirects the browser
  to `launch-gateway`'s OIDC Login Initiation endpoint for that tool. The
  standard third-party-initiated login flow runs from there: Login
  Initiation → Authentication Request → signed `id_token` delivered by
  `form_post` to the tool's (or `container-ui`'s) redirect URI, carrying an
  `LtiResourceLinkRequest` message.
* **Tool role** (an external LMS launches one of our learning objects):
  the external Platform performs the same flow against our
  `launch-gateway` acting as an LTI Tool — it receives the external
  Platform's Login Initiation request, redirects to that Platform's
  Authentication endpoint, and receives back a signed `id_token` we validate
  against that Platform's JWKS (issuer, audience, nonce, expiry — see
  ADR/spec notes in `packages/lti-core`).

TODO(spec): the exact claim names used for `LtiResourceLinkRequest` (e.g.
`https://purl.imsglobal.org/spec/lti/claim/*`) are implemented and verified
against the 1EdTech LTI 1.3 Core specification in `packages/lti-core`, not
guessed here — see that package's inline spec citations.

### Consequences

* Every learning object, including ones we host ourselves, is launched
  through the same OIDC flow as third-party tools — there is no "internal
  fast path" that skips identity/context. This costs an extra redirect
  round-trip on every launch but keeps the security model uniform and
  testable once.
* `launch-gateway` must implement both Platform and Tool roles of LTI 1.3
  Advantage (OIDC login initiation, JWKS, Deep Linking, AGS, NRPS) — see
  Phase 2.
* Product teams building tools must implement (or use a library for) LTI 1.3
  Tool-side launch validation, not a bespoke query-string contract. This is
  documented in `docs/spec/tool-authoring-guide.md` (Phase 3).
* Iframe-embedding and third-party cookie implications of completing this
  flow inside an iframe are significant enough to warrant their own decision
  — see ADR-002.

## More Information

* 1EdTech (IMS Global) *Security Framework* — OpenID Connect Launch Flow
  (third-party initiated login), the normative basis for this decision.
* 1EdTech *LTI 1.3 Core* specification — resource link launch message and
  claims.
* 1EdTech *LTI Advantage* — Deep Linking, Assignment and Grade Services
  (AGS), Names and Role Provisioning Services (NRPS).
