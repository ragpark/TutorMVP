export type NodeLike = { id: string; type: string; entityId: string; label: string };
export type EdgeLike = {
  sourceNodeId: string;
  targetNodeId: string;
  type: string;
  weight?: number;
};
const byEntity = (nodes: NodeLike[], entityId: string) =>
  nodes.find((n) => n.entityId === entityId);
export function getPrerequisitesForLo(nodes: NodeLike[], edges: EdgeLike[], loId: string) {
  const n = byEntity(nodes, loId);
  if (!n) return [];
  return edges
    .filter((e) => e.sourceNodeId === n.id && e.type === 'DEPENDS_ON')
    .map((e) => nodes.find((x) => x.id === e.targetNodeId))
    .filter(Boolean) as NodeLike[];
}
export function getConceptsForLo(nodes: NodeLike[], edges: EdgeLike[], loId: string) {
  const n = byEntity(nodes, loId);
  if (!n) return [];
  return edges
    .filter((e) => e.sourceNodeId === n.id && e.type === 'REQUIRES_CONCEPT')
    .map((e) => nodes.find((x) => x.id === e.targetNodeId))
    .filter(Boolean) as NodeLike[];
}
export function getUnlockedLos(nodes: NodeLike[], edges: EdgeLike[], loId: string) {
  const n = byEntity(nodes, loId);
  if (!n) return [];
  return edges
    .filter((e) => e.sourceNodeId === n.id && e.type === 'UNLOCKS')
    .map((e) => nodes.find((x) => x.id === e.targetNodeId))
    .filter(Boolean) as NodeLike[];
}
export function getCandidateNextLos(
  nodes: NodeLike[],
  edges: EdgeLike[],
  masteredIds: Set<string>,
) {
  return nodes
    .filter((n) => n.type === 'LEARNING_OBJECTIVE' && !masteredIds.has(n.entityId))
    .filter((n) =>
      getPrerequisitesForLo(nodes, edges, n.entityId).every((p) => masteredIds.has(p.entityId)),
    );
}
export function detectCircularDependencies(nodes: NodeLike[], edges: EdgeLike[]) {
  const dep = edges.filter((e) => e.type === 'DEPENDS_ON');
  const cycles: string[][] = [];
  const visit = (id: string, path: string[]) => {
    if (path.includes(id)) {
      cycles.push([...path.slice(path.indexOf(id)), id]);
      return;
    }
    dep.filter((e) => e.sourceNodeId === id).forEach((e) => visit(e.targetNodeId, [...path, id]));
  };
  nodes.filter((n) => n.type === 'LEARNING_OBJECTIVE').forEach((n) => visit(n.id, []));
  return cycles;
}
export function detectOrphanedLos(nodes: NodeLike[], edges: EdgeLike[]) {
  return nodes.filter(
    (n) =>
      n.type === 'LEARNING_OBJECTIVE' &&
      !edges.some(
        (e) =>
          (e.sourceNodeId === n.id || e.targetNodeId === n.id) &&
          ['CONTAINS', 'DEPENDS_ON', 'UNLOCKS'].includes(e.type),
      ),
  );
}
