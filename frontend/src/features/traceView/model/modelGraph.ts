import type { TraceIndex } from "@/lib/replay/traceIndex";

export interface ModelNode {
  model: string;
  /** Modules whose implementations ran on this model, most frequent first. */
  modules: string[];
  calls: number;
  changes: number;
  /** Position of the first step on this model. */
  firstPosition: number;
  /** Distance from the entrypoint's model along calls (layout column). */
  layer: number;
}

export interface ModelEdge {
  source: string;
  target: string;
  calls: number;
}

export interface ModelGraph {
  nodes: ModelNode[];
  edges: ModelEdge[];
}

/**
 * Models of the run and who calls whom: an edge A → B means a step on A called a step on
 * B. Calls within one model are counted on the node, not drawn.
 */
export function modelGraph(index: TraceIndex): ModelGraph {
  const nodes = new Map<string, ModelNode & { moduleCounts: Map<string, number> }>();
  const edges = new Map<string, ModelEdge>();

  index.ordered.forEach((step, position) => {
    let node = nodes.get(step.model);
    if (!node) {
      node = {
        model: step.model,
        modules: [],
        calls: 0,
        changes: 0,
        firstPosition: position,
        layer: 0,
        moduleCounts: new Map(),
      };
      nodes.set(step.model, node);
    }
    node.calls += 1;
    node.changes += step.changes.length;
    const module = step.module ?? "core";
    node.moduleCounts.set(module, (node.moduleCounts.get(module) ?? 0) + 1);

    const parent = step.parent_id === null ? undefined : index.byId.get(step.parent_id);
    if (parent && parent.model !== step.model) {
      const key = `${parent.model}→${step.model}`;
      const edge = edges.get(key);
      if (edge) edge.calls += 1;
      else edges.set(key, { source: parent.model, target: step.model, calls: 1 });
    }
  });

  // Layers: breadth-first from the models of the top-level steps.
  const outgoing = new Map<string, string[]>();
  for (const edge of edges.values()) {
    const list = outgoing.get(edge.source) ?? [];
    list.push(edge.target);
    outgoing.set(edge.source, list);
  }
  const layer = new Map<string, number>();
  const queue: string[] = [];
  for (const root of index.roots) {
    const model = index.byId.get(root)?.model;
    if (model !== undefined && !layer.has(model)) {
      layer.set(model, 0);
      queue.push(model);
    }
  }
  for (let i = 0; i < queue.length; i++) {
    const model = queue[i] ?? "";
    for (const target of outgoing.get(model) ?? []) {
      if (!layer.has(target)) {
        layer.set(target, (layer.get(model) ?? 0) + 1);
        queue.push(target);
      }
    }
  }

  return {
    nodes: [...nodes.values()]
      .map(({ moduleCounts, ...node }) => ({
        ...node,
        modules: [...moduleCounts].sort((a, b) => b[1] - a[1]).map(([name]) => name),
        layer: layer.get(node.model) ?? 0,
      }))
      .sort((a, b) => a.firstPosition - b.firstPosition),
    edges: [...edges.values()],
  };
}

export interface Point {
  x: number;
  y: number;
}

/** Columns by layer, rows by first appearance: a readable left-to-right call direction. */
export function layoutLayers(
  nodes: readonly ModelNode[],
  spacing: { column: number; row: number },
): Map<string, Point> {
  const rowInLayer = new Map<number, number>();
  const positions = new Map<string, Point>();
  for (const node of nodes) {
    const row = rowInLayer.get(node.layer) ?? 0;
    rowInLayer.set(node.layer, row + 1);
    positions.set(node.model, { x: node.layer * spacing.column, y: row * spacing.row });
  }
  return positions;
}
