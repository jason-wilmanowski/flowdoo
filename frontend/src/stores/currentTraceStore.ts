import { createStore } from "zustand/vanilla";

import type { AppError } from "@/api/errors";
import type { StartTraceCommand } from "@/api/types";
import type { DataSource, Trace } from "@/datasource/types";
import { indexTrace, type TraceIndex } from "@/lib/replay/traceIndex";
import { isAbort, toAppError, type Phase } from "@/stores/async";

/** State of a trace run started from the UI (POST /traces is synchronous). */
export interface RunState {
  phase: "idle" | "running" | "error";
  command: StartTraceCommand | null;
  error: AppError | null;
}

export interface CurrentTraceState {
  traceId: string | null;
  trace: Trace | null;
  /** Lookup structures for the payload; null without a trace or payload. */
  index: TraceIndex | null;
  phase: Phase;
  error: AppError | null;
  run: RunState;
  /** Show a stored trace; a newer call supersedes an older one still loading. */
  load: (traceId: string) => Promise<void>;
  /** Record a new run; resolves with the stored trace (status succeeded or failed). */
  start: (command: StartTraceCommand) => Promise<Trace | null>;
  cancelStart: () => void;
  clear: () => void;
}

const IDLE_RUN: RunState = { phase: "idle", command: null, error: null };

function withIndex(trace: Trace) {
  return { trace, index: trace.payload ? indexTrace(trace.payload) : null };
}

export function createCurrentTraceStore(source: DataSource) {
  let loading: AbortController | null = null;
  let running: AbortController | null = null;

  return createStore<CurrentTraceState>()((set) => ({
    traceId: null,
    trace: null,
    index: null,
    phase: "idle",
    error: null,
    run: IDLE_RUN,

    async load(traceId) {
      loading?.abort();
      const controller = new AbortController();
      loading = controller;
      set({ traceId, trace: null, index: null, phase: "loading", error: null });
      try {
        const trace = await source.getTrace(traceId, { signal: controller.signal });
        if (loading === controller) set({ ...withIndex(trace), phase: "ready" });
      } catch (error) {
        if (loading === controller && !isAbort(error)) {
          set({ phase: "error", error: toAppError(error) });
        }
      }
    },

    async start(command) {
      running?.abort();
      const controller = new AbortController();
      running = controller;
      set({ run: { phase: "running", command, error: null } });
      try {
        const trace = await source.startTrace(command, { signal: controller.signal });
        if (running !== controller) return null;
        loading?.abort();
        set({
          ...withIndex(trace),
          traceId: trace.id,
          phase: "ready",
          error: null,
          run: IDLE_RUN,
        });
        return trace;
      } catch (error) {
        if (running === controller) {
          set({
            run: isAbort(error) ? IDLE_RUN : { phase: "error", command, error: toAppError(error) },
          });
        }
        return null;
      } finally {
        if (running === controller) running = null;
      }
    },

    cancelStart() {
      running?.abort();
    },

    clear() {
      loading?.abort();
      set({ traceId: null, trace: null, index: null, phase: "idle", error: null });
    },
  }));
}
