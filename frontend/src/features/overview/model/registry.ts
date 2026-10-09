import type { ModelSummary } from "@/api/types";

/** Group name for models defined by the ORM itself (no module). */
export const CORE = "core";

export interface ModelFilter {
  query: string;
  /** Defining module, or null for all. */
  module: string | null;
  showAbstract: boolean;
  showTransient: boolean;
}

export const DEFAULT_FILTER: ModelFilter = {
  query: "",
  module: null,
  showAbstract: true,
  showTransient: false,
};

/** Models matching the filter; every query word must appear in the name or description. */
export function filterModels(models: readonly ModelSummary[], filter: ModelFilter): ModelSummary[] {
  const words = filter.query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  return models.filter((model) => {
    if (!filter.showAbstract && model.abstract) return false;
    if (!filter.showTransient && model.transient) return false;
    if (filter.module !== null && (model.module ?? CORE) !== filter.module) return false;
    const text = `${model.model} ${model.description ?? ""}`.toLowerCase();
    return words.every((word) => text.includes(word));
  });
}

/** Models grouped by the module that defined them, groups and models sorted by name. */
export function groupByModule(models: readonly ModelSummary[]): [string, ModelSummary[]][] {
  const groups = new Map<string, ModelSummary[]>();
  for (const model of models) {
    const module = model.module ?? CORE;
    const group = groups.get(module);
    if (group) group.push(model);
    else groups.set(module, [model]);
  }
  return [...groups]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([module, list]) => [module, [...list].sort((a, b) => a.model.localeCompare(b.model))]);
}

/** Defining modules, sorted, for the module filter. */
export function modulesOf(models: readonly ModelSummary[]): string[] {
  return [...new Set(models.map((m) => m.module ?? CORE))].sort();
}

export interface IncomingRelation {
  from: string;
  field: string;
  type: string;
}

/** Relational fields of other models that point to `model`. */
export function incomingRelations(
  models: readonly ModelSummary[],
  model: string,
): IncomingRelation[] {
  const result: IncomingRelation[] = [];
  for (const other of models) {
    if (other.model === model) continue;
    for (const relation of other.relations) {
      if (relation.target === model) {
        result.push({ from: other.model, field: relation.field, type: relation.type });
      }
    }
  }
  return result.sort((a, b) => a.from.localeCompare(b.from) || a.field.localeCompare(b.field));
}
