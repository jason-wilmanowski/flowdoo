import { AppError } from "@/api/errors";
import type { OdooConnectionStatus, StartTraceCommand, TraceSummary } from "@/api/types";
import {
  FIXTURE_NAMES,
  loadFixture,
  loadRegistryFixture,
  type RegistryFixture,
} from "@/datasource/fixtures/catalog";
import type { CallOptions, DataSource, Trace } from "@/datasource/types";
import type { TracePayload } from "@/generated/trace";

/** Shown wherever fixture mode could be mistaken for a real Odoo. */
export const FIXTURE_MODE_NOTICE =
  "Fixture mode: traces come from shared/fixtures; no backend or Odoo is connected.";

// Same text as the backend's answer to dry_run=false in its default configuration.
const NON_DRY_RUN_REFUSED =
  "dry_run=false is disabled. It writes to the Odoo database and is only allowed when explicitly enabled for a development setup.";

export interface FixtureDataSourceOptions {
  /** Artificial latency per call, so loading states are visible. 0 in tests. */
  delayMs?: number;
  now?: () => Date;
}

function wait(ms: number, signal?: AbortSignal): Promise<void> {
  if (signal?.aborted) return Promise.reject(new AppError("aborted", "The request was cancelled."));
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(new AppError("aborted", "The request was cancelled."));
      },
      { once: true },
    );
  });
}

function traceFromPayload(payload: TracePayload): Trace {
  const roots = payload.steps.filter((step) => step.parent_id === null);
  const durationMs = roots.reduce((sum, step) => sum + step.duration_ms, 0);
  const finished = new Date(new Date(payload.started_at).getTime() + durationMs);
  return {
    id: payload.trace_id,
    status: "succeeded",
    entrypoint_model: payload.entrypoint.model,
    entrypoint_method: payload.entrypoint.method,
    dry_run: payload.dry_run,
    schema_version: payload.schema_version,
    odoo_version: payload.odoo_version,
    started_at: payload.started_at,
    finished_at: finished.toISOString(),
    created_at: payload.started_at,
    error: null,
    payload,
  };
}

function summaryOf(trace: Trace): TraceSummary {
  const { payload, ...summary } = trace;
  return summary;
}

/** A recording that failed before Odoo answered: status failed, no payload. */
function failedExample(): Trace {
  return {
    id: "00000000-0000-4000-8000-0000000000f1",
    status: "failed",
    entrypoint_model: "account.move",
    entrypoint_method: "action_post",
    dry_run: true,
    schema_version: null,
    odoo_version: null,
    started_at: "2026-10-03T11:58:00+00:00",
    finished_at: "2026-10-03T11:58:00.120000+00:00",
    created_at: "2026-10-03T11:58:00+00:00",
    error: "Cannot reach Odoo: ConnectError (fixture: example of a failed recording)",
    payload: null,
  };
}

/**
 * DataSource on shared/fixtures, for working without backend and Odoo. It simulates the
 * API's behavior (list filters and paging, 404s, the synchronous start of a run, the
 * default refusal of dry_run=false) on the four fixture traces plus one failed recording.
 */
