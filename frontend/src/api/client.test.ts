import { createApiClient, DEFAULT_TIMEOUT_MS, START_TRACE_TIMEOUT_MS } from "@/api/client";
import { AppError } from "@/api/errors";
import type { FetchLike } from "@/api/http";
import type { StartTraceCommand } from "@/api/types";

const BASE = "http://api.test";

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function mockFetch(response: Response | (() => Promise<Response>)) {
  return vi.fn<FetchLike>(() =>
    typeof response === "function" ? response() : Promise.resolve(response),
  );
}

async function failure(promise: Promise<unknown>): Promise<AppError> {
  try {
    await promise;
  } catch (error) {
    if (error instanceof AppError) return error;
    throw error;
  }
  throw new Error("expected the call to fail");
}

const COMMAND: StartTraceCommand = {
  entrypoint_model: "sale.order",
  entrypoint_method: "action_confirm",
  record_ids: [1],
  dry_run: true,
};

describe("api client: requests", () => {
  it.each([
    ["health", (c: ReturnType<typeof createApiClient>) => c.health(), "/health"],
    ["odooStatus", (c: ReturnType<typeof createApiClient>) => c.odooStatus(), "/odoo/status"],
    [
      "describeEntrypoint",
      (c: ReturnType<typeof createApiClient>) => c.describeEntrypoint("res.partner", "write"),
      "/odoo/entrypoints/res.partner/write",
    ],
    [
      "getTrace",
      (c: ReturnType<typeof createApiClient>) => c.getTrace("3f2b8c1e-6d4a-4c1e-9b7a-1a2b3c4d5e01"),
      "/traces/3f2b8c1e-6d4a-4c1e-9b7a-1a2b3c4d5e01",
    ],
  ])("%s sends GET %s without extra headers", async (_name, call, path) => {
    const fetchFn = mockFetch(json(200, { ok: true }));

    await expect(call(createApiClient({ baseUrl: BASE, fetch: fetchFn }))).resolves.toEqual({
      ok: true,
    });

    const [url, init] = fetchFn.mock.calls[0]!;
    expect(url).toBe(`${BASE}${path}`);
    expect(init.method).toBe("GET");
    expect(init.headers).toBeUndefined();
    expect(init.body).toBeUndefined();
  });

  it("puts list filters into the query and leaves empty ones out", async () => {
    const fetchFn = mockFetch(json(200, { items: [], total: 0, limit: 20, offset: 40 }));
    const client = createApiClient({ baseUrl: BASE, fetch: fetchFn });

    await client.listTraces({
      status: "failed",
      entrypoint_model: "sale.order",
      entrypoint_method: null,
      limit: 20,
      offset: 40,
    });

    const url = new URL(fetchFn.mock.calls[0]![0]);
    expect(url.pathname).toBe("/traces");
    expect(Object.fromEntries(url.searchParams)).toEqual({
      status: "failed",
      entrypoint_model: "sale.order",
      limit: "20",
      offset: "40",
    });
  });

  it("starts a trace with a JSON body and only the Content-Type header", async () => {
    const fetchFn = mockFetch(json(201, { id: "t1", status: "succeeded" }));

    const result = await createApiClient({ baseUrl: BASE, fetch: fetchFn }).startTrace(COMMAND);

    expect(result).toEqual({ id: "t1", status: "succeeded" });
    const [url, init] = fetchFn.mock.calls[0]!;
    expect(url).toBe(`${BASE}/traces`);
    expect(init.method).toBe("POST");
    expect(init.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(init.body as string)).toEqual(COMMAND);
  });

  it("deletes a trace (204 without body)", async () => {
    const fetchFn = mockFetch(new Response(null, { status: 204 }));

    await expect(
      createApiClient({ baseUrl: BASE, fetch: fetchFn }).deleteTrace("t1"),
    ).resolves.toBeUndefined();
    expect(fetchFn.mock.calls[0]![1].method).toBe("DELETE");
  });

  it("encodes path parameters", async () => {
    const fetchFn = mockFetch(json(200, {}));

    await createApiClient({ baseUrl: BASE, fetch: fetchFn }).describeEntrypoint("x/y", "a b");

    expect(fetchFn.mock.calls[0]![0]).toBe(`${BASE}/odoo/entrypoints/x%2Fy/a%20b`);
  });

  it("keeps a path prefix in the base URL", async () => {
    const fetchFn = mockFetch(json(200, {}));

    await createApiClient({ baseUrl: "http://host/flowdoo/api", fetch: fetchFn }).health();

    expect(fetchFn.mock.calls[0]![0]).toBe("http://host/flowdoo/api/health");
  });
});

