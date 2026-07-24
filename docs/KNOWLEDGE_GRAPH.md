# Knowledge Graph

The MVP graph uses PostgreSQL `GraphNode` and `GraphEdge` tables. Node types include course, module, topic, learning objective, concept, resource, assessment item, and misconception. Edge types include contains, requires concept, depends on, unlocks, assesses, teaches, remediates, and related to.

Validation checks detect circular `DEPENDS_ON` paths and orphaned LOs without meaningful graph edges. Query examples are implemented in `packages/knowledge-graph`: prerequisites for an LO, concepts for an LO, unlocked LOs, candidate next LOs, cycle detection, and orphan detection.
