# ADR-003: xAPI actor identity uses a pseudonymous `account` IFI, never `mbox`/`mbox_sha1sum`

* Status: accepted
* Date: 2026-08-03

## Context and Problem Statement

Every xAPI statement requires an Actor with exactly one Inverse Functional
Identifier (IFI): `mbox`, `mbox_sha1sum`, `openid`, or `account`. The
`xapi-gateway` stamps the actor on every statement (tools never talk to the
LRS directly). The learner cohort includes minors. What IFI do we use, and
how do we make it safe to persist and to forward to a configurable external
LRS, while still allowing legitimate re-identification when we are legally
or operationally required to (safeguarding, FERPA/COPPA data-subject
requests)?

## Decision Drivers

* The cohort includes minors — we must not emit anything that is, or trivially
  reduces to, a directly identifying credential (email address) by default.
* Statements are forwarded to a **configurable external LRS** (Phase 4); we do
  not control what that system does with an IFI once it leaves our boundary,
  so the IFI itself must be safe to hand to a third party.
  `TODO(spec): confirm the external LRS forwarding contract (Phase 4) never
  bypasses this pseudonymization step — the gateway must pseudonymize before
  forwarding, not rely on the receiving LRS to do so.`
  * Pseudonymization must still be reversible **inside our boundary** —
    safeguarding escalation and legal data-subject requests require us to be
    able to answer "which learner is this."
  * Tenants must not be correlatable to each other through the actor
    identifier — two different platform deployments must not be able to tell
    whether they share a learner.
* Compromise of one signing/HMAC key must not retroactively deanonymize
  historical statements signed with a different key, and must not force
  re-pseudonymizing history to rotate.

## Considered Options

* **A — `mbox`**: the actor's email address as `mailto:...`. Rejected
  outright: this is direct PII, not pseudonymous at all, and many minors in
  the cohort will not have a stable personal email address to begin with —
  the IFI wouldn't even be reliably available, let alone safe.
* **B — `mbox_sha1sum`**: a SHA1 hash of a `mailto:` IRI. Rejected outright:
  hashing an email address is not meaningful pseudonymization. Email
  addresses have low entropy and are enumerable/dictionary-attackable — an
  external LRS (or anyone it leaks to) can feasibly recover the original
  address by hashing candidate emails and comparing. It also inherits
  `mbox`'s availability problem for minors.
* **C — `openid`**: an OpenID Connect identifier URI. Rejected: this ties the
  actor identifier to an external identity provider's durable subject
  identifier, which is exactly the kind of externally-correlatable, durable
  identifier we're trying to avoid handing to a third-party LRS.
* **D — `account`**: an `{ homePage, name }` pair, both platform-defined. This
  is the only IFI type where **we** define both the namespace (`homePage`)
  and the identifier (`name`), so we control what "the identifier" actually
  encodes.

## Decision Outcome

Chosen option: **D — `account`**, with a platform-owned `homePage` and an
opaque, per-tenant HMAC-derived `name`. Options A and B are rejected
outright per the task brief, not merely deprioritized: they must never
appear in `xapi-gateway` code, tests, or fixtures.

### Shape

```
actor.account.homePage = "https://xapi.<platform-domain>/actors"   // constant, platform-owned
actor.account.name     = HMAC-SHA256(tenantKey_v<N>, `${tenantId}:${issuer}:${lti_sub}`)
                          -> base32/hex-encoded opaque string
```

* `homePage` is a single, constant, platform-owned URI — not the tenant's
  domain, not the tool's domain, not the learner's LMS domain. xAPI compares
  actors by the `(homePage, name)` pair, so keeping `homePage` constant and
  putting all the entropy in `name` keeps the identifier stable and
  comparable across statements for the same learner within a tenant, without
  ever exposing a platform, tenant, or tool hostname as part of the identity
  itself.
* `name` is derived from the durable, already-pseudonymous-relative-to-the-
  outside-world identifier we already have from the LTI launch — the
  `(issuer, sub)` pair from the validated `id_token` (`packages/lti-core`) —
  **not** from anything like a name or email.
