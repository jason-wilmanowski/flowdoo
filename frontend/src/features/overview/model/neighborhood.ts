import type { ModelSummary } from "@/api/types";

import { incomingRelations } from "./registry";

export type NodeRole = "center" | "target" | "source" | "parent" | "more";

export interface NeighborNode {
  id: string;
  role: NodeRole;
  /** Model name, or the "+ N more" text of a summary node. */
  model: string;
  module: string | null;
  /** How it is linked, short, e.g. "via partner_id +1" (all fields are in the details). */
  detail: string;
  x: number;
  y: number;
}

export interface NeighborEdge {
  id: string;
  source: string;
  target: string;
  /** Field names of a relation; "inherits" for inheritance. */
  label: string;
  kind: "relation" | "inherits";
}

export interface NeighborOptions {
  outgoing: boolean;
  incoming: boolean;
  parents: boolean;
  /** Most models per side; the rest is one "+ N more" node. */
  limit: number;
}

export const DEFAULT_NEIGHBOR_OPTIONS: NeighborOptions = {
  outgoing: true,
  incoming: true,
  parents: false,
  limit: 12,
};

export const SPACING = { column: 380, row: 76, inheritColumn: 300, inheritGap: 190 };

interface Link {
  model: string;
  fields: string[];
}

function collect(entries: { model: string; field: string }[]): Link[] {
  const byModel = new Map<string, string[]>();
  for (const { model, field } of entries) {
    const fields = byModel.get(model);
    if (fields) fields.push(field);
    else byModel.set(model, [field]);
  }
  return [...byModel]
    .map(([model, fields]) => ({ model, fields }))
    .sort((a, b) => b.fields.length - a.fields.length || a.model.localeCompare(b.model));
}

function column(
  links: Link[],
  role: "target" | "source" | "parent",
  x: number,
  limit: number,
  moduleOf: (model: string) => string | null,
): NeighborNode[] {
  const shown = links.slice(0, limit);
  const nodes: NeighborNode[] = shown.map((link) => ({
    id: `${role}:${link.model}`,
    role,
    model: link.model,
    module: moduleOf(link.model),
    detail:
      link.fields.length === 1
        ? `via ${link.fields[0] ?? ""}`
        : `via ${link.fields[0] ?? ""} +${String(link.fields.length - 1)}`,
    x,
    y: 0,
  }));
  if (links.length > limit) {
    nodes.push({
      id: `more:${role}`,
      role: "more",
      model: `+ ${String(links.length - limit)} more`,
      module: null,
      detail:
        role === "target" ? "linked models" : role === "source" ? "models linking here" : "parents",
      x,
      y: 0,
    });
  }
  // centre the column vertically around the selected model
  nodes.forEach((node, i) => {
    node.y = (i - (nodes.length - 1) / 2) * SPACING.row;
  });
  return nodes;
}

/**
 * The selected model with what it links to (right), what links to it (left) and, on
 * request, the models it inherits from (above). Several fields to the same model become
 * one node and one edge. Self references are left out of the picture (see the details).
 */
export function neighborhood(
  models: readonly ModelSummary[],
  center: string,
  options: NeighborOptions,
): { nodes: NeighborNode[]; edges: NeighborEdge[] } {
  const byName = new Map(models.map((m) => [m.model, m]));
  const selected = byName.get(center);
  const moduleOf = (model: string) => byName.get(model)?.module ?? null;
  const nodes: NeighborNode[] = [
    {
      id: `center:${center}`,
      role: "center",
      model: center,
      module: selected?.module ?? null,
      detail: selected?.description ?? "",
      x: 0,
      y: 0,
    },
  ];
  const edges: NeighborEdge[] = [];
  if (!selected) return { nodes, edges };

  const link = (node: NeighborNode, fields: string, toCenter: boolean) => {
    if (node.role === "more") return;
    edges.push({
      id: `${node.id}->${center}`,
      source: toCenter ? node.id : `center:${center}`,
      target: toCenter ? `center:${center}` : node.id,
      label: fields,
      kind: node.role === "parent" ? "inherits" : "relation",
    });
  };

  if (options.outgoing) {
    const targets = collect(
      selected.relations
        .filter((r) => r.target !== center)
        .map((r) => ({ model: r.target, field: r.field })),
    );
    for (const node of column(targets, "target", SPACING.column, options.limit, moduleOf)) {
      nodes.push(node);
      link(node, targets.find((t) => t.model === node.model)?.fields.join(", ") ?? "", false);
    }
  }
  if (options.incoming) {
    const sources = collect(
      incomingRelations(models, center).map((r) => ({ model: r.from, field: r.field })),
    );
    for (const node of column(sources, "source", -SPACING.column, options.limit, moduleOf)) {
      nodes.push(node);
      link(node, sources.find((t) => t.model === node.model)?.fields.join(", ") ?? "", true);
    }
  }
  if (options.parents && selected.parents.length > 0) {
    const parents = selected.parents.map((model) => ({ model, fields: ["inherits"] }));
    const row = column(parents, "parent", 0, options.limit, moduleOf);
    // a row of its own above everything else, so relation columns never cover it
    const top = Math.min(0, ...nodes.map((node) => node.y));
    row.forEach((node, i) => {
      node.x = (i - (row.length - 1) / 2) * SPACING.inheritColumn;
      node.y = top - SPACING.inheritGap;
      node.detail = "inherited";
      link(node, "inherits", true);
    });
    nodes.push(...row);
  }
  return { nodes, edges };
}
