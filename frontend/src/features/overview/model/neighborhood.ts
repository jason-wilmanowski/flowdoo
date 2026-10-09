import type { ModelSummary } from "@/api/types";

import { incomingRelations } from "./registry";

export type NodeRole = "center" | "target" | "source" | "parent" | "more";

export interface NeighborNode {
  id: string;
  role: NodeRole;
  /** Model name, or the "+ N more" text of a summary node. */
  model: string;
  module: string | null;
  /** Field names that link it, e.g. "partner_id, partner_invoice_id". */
  detail: string;
  x: number;
  y: number;
}

export interface NeighborEdge {
  id: string;
  source: string;
  target: string;
  label: string;
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

export const SPACING = { column: 380, row: 76 };

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
    detail: link.fields.join(", "),
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

  const link = (node: NeighborNode, label: string, toCenter: boolean) => {
    if (node.role === "more") return;
    edges.push({
      id: `${node.id}->${center}`,
      source: toCenter ? node.id : `center:${center}`,
      target: toCenter ? `center:${center}` : node.id,
      label,
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
      link(node, node.detail, false);
    }
  }
  if (options.incoming) {
    const sources = collect(
      incomingRelations(models, center).map((r) => ({ model: r.from, field: r.field })),
    );
    for (const node of column(sources, "source", -SPACING.column, options.limit, moduleOf)) {
      nodes.push(node);
      link(node, node.detail, true);
    }
  }
  if (options.parents && selected.parents.length > 0) {
    const parents = selected.parents.map((model) => ({ model, fields: ["inherits"] }));
    const row = column(parents, "parent", 0, options.limit, moduleOf);
    // one row above the selected model instead of a column
    row.forEach((node, i) => {
      node.x = (i - (row.length - 1) / 2) * (SPACING.column * 0.75);
      node.y = -SPACING.row * 2.5;
      node.detail = "inherited";
      link(node, "inherits", true);
    });
    nodes.push(...row);
  }
  return { nodes, edges };
}
