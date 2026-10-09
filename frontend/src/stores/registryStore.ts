import { createStore } from "zustand/vanilla";

import type { AppError } from "@/api/errors";
import type { ModelDetail, ModelSummary } from "@/api/types";
import type { DataSource } from "@/datasource/types";
import { isAbort, toAppError, type Phase } from "@/stores/async";

export interface RegistryState {
  /** Every model of the connected Odoo; null until loaded. */
  models: ModelSummary[] | null;
  phase: Phase;
  error: AppError | null;
  /** Load the list (once; `force` loads again). */
  load: (force?: boolean) => Promise<void>;

  /** The model shown in detail. */
  model: string | null;
  detail: ModelDetail | null;
  detailPhase: Phase;
  detailError: AppError | null;
  /** Show a model; a newer call supersedes an older one still loading. */
  describe: (model: string) => Promise<void>;
}

export function createRegistryStore(source: DataSource) {
  let describing: AbortController | null = null;
  const cache = new Map<string, ModelDetail>();

  return createStore<RegistryState>()((set, get) => ({
    models: null,
    phase: "idle",
    error: null,
    async load(force = false) {
      if (!force && (get().phase === "ready" || get().phase === "loading")) return;
      set({ phase: "loading", error: null });
      try {
        const { models } = await source.listModels();
        set({ models, phase: "ready" });
      } catch (error) {
        set({ phase: "error", error: toAppError(error) });
      }
    },

    model: null,
    detail: null,
    detailPhase: "idle",
    detailError: null,
    async describe(model) {
      describing?.abort();
      const cached = cache.get(model);
      if (cached) {
        describing = null;
        set({ model, detail: cached, detailPhase: "ready", detailError: null });
        return;
      }
      const controller = new AbortController();
      describing = controller;
      set({ model, detail: null, detailPhase: "loading", detailError: null });
      try {
        const detail = await source.describeModel(model, { signal: controller.signal });
        cache.set(model, detail);
        if (describing === controller) set({ detail, detailPhase: "ready" });
      } catch (error) {
        if (describing === controller && !isAbort(error)) {
          set({ detailPhase: "error", detailError: toAppError(error) });
        }
      }
    },
  }));
}
