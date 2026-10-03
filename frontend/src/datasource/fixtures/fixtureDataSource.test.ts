import { AppError } from "@/api/errors";
import type { StartTraceCommand } from "@/api/types";
import {
  createFixtureDataSource,
  FIXTURE_MODE_NOTICE,
} from "@/datasource/fixtures/fixtureDataSource";

const RECORDED = "22585514-6fae-4c9b-96ee-3f431ba1035a";
const ERROR_FIXTURE = "3f2b8c1e-6d4a-4c1e-9b7a-1a2b3c4d5e03";
const FAILED_EXAMPLE = "00000000-0000-4000-8000-0000000000f1";

const CONFIRM: StartTraceCommand = {
  entrypoint_model: "sale.order",
  entrypoint_method: "action_confirm",
  record_ids: [9],
  dry_run: true,
};

async function failure(promise: Promise<unknown>): Promise<AppError> {
  try {
    await promise;
  } catch (error) {
    if (error instanceof AppError) return error;
    throw error;
  }
  throw new Error("expected the call to fail");
}

describe("fixture data source", () => {
  const source = () => createFixtureDataSource({ delayMs: 0 });

  it("is marked as fixture mode", async () => {
    const status = await source().odooStatus();

    expect(source().kind).toBe("fixtures");
    expect(status.ok).toBe(true);
    expect(status.warnings).toEqual([FIXTURE_MODE_NOTICE]);
  });

  it("lists the four fixtures and a failed recording, newest first", async () => {
    const page = await source().listTraces();

    expect(page.total).toBe(5);
    expect(page.items.map((t) => t.created_at)).toEqual(
      [...page.items.map((t) => t.created_at)].sort().reverse(),
    );
    expect(page.items.every((t) => !("payload" in t))).toBe(true);
    expect(page.items.find((t) => t.id === FAILED_EXAMPLE)?.status).toBe("failed");
  });

  it("filters and pages like the API", async () => {
    const failed = await source().listTraces({ status: "failed" });
    const confirm = await source().listTraces({
      entrypoint_model: "sale.order",
      entrypoint_method: "action_confirm",
    });
    const page = await source().listTraces({ limit: 2, offset: 2 });

    expect(failed.items.map((t) => t.id)).toEqual([FAILED_EXAMPLE]);
    expect(confirm.total).toBe(4);
    expect(page).toMatchObject({ total: 5, limit: 2, offset: 2 });
    expect(page.items).toHaveLength(2);
  });

  it("returns a trace with its payload", async () => {
    const trace = await source().getTrace(RECORDED);

    expect(trace.status).toBe("succeeded");
    expect(trace.payload?.steps).toHaveLength(879);
    expect(trace.entrypoint_model).toBe("sale.order");
    expect(trace.schema_version).toBe("0.2.0");
  });

  it("keeps recording status and Odoo exception apart", async () => {
    const trace = await source().getTrace(ERROR_FIXTURE);

    expect(trace.status).toBe("succeeded");
    expect(trace.error).toBeNull();
    expect(trace.payload?.error?.type).toBe("odoo.exceptions.UserError");
  });

  it("answers unknown ids with 404", async () => {
    const error = await failure(source().getTrace("nope"));

    expect(error.status).toBe(404);
    expect(error.message).toBe("Trace nope not found");
  });

  it("starts a known entrypoint as a new trace from the recorded fixture", async () => {
    const data = source();

    const trace = await data.startTrace({ ...CONFIRM, kwargs: { note: "x" } });

    expect(trace.status).toBe("succeeded");
    expect(trace.id).not.toBe(RECORDED);
    expect(trace.payload?.trace_id).toBe(trace.id);
    expect(trace.payload?.entrypoint).toMatchObject({ record_ids: [9], kwargs: { note: "x" } });
    expect(trace.payload?.steps).toHaveLength(879);
    expect((await data.listTraces()).items[0]?.id).toBe(trace.id);
    expect((await data.getTrace(trace.id)).id).toBe(trace.id);
  });

  it("records an unknown entrypoint as a failed run", async () => {
    const trace = await source().startTrace({ ...CONFIRM, entrypoint_model: "res.partner" });

    expect(trace.status).toBe("failed");
    expect(trace.payload).toBeNull();
    expect(trace.error).toContain("Fixture mode can only run");
  });

  it("refuses dry_run=false like the backend's default", async () => {
    const error = await failure(source().startTrace({ ...CONFIRM, dry_run: false }));

    expect(error.status).toBe(403);
  });

  it("describes entrypoints from the fixtures only", async () => {
    const known = await source().describeEntrypoint("sale.order", "action_confirm");
    const unknown = await failure(source().describeEntrypoint("res.partner", "write"));

    expect(known).toMatchObject({ module: "sale", model_level: false, parameters: [] });
    expect(unknown.status).toBe(404);
    expect(unknown.message).toContain(FIXTURE_MODE_NOTICE);
  });

  it("deletes traces", async () => {
    const data = source();

    await data.deleteTrace(FAILED_EXAMPLE);

    expect((await data.listTraces()).total).toBe(4);
    expect((await failure(data.deleteTrace(FAILED_EXAMPLE))).status).toBe(404);
  });

  it("simulates latency and can be cancelled", async () => {
    vi.useFakeTimers();
    try {
      const data = createFixtureDataSource({ delayMs: 400 });
      const controller = new AbortController();
      let settled = false;

      const pending = failure(data.startTrace(CONFIRM, { signal: controller.signal })).finally(
        () => {
          settled = true;
        },
      );
      await vi.advanceTimersByTimeAsync(1000);
      expect(settled).toBe(false);

      controller.abort();
      expect((await pending).kind).toBe("aborted");
    } finally {
      vi.useRealTimers();
    }
  });
});
