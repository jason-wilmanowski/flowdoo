import type { Step } from "@/generated/trace";
import type { TraceIndex } from "@/lib/replay/traceIndex";
import type { TreeRow } from "@/ui";

/**
 * The call tree as a developer reads it:
 *
 * - A **super chain** is one call. When `sale_stock.write` calls `super()`, the recorder
 *   records `sale.write` as its child; here both are layers of one node.
 * - Expanding a chain shows its layers as a stack (one row per implementation, in MRO
 *   order); the calls each layer made sit under that layer (before or after `super()`
 *   matters for overrides). A call with one implementation shows its calls directly.
 * - A node is **relevant** when it or something below it changed field values or failed.
 *   Only relevant paths start expanded.
 * - Runs of irrelevant sibling calls (tax and rounding helpers, …) are folded into one
 *   **group** row.
 *
 * All steps stay reachable; nothing is dropped.
 */

/** Folding starts at this many consecutive irrelevant sibling calls. */
export const GROUP_MIN = 2;
const GROUP_PREFIX = "group:";
const LAYER_PREFIX = "layer:";

export interface CallNode {
  /** Id of the first layer (the most derived implementation). */
  id: string;
  /** Implementations the call ran through, most derived first. */
  chain: Step[];
  /** Child node ids in seq order. */
  children: string[];
  /** Parent node id (null at the top). */
  parentId: string | null;
  /** The layer of the parent's chain that made this call. */
  calledFrom: Step | null;
  /** Field changes written by the layers themselves. */
  ownChanges: number;
  failed: boolean;
  /** Steps in this node and below (layers included). */
  stepCount: number;
  /** This node or something below it changed values or failed. */
  relevant: boolean;
  /** Something below this node changed values or failed. */
  relevantBelow: boolean;
}

export interface CallGroup {
  id: string;
  /** The model when all members run on the same one, else null. */
  model: string | null;
  members: string[];
  parentId: string | null;
  stepCount: number;
}

/** One implementation in a super chain, shown as a row when the chain is expanded. */
export interface CallLayer {
  /** `layer:<step id>` */
  id: string;
  step: Step;
  nodeId: string;
  /** Something the layer called changed values or failed. */
  relevantBelow: boolean;
}

export interface CallTree {
  nodes: ReadonlyMap<string, CallNode>;
  groups: ReadonlyMap<string, CallGroup>;
  layers: ReadonlyMap<string, CallLayer>;
  /** Children as displayed: node ids and group ids, per parent (null = top level). */
  display: ReadonlyMap<string | null, readonly string[]>;
  /** Display parent of a node or group (a node inside a group has the group as parent). */
  displayParent: ReadonlyMap<string, string | null>;
  /** Any step id (also inner layers) -> its node id. */
  nodeOfStep: ReadonlyMap<string, string>;
}

export const isGroupId = (id: string) => id.startsWith(GROUP_PREFIX);
export const isLayerId = (id: string) => id.startsWith(LAYER_PREFIX);
export const layerId = (stepId: string) => `${LAYER_PREFIX}${stepId}`;

/** `child` is the next implementation of the same call (reached through `super()`). */
export function isSuperCall(parent: Step, child: Step): boolean {
  if (parent.model !== child.model || parent.method !== child.method) return false;
  if (parent.mro_position !== null && child.mro_position !== null) {
    return child.mro_position > parent.mro_position;
  }
  return parent.calls_super === true;
}

