# Knowledge Graph

The knowledge graph structures the Algebra course as a property graph layered on top of
normalized Postgres tables. Canonical content (courses, modules, topics, learning objectives,
concepts, resources, assessment items) lives in its own relational table; the `GraphNode` and
`GraphEdge` tables form an overlay index that connects those rows with typed, directed, weighted
edges so the app can traverse prerequisites, unlock sequences, and validation checks without a
separate graph database.

Schema: `apps/api/prisma/schema.prisma`. Traversal helpers: `packages/knowledge-graph`. Shared
enum types: `packages/shared`. Seed example: `apps/api/prisma/seed.ts`.

## Node model

Every `GraphNode` is a thin pointer into a domain entity:

| Field | Meaning |
|---|---|
| `id` | Graph node id |
| `type` | `GraphNodeType` (see below) |
| `entityId` | Foreign key into the domain table for that type |
| `label` | Denormalized display name |
| `metadata` | JSON bag of denormalized fields for fast rendering (e.g. `difficulty`, `cognitiveLevel`) |

`(type, entityId)` is unique — one graph node per domain row.

### Node types (ontology classes)

| `GraphNodeType` | Backing entity | Represents |
|---|---|---|
| `COURSE` | `Course` | The whole course, e.g. "Algebra Foundations" |
| `MODULE` | `Module` | An ordered unit within a course, e.g. "Equations" |
| `TOPIC` | `Topic` | An ordered sub-unit within a module, e.g. "Two-Step Equations" |
| `LEARNING_OBJECTIVE` | `LearningObjective` | An atomic, assessable skill a learner masters (`code`, `cognitiveLevel`, `difficulty`, `estimatedMinutes`) — the primary unit the adaptive engine reasons about |
| `CONCEPT` | `Concept` | A reusable idea/vocabulary term (e.g. "inverse operation") that one or more learning objectives require, independent of course structure |
| `RESOURCE` | `Resource` | Teaching content (article, practice set, etc.) that instructs a learning objective |
| `ASSESSMENT_ITEM` | `AssessmentItem` | A question/prompt used to measure mastery of a learning objective |
| `MISCONCEPTION` | — | A named error pattern learners commonly exhibit, intended to be linked to remediation content (defined in the schema; not yet populated by the seed data) |

## Edge model

Every `GraphEdge` is `(sourceNodeId, targetNodeId, type, weight, metadata)`, always directed.
`weight` defaults to `1` and is used e.g. to carry ordering within a `CONTAINS` edge.

### Edge types (ontology relationships)

| `GraphEdgeType` | Direction (source → target) | Semantics |
|---|---|---|
| `CONTAINS` | `COURSE → MODULE → TOPIC → LEARNING_OBJECTIVE` | Structural composition/hierarchy. Defines the course's table of contents. |
| `REQUIRES_CONCEPT` | `LEARNING_OBJECTIVE → CONCEPT` | The LO's understanding depends on this concept. Concepts cut across the module/topic hierarchy (e.g. "inverse operation" is required by multiple LOs in different topics). |
| `DEPENDS_ON` | `LEARNING_OBJECTIVE → LEARNING_OBJECTIVE` | Prerequisite edge: the target LO must be mastered before the source LO is attempted. This is the edge the sequencing/gating logic walks. |
| `UNLOCKS` | `LEARNING_OBJECTIVE → LEARNING_OBJECTIVE` | The inverse of `DEPENDS_ON`, written symmetrically at seed time so "what does mastering X unlock?" is a direct outgoing-edge query instead of a reverse lookup. |
| `ASSESSES` | `ASSESSMENT_ITEM → LEARNING_OBJECTIVE` | This item measures mastery of the LO. |
| `TEACHES` | `RESOURCE → LEARNING_OBJECTIVE` | This resource instructs the LO. |
| `REMEDIATES` | *(reserved)* | Intended to connect remediation content back to a `MISCONCEPTION`, once misconception tagging is populated. |
| `RELATED_TO` | *(reserved)* | Generic, non-hierarchical lateral association (e.g. between sibling concepts or LOs) for future recommendation use, not yet emitted by the seed. |

