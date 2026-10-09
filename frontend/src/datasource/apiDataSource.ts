import type { ApiClient } from "@/api/client";
import type { TraceDetail } from "@/api/types";
import type { DataSource, Trace } from "@/datasource/types";
import type { TracePayload } from "@/generated/trace";

/** The one place where an API payload is read as a TracePayload (see Trace). */
function asTrace(detail: TraceDetail): Trace {
  return { ...detail, payload: detail.payload as unknown as TracePayload | null };
}

export function createApiDataSource(client: ApiClient): DataSource {
  return {
    kind: "api",
    odooStatus: (call) => client.odooStatus(call),
    describeEntrypoint: (model, method, call) => client.describeEntrypoint(model, method, call),
    listModels: (call) => client.listModels(call),
    describeModel: (model, call) => client.describeModel(model, call),
    listTraces: (query, call) => client.listTraces(query, call),
    getTrace: async (traceId, call) => asTrace(await client.getTrace(traceId, call)),
    startTrace: async (command, call) => asTrace(await client.startTrace(command, call)),
    deleteTrace: async (traceId, call) => {
      await client.deleteTrace(traceId, call);
    },
  };
}
