import type { DataSource } from "@/datasource/types";
import { createConnectionStore } from "@/stores/connectionStore";
import { createCurrentTraceStore } from "@/stores/currentTraceStore";
import { createRegistryStore } from "@/stores/registryStore";
import { createReplayStore } from "@/stores/replayStore";
import { createTraceListStore } from "@/stores/traceListStore";

export type AppStores = ReturnType<typeof createAppStores>;

/**
 * All stores of the app, wired to one data source. Switching between API and fixtures
 * means creating a new set of stores for the other source.
 */
export function createAppStores(source: DataSource) {
  const connection = createConnectionStore(source);
  const traceList = createTraceListStore(source);
  const currentTrace = createCurrentTraceStore(source);
  const replay = createReplayStore();
  const registry = createRegistryStore(source);

  // A newly shown trace starts its replay at the first step.
  currentTrace.subscribe((state, previous) => {
    if (state.index !== previous.index) replay.getState().reset(state.index?.ordered.length ?? 0);
  });
  // A newly recorded run appears in the list.
  currentTrace.subscribe((state, previous) => {
    if (previous.run.phase === "running" && state.run.phase === "idle" && state.trace) {
      void traceList.getState().load();
    }
  });

  return { source, connection, traceList, currentTrace, replay, registry };
}
