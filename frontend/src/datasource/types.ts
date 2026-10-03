import type {
  EntrypointSignature,
  OdooConnectionStatus,
  StartTraceCommand,
  TraceDetail,
  TraceListQuery,
  TracePage,
} from "@/api/types";
import type { TracePayload } from "@/generated/trace";

export type DataSourceKind = "api" | "fixtures";

export interface CallOptions {
  signal?: AbortSignal;
}

/**
 * A trace with its payload typed by the trace schema. The API types the payload as an open
 * object; the backend has validated it against the same schema before storing it.
 */
export type Trace = Omit<TraceDetail, "payload"> & { payload: TracePayload | null };

/**
 * Where the stores get their data from. Errors are AppErrors (src/api/errors.ts), in both
 * implementations, so the UI handles them the same way.
 */
export interface DataSource {
  readonly kind: DataSourceKind;
  odooStatus(call?: CallOptions): Promise<OdooConnectionStatus>;
  describeEntrypoint(
    model: string,
    method: string,
    call?: CallOptions,
  ): Promise<EntrypointSignature>;
  listTraces(query?: TraceListQuery, call?: CallOptions): Promise<TracePage>;
  getTrace(traceId: string, call?: CallOptions): Promise<Trace>;
  /** Resolves once the run is recorded (status succeeded or failed). */
  startTrace(command: StartTraceCommand, call?: CallOptions): Promise<Trace>;
  deleteTrace(traceId: string, call?: CallOptions): Promise<void>;
}
