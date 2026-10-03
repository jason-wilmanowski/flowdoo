// Names for the generated API types (src/generated/api.ts). Aliases only: the shapes come
// from the backend's OpenAPI document, never written by hand.
import type { components, operations } from "@/generated/api";

type Schemas = components["schemas"];

export type TraceStatus = Schemas["TraceStatus"];
export type TraceSummary = Schemas["TraceSummary"];
export type TraceDetail = Schemas["TraceDetail"];
export type TracePage = Schemas["TracePage"];
export type StartTraceCommand = Schemas["StartTraceCommand"];
export type OdooConnectionStatus = Schemas["OdooConnectionStatus"];
export type EntrypointSignature = Schemas["EntrypointSignature"];
export type EntrypointParameter = Schemas["EntrypointParameter"];
export type HealthResponse = Schemas["HealthResponse"];

/** Query parameters of GET /traces (all optional). */
export type TraceListQuery = NonNullable<
  operations["list_traces_traces_get"]["parameters"]["query"]
>;