describe("api client: errors", () => {
  it.each([
    [403, "dry_run=false is disabled."],
    [404, "Trace t1 not found"],
    [409, "Trace t1 was deleted while it was being recorded"],
    [502, "Unexpected signature answer from flow_tracer: 3 errors"],
    [503, "No connection to Odoo is configured, traces cannot be started"],
  ])("HTTP %i keeps the backend message", async (status, detail) => {
    const client = createApiClient({ baseUrl: BASE, fetch: mockFetch(json(status, { detail })) });

    const error = await failure(client.startTrace(COMMAND));

    expect(error.kind).toBe("http");
    expect(error.status).toBe(status);
    expect(error.message).toBe(detail);
  });

  it("HTTP 422 becomes a validation error with field errors", async () => {
    const body = { detail: [{ loc: ["query", "limit"], msg: "too large", type: "le" }] };
    const client = createApiClient({ baseUrl: BASE, fetch: mockFetch(json(422, body)) });

    const error = await failure(client.listTraces({ limit: 999 }));

    expect(error.kind).toBe("validation");
    expect(error.fieldErrors).toEqual([{ path: "query.limit", message: "too large" }]);
  });

  it("an unreachable API is a network error", async () => {
    const fetchFn = vi.fn<FetchLike>(() => Promise.reject(new TypeError("Failed to fetch")));

    const error = await failure(createApiClient({ baseUrl: BASE, fetch: fetchFn }).health());

    expect(error.kind).toBe("network");
    expect(error.message).toContain(BASE);
  });

  it("a 200 without a readable body is unexpected", async () => {
    const fetchFn = mockFetch(new Response("not json", { status: 200 }));

    const error = await failure(createApiClient({ baseUrl: BASE, fetch: fetchFn }).odooStatus());

    expect(error.kind).toBe("unexpected");
  });
});

describe("api client: timeouts and cancellation", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  function hangingFetch() {
    return vi.fn<FetchLike>(
      (_url, init) =>
        new Promise((_resolve, reject) => {
          init.signal?.addEventListener("abort", () => {
            reject(new DOMException("aborted", "AbortError"));
          });
        }),
    );
  }

  it("reads time out after the short default", async () => {
    vi.useFakeTimers();
    const client = createApiClient({ baseUrl: BASE, fetch: hangingFetch() });

    const pending = failure(client.health());
    await vi.advanceTimersByTimeAsync(DEFAULT_TIMEOUT_MS);

    const error = await pending;
    expect(error.kind).toBe("timeout");
    expect(error.message).toBe("The API did not answer within 10 s.");
  });

  it("starting a trace waits longer than a read", async () => {
    vi.useFakeTimers();
    const client = createApiClient({ baseUrl: BASE, fetch: hangingFetch() });
    let settled = false;

    const pending = failure(client.startTrace(COMMAND)).finally(() => {
      settled = true;
    });
    await vi.advanceTimersByTimeAsync(DEFAULT_TIMEOUT_MS * 6);
    expect(settled).toBe(false);

    await vi.advanceTimersByTimeAsync(START_TRACE_TIMEOUT_MS);
    expect((await pending).kind).toBe("timeout");
  });

  it("a running trace start can be cancelled", async () => {
    const controller = new AbortController();
    const client = createApiClient({ baseUrl: BASE, fetch: hangingFetch() });

    const pending = failure(client.startTrace(COMMAND, { signal: controller.signal }));
    controller.abort();

    const error = await pending;
    expect(error.kind).toBe("aborted");
  });

  it("an already cancelled signal does not reach the API", async () => {
    const controller = new AbortController();
    controller.abort();
    const fetchFn = hangingFetch();

    const error = await failure(
      createApiClient({ baseUrl: BASE, fetch: fetchFn }).getTrace("t1", {
        signal: controller.signal,
      }),
    );

    expect(error.kind).toBe("aborted");
    expect(fetchFn).not.toHaveBeenCalled();
  });
});
