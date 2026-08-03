# Architecture Decision Records

MADR format (https://adr.github.io/madr/). One file per decision, numbered
sequentially, never renumbered or deleted — a superseded decision gets a new
ADR that says so and links back.

| ADR | Title |
| --- | --- |
| [0001](0001-launch-protocol.md) | Launch protocol is OIDC third-party login initiation, not a bare tool URL |
| [0002](0002-iframe-rendering-and-cookie-strategy.md) | Iframe rendering and third-party cookie strategy |
| [0003](0003-xapi-actor-identity.md) | xAPI actor identity uses a pseudonymous `account` IFI |

0001–0003 are the mandatory foundational ADRs for the Learning Object
Registry and Runtime Container. Later phases add ADRs here as significant
decisions come up (e.g. `ltijs` vs. a direct LTI 1.3 implementation in
Phase 2).
