import type { TraceIndex } from "@/lib/replay/traceIndex";
import type { TreeRow } from "@/ui";

/** Visible rows of the call tree in seq order; children of collapsed steps are left out. */
export function visibleRows(index: TraceIndex, collapsed: ReadonlySet<string>): TreeRow[] {
  const rows: TreeRow[] = [];
  const stack = [...index.roots].reverse();
  for (let id = stack.pop(); id !== undefined; id = stack.pop()) {
    const step = index.byId.get(id);
    if (!step) continue;
    const children = index.childrenById.get(id) ?? [];
    const expanded = !collapsed.has(id);
    const parent =
      step.parent_id !== null && index.byId.has(step.parent_id) ? step.parent_id : null;
    rows.push({
      id,
      depth: index.depthById.get(id) ?? 0,
      parentId: parent,
      hasChildren: children.length > 0,
      expanded,
    });
    if (expanded) for (let i = children.length - 1; i >= 0; i--) stack.push(children[i] ?? "");
  }
  return rows;
}

/** Ancestors of a step, nearest first. */
export function ancestorsOf(index: TraceIndex, id: string): string[] {
  const result: string[] = [];
  let parent = index.byId.get(id)?.parent_id ?? null;
  while (parent !== null && index.byId.has(parent)) {
    result.push(parent);
    parent = index.byId.get(parent)?.parent_id ?? null;
  }
  return result;
}

/** Collapsed set without the ancestors of `id`, so the step is visible. */
export function revealStep(
  index: TraceIndex,
  collapsed: ReadonlySet<string>,
  id: string,
): ReadonlySet<string> {
  const hidden = ancestorsOf(index, id).filter((ancestor) => collapsed.has(ancestor));
  if (hidden.length === 0) return collapsed;
  const next = new Set(collapsed);
  for (const ancestor of hidden) next.delete(ancestor);
  return next;
}

/** Collapse every step deeper than `depth` that has children (a readable start for big traces). */
export function collapseBelow(index: TraceIndex, depth: number): Set<string> {
  const collapsed = new Set<string>();
  for (const [id, children] of index.childrenById) {
    if (id !== null && children.length > 0 && (index.depthById.get(id) ?? 0) >= depth) {
      collapsed.add(id);
    }
  }
  return collapsed;
}