## Worked example (from `apps/api/prisma/seed.ts`)

```
Course "Algebra Foundations"
 └─CONTAINS→ Module "Equations"
     └─CONTAINS→ Topic "Two-Step Equations"
         └─CONTAINS→ LO "ALG-EQ-003  Solve two-step equations"
                ├─REQUIRES_CONCEPT→ Concept "inverse operation"
                ├─REQUIRES_CONCEPT→ Concept "multi-step reasoning"
                ├─DEPENDS_ON→ LO "ALG-EQ-002  Solve one-step equations"
                └─(AssessmentItem "Solve 2x + 3 = 11")─ASSESSES→ LO "ALG-EQ-003"

LO "ALG-EQ-002" ─UNLOCKS→ LO "ALG-EQ-003"   (mirror of the DEPENDS_ON edge above)
```

`ALG-EQ-002` in turn `DEPENDS_ON` both `ALG-VAR-001` (variables) and `ALG-EQ-001` (inverse
operations), so the full prerequisite chain for two-step equations is:
`ALG-VAR-001 → ALG-EQ-001 → ALG-EQ-002 → ALG-EQ-003`.

## Graph queries (`packages/knowledge-graph`)

- **`getPrerequisitesForLo`** — follow `DEPENDS_ON` edges out of an LO node.
- **`getConceptsForLo`** — follow `REQUIRES_CONCEPT` edges out of an LO node.
- **`getUnlockedLos`** — follow `UNLOCKS` edges out of an LO node.
- **`getCandidateNextLos`** — LOs not yet mastered whose `DEPENDS_ON` prerequisites are *all*
  mastered; this is the core "what should the learner do next" rule.
- **`detectCircularDependencies`** — DFS over `DEPENDS_ON` edges restricted to
  `LEARNING_OBJECTIVE` nodes; the prerequisite graph must be a DAG.
- **`detectOrphanedLos`** — flags LO nodes with no `CONTAINS`, `DEPENDS_ON`, or `UNLOCKS` edge at
  all (unreachable from the course hierarchy and disconnected from sequencing).

## How mastery fits in

`LearnerMastery` (`masteryScore`, `confidenceScore`, `attemptCount`, `status`) is keyed by
`(learnerId, learningObjectiveId)`. It is not itself a graph node — it's per-learner state that
the recommendation engine joins against the graph: a learner's mastered-LO set is checked against
`DEPENDS_ON` edges (via `getCandidateNextLos`) to decide which learning objectives are eligible to
study next.

Score thresholds (`docs/LEARNING_FRAMEWORK.md`) drive the `MasteryStatus` an LO node's mastery
record settles into: `>= .85` → trending `MASTERED`, `.60–.85` → `PARTIAL`, `< .60` →
`PRACTICING`/`NEEDS_REVIEW`. When a prerequisite LO's mastery is below `.70`, the orchestration
engine (`packages/orchestration-engine`) walks the LO's `DEPENDS_ON` edges and emits a
`REMEDIATE_PREREQUISITE` recommendation pointing at the weak prerequisite instead of the LO itself
— the graph is what makes "which upstream node is actually blocking this learner" answerable.

## API / admin surface

- `GET /learning-objectives/:id/prerequisites` and `GET /learning-objectives/:id/concepts`
  (`apps/api/src/server.ts`) expose the traversal helpers above.
- `GET /admin/graph/validate` runs `detectCircularDependencies` and `detectOrphanedLos` and
  returns node/edge counts alongside any violations; rendered at `apps/web/src/app/admin/graph/page.tsx`.

## Known gaps

- `MISCONCEPTION` nodes and the `REMEDIATES` / `RELATED_TO` edge types are defined in the schema
  and shared types but not yet populated by the seed data or referenced by any query — they're
  reserved for tagging common learner errors and linking them to remediation content, and for
  lateral (non-hierarchical) recommendations.
- `seed.ts` hardcodes its own copies of the `GraphNodeType`/`GraphEdgeType` string unions instead
  of importing them from `@tutor/shared`, so the enum values must be kept in sync by hand.
