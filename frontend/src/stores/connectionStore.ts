import { createStore } from "zustand/vanilla";

import type { AppError } from "@/api/errors";
import type { OdooConnectionStatus } from "@/api/types";
import type { DataSource } from "@/datasource/types";
import { toAppError, type Phase } from "@/stores/async";

export interface ConnectionState {
  /** Answer of GET /odoo/status (problems and warnings are shown as they are). */
  status: OdooConnectionStatus | null;
  phase: Phase;
  error: AppError | null;
  refresh: () => Promise<void>;
}

export function createConnectionStore(source: DataSource) {
  return createStore<ConnectionState>()((set) => ({
    status: null,
    phase: "idle",
    error: null,
    async refresh() {
      set({ phase: "loading", error: null });
      try {
        set({ status: await source.odooStatus(), phase: "ready" });
      } catch (error) {
        set({ phase: "error", error: toAppError(error) });
      }
    },
  }));
}