export function buildCallTree(index: TraceIndex): CallTree {
  // 1. the next layer of every step that continues a super chain
  const nextLayer = new Map<string, string>();
  const continuation = new Set<string>();
  for (const step of index.ordered) {
    for (const childId of index.childrenById.get(step.id) ?? []) {
      const child = index.byId.get(childId);
      if (child && isSuperCall(step, child)) {
        nextLayer.set(step.id, childId);
        continuation.add(childId);
        break;
      }
    }
  }

  // 2. nodes: one per chain head
  const nodes = new Map<string, CallNode>();
  const nodeOfStep = new Map<string, string>();
  for (const head of index.ordered) {
    if (continuation.has(head.id)) continue;
    const chain: Step[] = [];
    for (let id: string | undefined = head.id; id !== undefined; id = nextLayer.get(id)) {
      const layer = index.byId.get(id);
      if (!layer) break;
      chain.push(layer);
      nodeOfStep.set(layer.id, head.id);
    }
    nodes.set(head.id, {
      id: head.id,
      chain,
      children: [],
      parentId: null,
      calledFrom: null,
      ownChanges: chain.reduce((sum, layer) => sum + layer.changes.length, 0),
      failed: chain.some((layer) => layer.error !== null),
      stepCount: chain.length,
      relevant: false,
      relevantBelow: false,
    });
  }

  // 3. children: calls made by any layer, except the next layer itself
  const roots: string[] = [];
  for (const node of nodes.values()) {
    const head = node.chain[0];
    const parentStep = head && head.parent_id !== null ? index.byId.get(head.parent_id) : undefined;
    const parentNode = parentStep ? nodeOfStep.get(parentStep.id) : undefined;
    if (parentStep && parentNode !== undefined) {
      node.parentId = parentNode;
      node.calledFrom = parentStep;
      nodes.get(parentNode)?.children.push(node.id);
    } else {
      roots.push(node.id);
    }
  }
  const seqOf = (id: string) => index.byId.get(id)?.seq ?? 0;
  for (const node of nodes.values()) node.children.sort((a, b) => seqOf(a) - seqOf(b));
  roots.sort((a, b) => seqOf(a) - seqOf(b));

  // 4. relevance and sizes, bottom-up (children start after their parent)
  const byLateFirst = [...nodes.values()].sort((a, b) => seqOf(b.id) - seqOf(a.id));
  for (const node of byLateFirst) {
    for (const childId of node.children) {
      const child = nodes.get(childId);
      if (!child) continue;
      node.stepCount += child.stepCount;
      if (child.relevant) node.relevantBelow = true;
    }
    node.relevant = node.ownChanges > 0 || node.failed || node.relevantBelow;
  }

  // 5. fold runs of irrelevant calls on one model
  const groups = new Map<string, CallGroup>();
  const display = new Map<string | null, string[]>();
  const displayParent = new Map<string, string | null>();
  const fold = (parentId: string | null, children: readonly string[]) => {
    const shown: string[] = [];
    let i = 0;
    while (i < children.length) {
      const first = nodes.get(children[i] ?? "");
      let j = i;
      if (first && !first.relevant) {
        while (j < children.length) {
          const candidate = nodes.get(children[j] ?? "");
          if (!candidate || candidate.relevant) break;
          j++;
        }
      }
      if (first && j - i >= GROUP_MIN) {
        const members = children.slice(i, j);
        const id = `${GROUP_PREFIX}${first.id}`;
        const models = new Set(members.map((m) => nodes.get(m)?.chain[0]?.model));
        groups.set(id, {
          id,
          model: models.size === 1 ? (first.chain[0]?.model ?? null) : null,
          members,
          parentId,
          stepCount: members.reduce((sum, m) => sum + (nodes.get(m)?.stepCount ?? 0), 0),
        });
        display.set(id, members);
        for (const member of members) displayParent.set(member, id);
        displayParent.set(id, parentId);
        shown.push(id);
        i = j;
      } else {
        const id = children[i] ?? "";
        displayParent.set(id, parentId);
        shown.push(id);
        i++;
      }
    }
    display.set(parentId, shown);
  };
  // 6. chains show their layers; each layer holds the calls it made
  const layers = new Map<string, CallLayer>();
  fold(null, roots);
  for (const node of nodes.values()) {
    if (node.chain.length < 2) {
      fold(node.id, node.children);
      continue;
    }
    const layerIds: string[] = [];
    for (const step of node.chain) {
      const id = layerId(step.id);
      const calls = node.children.filter((child) => nodes.get(child)?.calledFrom?.id === step.id);
      layers.set(id, {
        id,
        step,
        nodeId: node.id,
        relevantBelow: calls.some((child) => nodes.get(child)?.relevant ?? false),
      });
      displayParent.set(id, node.id);
      layerIds.push(id);
      fold(id, calls);
    }
    display.set(node.id, layerIds);
  }

  return { nodes, groups, layers, display, displayParent, nodeOfStep };
}

/**
 * Expanded unless the user toggled it: calls and layers with something relevant below
 * (their calls, not their own writes); groups closed.
 */
export function expandedByDefault(tree: CallTree, id: string): boolean {
  if (isGroupId(id)) return false;
  const layer = tree.layers.get(id);
  if (layer) return layer.relevantBelow;
  return tree.nodes.get(id)?.relevantBelow ?? false;
}

