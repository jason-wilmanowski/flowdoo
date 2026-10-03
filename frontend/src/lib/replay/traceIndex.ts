import type { Step, TracePayload } from "@/generated/trace";

/**
 * Lookup structures for one trace, built once per loaded trace (O(n log n)).
 *
 * The order of `payload.steps` carries no meaning: replay order is `seq`, the call tree
 * comes from `parent_id`. Positions below are indexes into `ordered` (seq order).
 */
export interface TraceIndex {
  /** Steps in replay order (ascending seq). */
  readonly ordered: readonly Step[];
  readonly byId: ReadonlyMap<string, Step>;
  /** Step id -> position in `ordered`. */
  readonly positionById: ReadonlyMap<string, number>;
  /** Parent id (null = top level) -> child ids in seq order. */
  readonly childrenById: ReadonlyMap<string | null, readonly string[]>;
  /** Step id -> depth in the call tree (top level = 0). */
  readonly depthById: ReadonlyMap<string, number>;
  readonly roots: readonly string[];
}

const EMPTY: readonly string[] = [];

export function indexTrace(payload: Pick<TracePayload, "steps">): TraceIndex {
  const ordered = [...payload.steps].sort((a, b) => a.seq - b.seq);
  const byId = new Map<string, Step>();
  const positionById = new Map<string, number>();
  ordered.forEach((step, position) => {
    byId.set(step.id, step);
    positionById.set(step.id, position);
  });

  const children = new Map<string | null, string[]>();
  for (const step of ordered) {
    // A parent that is not in the trace makes the step a root instead of losing it.
    const parent = step.parent_id !== null && byId.has(step.parent_id) ? step.parent_id : null;
    let list = children.get(parent);
    if (!list) {
      list = [];
      children.set(parent, list);
    }
    list.push(step.id);
  }

  // Depth by walking the tree from the roots (iterative: deep call chains are normal).
  const depthById = new Map<string, number>();
  const roots = children.get(null) ?? [];
  const stack: [string, number][] = roots.map((id) => [id, 0]);
  for (let entry = stack.pop(); entry; entry = stack.pop()) {
    const [id, depth] = entry;
    if (depthById.has(id)) continue; // defensive: a cycle cannot loop forever
    depthById.set(id, depth);
    for (const child of children.get(id) ?? EMPTY) stack.push([child, depth + 1]);
  }

  return { ordered, byId, positionById, childrenById: children, depthById, roots };
}

export function childrenOf(index: TraceIndex, stepId: string | null): readonly string[] {
  return index.childrenById.get(stepId) ?? EMPTY;
}

/** Ids from the top-level step down to `stepId` (inclusive); empty for an unknown id. */
export function pathTo(index: TraceIndex, stepId: string): string[] {
  const path: string[] = [];
  let current = index.byId.get(stepId);
  const seen = new Set<string>();
  while (current && !seen.has(current.id)) {
    seen.add(current.id);
    path.push(current.id);
    current = current.parent_id === null ? undefined : index.byId.get(current.parent_id);
  }
  return path.reverse();
}
