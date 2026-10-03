import { request, type FetchLike } from "@/api/http";
import type {
  EntrypointSignature,
  HealthResponse,
  OdooConnectionStatus,
  StartTraceCommand,
  TraceDetail,
  TraceListQuery,
  TracePage,
} from "@/api/types";

/** Short reads: the API answers quickly or something is wrong. */
export const DEFAULT_TIMEOUT_MS = 10_000;
/** POST /traces waits for Odoo; the backend allows up to 120 s. A little margin on top. */
export const START_TRACE_TIMEOUT_MS = 130_000;

export const DEFAULT_API_URL = "http://localhost:8000";

export interface ApiClientOptions {
  baseUrl?: string;
  fetch?: FetchLike;
}

export interface CallOptions {
  signal?: AbortSignal;
}

export type ApiClient = ReturnType<typeof createApiClient>;

/** Thin client for every documented endpoint. Errors are AppErrors (see errors.ts). */
export function createApiClient(options: ApiClientOptions = {}) {
  const baseUrl = options.baseUrl ?? import.meta.env.VITE_API_URL ?? DEFAULT_API_URL;
  const fetchFn: FetchLike = options.fetch ?? ((input, init) => fetch(input, init));
  const get = <T>(path: string, call: CallOptions & { query?: TraceListQuery } = {}) =>
    request<T>(fetchFn, baseUrl, "GET", path, {
      timeoutMs: DEFAULT_TIMEOUT_MS,
      query: call.query,
      signal: call.signal,
    });

  return {
    baseUrl,

    health: (call?: CallOptions) => get<HealthResponse>("health", call),

    odooStatus: (call?: CallOptions) => get<OdooConnectionStatus>("odoo/status", call),

    describeEntrypoint: (model: string, method: string, call?: CallOptions) =>
      get<EntrypointSignature>(
        `odoo/entrypoints/${encodeURIComponent(model)}/${encodeURIComponent(method)}`,
        call,
      ),

    listTraces: (query: TraceListQuery = {}, call?: CallOptions) =>
      get<TracePage>("traces", { ...call, query }),

    getTrace: (traceId: string, call?: CallOptions) =>
      get<TraceDetail>(`traces/${encodeURIComponent(traceId)}`, call),

    /** Synchronous: resolves once Odoo has finished. Cancel with call.signal. */
    startTrace: (command: StartTraceCommand, call?: CallOptions) =>
      request<TraceDetail>(fetchFn, baseUrl, "POST", "traces", {
        body: command,
        timeoutMs: START_TRACE_TIMEOUT_MS,
        signal: call?.signal,
      }),

    deleteTrace: (traceId: string, call?: CallOptions) =>
      request<undefined>(fetchFn, baseUrl, "DELETE", `traces/${encodeURIComponent(traceId)}`, {
        timeoutMs: DEFAULT_TIMEOUT_MS,
        signal: call?.signal,
      }),
  };
}