/** Expansion = default, flipped for every id in `toggled`. */
export function isExpanded(tree: CallTree, toggled: ReadonlySet<string>, id: string): boolean {
  return expandedByDefault(tree, id) !== toggled.has(id);
}

function hasChildren(tree: CallTree, id: string): boolean {
  return (tree.display.get(id)?.length ?? 0) > 0;
}

/** Visible rows, depth-first in seq order. */
export function visibleCallRows(tree: CallTree, toggled: ReadonlySet<string>): TreeRow[] {
  const rows: TreeRow[] = [];
  const stack: [string, number, string | null][] = [...(tree.display.get(null) ?? [])]
    .reverse()
    .map((id) => [id, 0, null]);
  for (let entry = stack.pop(); entry; entry = stack.pop()) {
    const [id, depth, parentId] = entry;
    const children = tree.display.get(id) ?? [];
    const expanded = isExpanded(tree, toggled, id);
    rows.push({ id, depth, parentId, hasChildren: children.length > 0, expanded });
    if (expanded) {
      for (let i = children.length - 1; i >= 0; i--) stack.push([children[i] ?? "", depth + 1, id]);
    }
  }
  return rows;
}

/** The row id that shows a step: its layer row inside a chain, else its call. */
export function displayIdOfStep(tree: CallTree, stepId: string): string | null {
  const node = tree.nodeOfStep.get(stepId);
  if (node === undefined) return null;
  return tree.layers.has(layerId(stepId)) ? layerId(stepId) : node;
}

/** Display ancestors of a row, nearest first. */
export function displayAncestors(tree: CallTree, id: string): string[] {
  const result: string[] = [];
  let parent = tree.displayParent.get(id) ?? null;
  while (parent !== null) {
    result.push(parent);
    parent = tree.displayParent.get(parent) ?? null;
  }
  return result;
}

/** The visible row that stands for a step: its node, or the outermost collapsed ancestor. */
export function rowForStep(
  tree: CallTree,
  toggled: ReadonlySet<string>,
  stepId: string,
): string | null {
  const own = displayIdOfStep(tree, stepId);
  if (own === null) return null;
  let row = own;
  for (const ancestor of displayAncestors(tree, own)) {
    if (!isExpanded(tree, toggled, ancestor)) row = ancestor;
  }
  return row;
}

/** Toggles so that the step's own row is visible (its display ancestors expanded). */
export function revealStep(
  tree: CallTree,
  toggled: ReadonlySet<string>,
  stepId: string,
): ReadonlySet<string> {
  const own = displayIdOfStep(tree, stepId);
  if (own === null) return toggled;
  const closed = displayAncestors(tree, own).filter((a) => !isExpanded(tree, toggled, a));
  if (closed.length === 0) return toggled;
  const next = new Set(toggled);
  for (const id of closed) {
    if (next.has(id)) next.delete(id);
    else next.add(id);
  }
  return next;
}

/** Toggles that expand every row with children. */
export function expandAll(tree: CallTree): Set<string> {
  const toggled = new Set<string>();
  for (const id of [...tree.nodes.keys(), ...tree.groups.keys(), ...tree.layers.keys()]) {
    if (hasChildren(tree, id) && !expandedByDefault(tree, id)) toggled.add(id);
  }
  return toggled;
}

/** The step a row stands for (a layer: its implementation; a group: its first member). */
export function firstStepOfRow(tree: CallTree, rowId: string): string | null {
  const layer = tree.layers.get(rowId);
  if (layer) return layer.step.id;
  const group = tree.groups.get(rowId);
  return group ? (group.members[0] ?? null) : tree.nodes.has(rowId) ? rowId : null;
}

/** Logical call path to a step: node ids from the top down to the step's node. */
export function callPath(tree: CallTree, stepId: string): string[] {
  const path: string[] = [];
  for (
    let id: string | null = tree.nodeOfStep.get(stepId) ?? null;
    id !== null;
    id = tree.nodes.get(id)?.parentId ?? null
  ) {
    path.push(id);
  }
  return path.reverse();
}

/** The chain a step belongs to (all layers of its call). */
export function chainOfStep(tree: CallTree, stepId: string): Step[] {
  const node = tree.nodeOfStep.get(stepId);
  return node === undefined ? [] : (tree.nodes.get(node)?.chain ?? []);
}