* The HMAC key is **per tenant** and **versioned** (`tenantKey_v<N>`). Two
  different tenants derive different `name` values for what might otherwise
  be the same underlying person, so tenants cannot correlate learners
  against each other even by comparing statement dumps.
* HMAC is one-way; `xapi-gateway` additionally persists a restricted mapping
  table (`pseudonym -> {tenantId, issuer, sub, keyVersion}`), written at
  first-derivation time, so that re-identification inside our boundary does
  not depend on brute-forcing the HMAC.
  `TODO(spec): finalize the mapping table's schema and access-control model
  in the Phase 4 xapi-gateway implementation; this ADR fixes the identity
  *shape* and the *procedure*, not the SQL.`

### Key rotation

* HMAC keys are generated and stored per tenant, versioned (`v1`, `v2`, ...),
  and rotated on a schedule (recommend: annually, or immediately on
  suspected key compromise).
* Rotation **never retroactively re-derives past pseudonyms.** Statements
  already written keep the `name` value (and recorded `keyVersion`) computed
  under the key that was active when they were pseudonymized. Only newly
  derived pseudonyms use the new key.
* Because the mapping table records `keyVersion` alongside each mapping,
  re-identification of historical statements looks up the historical key by
  version rather than assuming the current key applies.
* Retiring a key version (rather than merely superseding it) is a distinct,
  deliberate operation from rotation: it means the mapping rows for that
  version are deleted, which makes every pseudonym derived under that key
  permanently unresolvable inside our boundary too — this is the tool to use
  when a data-subject erasure request applies to an entire key epoch, not
  routine rotation.

### Re-identification procedure

* Re-identification (pseudonym → real learner) is **never** exposed by
  `xapi-gateway`'s public statement/query API (Phase 4's "minimal statement
  query API" operates on pseudonymous actors only).
* It is performed only through a separate, privileged internal operation
  that takes `(pseudonym, tenantId)`, looks up `keyVersion` and the original
  `(issuer, sub)` from the restricted mapping table, and is:
  * gated to specific, named operational reasons (safeguarding escalation,
    FERPA/COPPA/GDPR data-subject request, legal process),
  * logged/audited on every access (who, when, why, which pseudonym), and
  * never automatic or bulk — one lookup is one recorded decision, not a
    batch export.
  `TODO(spec): the exact access-control mechanism (who is authorized, what
  the audit log schema is) belongs to the Phase 4 xapi-gateway design, not
  this ADR; this ADR fixes that the capability must exist, must be narrow,
  and must be audited.`

### Consequences

* `xapi-gateway` must derive the actor itself, from the validated LTI launch
  identity handed to it via `container-ui` (per the launch chain in
  ADR-001) — tools never supply `sub`/email/name and never see the
  pseudonym-to-real-identity mapping.
* The per-tenant HMAC key material is a secret and must be provisioned via
  environment variables per ADR/Phase 5 conventions (documented in
  `.env.example`), never committed, never logged.
* Because `name` is derived only from `(tenantId, issuer, sub)`, a learner
  who is launched into the same tool from two different resource links (or
  two different courses) within the same tenant gets the **same** pseudonym
  — this is intentional, since mastery/progress tracking (save-state,
  resume) needs a stable actor per learner per tenant. Cross-tenant stability
  is intentionally **not** provided.
* Forwarding to an external LRS (Phase 4) forwards the already-pseudonymized
  actor — the external LRS never receives `(issuer, sub)`, an email, or any
  other directly identifying value.

## More Information

* ADL xAPI specification — Actor/Agent object, Inverse Functional
  Identifiers (`mbox`, `mbox_sha1sum`, `openid`, `account`).
  `TODO(spec): cite the exact xAPI 2.0 section number in
  packages/manifest-schema or xapi-gateway code comments once that code is
  written, rather than in this ADR.`
* Related: ADR-001 (the `(issuer, sub)` pair this design pseudonymizes comes
  from the validated LTI `id_token`).
