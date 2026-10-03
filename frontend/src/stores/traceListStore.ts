import { createStore } from "zustand/vanilla";

import type { AppError } from "@/api/errors";
import type { TraceListQuery, TracePage } from "@/api/types";
import type { DataSource } from "@/datasource/types";
import { toAppError, type Phase } from "@/stores/async";

export interface TraceListState {
  query: TraceListQuery;
  page: TracePage | null;
  phase: Phase;
  error: AppError | null;
  /** Load with a new query (merged into the current one) or reload the current one. */
  load: (query?: TraceListQuery) => Promise<void>;
  remove: (traceId: string) => Promise<void>;
}

export function createTraceListStore(source: DataSource) {
  let request = 0;
  return createStore<TraceListState>()((set, get) => ({
    query: {},
    page: null,
    phase: "idle",
    error: null,
    async load(query) {
      const next = query ? { ...get().query, ...query } : get().query;
      const mine = ++request;
      set({ query: next, phase: "loading", error: null });
      try {
        const page = await source.listTraces(next);
        if (mine === request) set({ page, phase: "ready" });
      } catch (error) {
        if (mine === request) set({ phase: "error", error: toAppError(error) });
      }
    },
    async remove(traceId) {
      try {
        await source.deleteTrace(traceId);
      } catch (error) {
        set({ error: toAppError(error) });
        return;
      }
      await get().load();
    },
  }));
}