export function createFixtureDataSource(options: FixtureDataSourceOptions = {}): DataSource {
  const delayMs = options.delayMs ?? 400;
  const now = options.now ?? (() => new Date());
  let traces: Map<string, Trace> | null = null;

  async function store(): Promise<Map<string, Trace>> {
    if (!traces) {
      const payloads = await Promise.all(FIXTURE_NAMES.map(loadFixture));
      traces = new Map([...payloads.map(traceFromPayload), failedExample()].map((t) => [t.id, t]));
    }
    return traces;
  }

  let registry: Promise<RegistryFixture> | null = null;
  const loadRegistry = () => (registry ??= loadRegistryFixture());

  async function find(traceId: string, call?: CallOptions): Promise<Trace> {
    await wait(delayMs, call?.signal);
    const trace = (await store()).get(traceId);
    if (!trace) throw new AppError("http", `Trace ${traceId} not found`, { status: 404 });
    return trace;
  }

  return {
    kind: "fixtures",

    async odooStatus(call) {
      await wait(delayMs, call?.signal);
      const status: OdooConnectionStatus = {
        configured: true,
        url: null,
        database: null,
        reachable: true,
        server_version: "19.0",
        version_supported: true,
        authenticated: true,
        user_login: null,
        addon_installed: true,
        addon_state: "installed",
        tracing_enabled: true,
        recorder_available: true,
        user_is_admin: true,
        database_neutralized: null,
        ok: true,
        problems: [],
        warnings: [FIXTURE_MODE_NOTICE],
      };
      return status;
    },

    async describeEntrypoint(model, method, call) {
      await wait(delayMs, call?.signal);
      const known = [...(await store()).values()].find(
        (t) => t.payload?.entrypoint.model === model && t.payload.entrypoint.method === method,
      );
      const entry = known?.payload?.steps.find((s) => s.parent_id === null && s.seq === 1);
      if (!known || !entry) {
        throw new AppError(
          "http",
          `The method '${model}.${method}' is not in the fixtures. ${FIXTURE_MODE_NOTICE}`,
          { status: 404 },
        );
      }
      return {
        model,
        method,
        model_level: false,
        module: entry.module,
        summary: null,
        parameters: [],
      };
    },

    async listModels(call) {
      await wait(delayMs, call?.signal);
      return { models: (await loadRegistry()).models };
    },

    async describeModel(model, call) {
      await wait(delayMs, call?.signal);
      const fixture = await loadRegistry();
      const detail = fixture.details[model];
      if (detail) return detail;
      const known = fixture.models.some((m) => m.model === model);
      throw new AppError(
        "http",
        known
          ? `Details of ${model} are not in the fixtures: in fixture mode only ${String(Object.keys(fixture.details).length)} central models have them.`
          : `The model '${model}' does not exist`,
        { status: 404 },
      );
    },

    async listTraces(query = {}, call) {
      await wait(delayMs, call?.signal);
      const limit = query.limit ?? 50;
      const offset = query.offset ?? 0;
      const items = [...(await store()).values()]
        .filter((t) => !query.status || t.status === query.status)
        .filter((t) => !query.entrypoint_model || t.entrypoint_model === query.entrypoint_model)
        .filter((t) => !query.entrypoint_method || t.entrypoint_method === query.entrypoint_method)
        .sort((a, b) => b.created_at.localeCompare(a.created_at));
      return {
        items: items.slice(offset, offset + limit).map(summaryOf),
        total: items.length,
        limit,
        offset,
      };
    },

    getTrace: (traceId, call) => find(traceId, call),

    async startTrace(command: StartTraceCommand, call) {
      if (!command.dry_run) {
        throw new AppError("http", NON_DRY_RUN_REFUSED, { status: 403 });
      }
      await wait(delayMs * 3, call?.signal); // a run takes longer than a read
      const all = await store();
      const template = [...all.values()]
        .filter(
          (t) =>
            t.payload?.entrypoint.model === command.entrypoint_model &&
            t.payload.entrypoint.method === command.entrypoint_method,
        )
        .sort((a, b) => (b.payload?.steps.length ?? 0) - (a.payload?.steps.length ?? 0))[0];
      const id = crypto.randomUUID();
      const startedAt = now().toISOString();
      let trace: Trace;
      if (template?.payload) {
        const payload: TracePayload = {
          ...template.payload,
          trace_id: id,
          started_at: startedAt,
          entrypoint: {
            model: command.entrypoint_model,
            method: command.entrypoint_method,
            record_ids: command.record_ids,
            context: command.context ?? {},
            kwargs: command.kwargs ?? {},
          },
        };
        trace = { ...traceFromPayload(payload), created_at: startedAt };
      } else {
        trace = {
          ...failedExample(),
          id,
          entrypoint_model: command.entrypoint_model,
          entrypoint_method: command.entrypoint_method,
          started_at: startedAt,
          finished_at: startedAt,
          created_at: startedAt,
          error: `Fixture mode can only run the entrypoints in shared/fixtures (sale.order.action_confirm). ${FIXTURE_MODE_NOTICE}`,
        };
      }
      all.set(id, trace);
      return trace;
    },

    async deleteTrace(traceId, call) {
      await find(traceId, call);
      (await store()).delete(traceId);
    },
  };
}
