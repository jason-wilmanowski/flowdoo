import { AppError } from "@/api/errors";
import type { StartTraceCommand } from "@/api/types";
import { createFixtureDataSource } from "@/datasource/fixtures/fixtureDataSource";
import type { DataSource, Trace } from "@/datasource/types";
import { createAppStores } from "@/stores/appStores";

const RECORDED = "22585514-6fae-4c9b-96ee-3f431ba1035a";
const SMALL = "3f2b8c1e-6d4a-4c1e-9b7a-1a2b3c4d5e01";
const CONFIRM: StartTraceCommand = {
  entrypoint_model: "sale.order",
  entrypoint_method: "action_confirm",
  record_ids: [1],
  dry_run: true,
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("stores on the fixture data source", () => {
  const stores = () => createAppStores(createFixtureDataSource({ delayMs: 0 }));

  it("loads the connection status", async () => {
    const { connection } = stores();

    const pending = connection.getState().refresh();
    expect(connection.getState().phase).toBe("loading");
    await pending;

    expect(connection.getState().phase).toBe("ready");
    expect(connection.getState().status?.ok).toBe(true);
  });

  it("loads and filters the trace list", async () => {
    const { traceList } = stores();

    await traceList.getState().load({ status: "failed" });

    expect(traceList.getState().phase).toBe("ready");
    expect(traceList.getState().query).toEqual({ status: "failed" });
    expect(traceList.getState().page?.total).toBe(1);
  });

  it("loads a trace, indexes it and resets the replay", async () => {
    const { currentTrace, replay } = stores();

    await currentTrace.getState().load(RECORDED);

    const state = currentTrace.getState();
    expect(state.phase).toBe("ready");
    expect(state.index?.ordered).toHaveLength(879);
    expect(replay.getState()).toMatchObject({ stepCount: 879, cursor: 0, playing: false });
  });

  it("starts a run, shows it and refreshes the list", async () => {
    const { currentTrace, traceList } = stores();
    await traceList.getState().load();
    const before = traceList.getState().page!.total;

    const pending = currentTrace.getState().start(CONFIRM);
    expect(currentTrace.getState().run).toMatchObject({ phase: "running", command: CONFIRM });
    const trace = await pending;

    expect(trace?.status).toBe("succeeded");
    expect(currentTrace.getState()).toMatchObject({ traceId: trace!.id, run: { phase: "idle" } });
    await vi.waitFor(() => {
      expect(traceList.getState().page!.total).toBe(before + 1);
    });
  });

  it("deletes a trace and reloads the list", async () => {
    const { traceList } = stores();
    await traceList.getState().load();

    await traceList.getState().remove(SMALL);

    expect(traceList.getState().page!.items.some((t) => t.id === SMALL)).toBe(false);
  });
});

describe("stores: errors, stale answers, cancellation", () => {
  function fakeSource(overrides: Partial<DataSource>): DataSource {
    return { ...createFixtureDataSource({ delayMs: 0 }), ...overrides };
  }

  it("keeps the AppError of a failed load", async () => {
    const error = new AppError("http", "Trace x not found", { status: 404 });
    const { currentTrace } = createAppStores(fakeSource({ getTrace: () => Promise.reject(error) }));

    await currentTrace.getState().load("x");

    expect(currentTrace.getState()).toMatchObject({ phase: "error", error });
  });

  it("wraps unknown errors as unexpected AppErrors", async () => {
    const { connection } = createAppStores(
      fakeSource({ odooStatus: () => Promise.reject(new Error("boom")) }),
    );

    await connection.getState().refresh();

    expect(connection.getState().error?.kind).toBe("unexpected");
  });

  it("shows the newest requested trace even if an older answer arrives later", async () => {
    const slow = deferred<Trace>();
    const real = createFixtureDataSource({ delayMs: 0 });
    const { currentTrace } = createAppStores(
      fakeSource({
        getTrace: (id, call) => (id === "slow" ? slow.promise : real.getTrace(id, call)),
      }),
    );

    const first = currentTrace.getState().load("slow");
    await currentTrace.getState().load(SMALL);
    slow.resolve(await real.getTrace(RECORDED));
    await first;

    expect(currentTrace.getState().trace?.id).toBe(SMALL);
  });

  it("a cancelled run returns to idle without an error", async () => {
    const { currentTrace } = createAppStores(createFixtureDataSource({ delayMs: 50 }));

    const pending = currentTrace.getState().start(CONFIRM);
    currentTrace.getState().cancelStart();

    await expect(pending).resolves.toBeNull();
    expect(currentTrace.getState().run).toMatchObject({ phase: "idle", error: null });
    expect(currentTrace.getState().trace).toBeNull();
  });

  it("a failed start keeps the command and the error", async () => {
    const { currentTrace } = createAppStores(createFixtureDataSource({ delayMs: 0 }));

    await currentTrace.getState().start({ ...CONFIRM, dry_run: false });

    expect(currentTrace.getState().run).toMatchObject({
      phase: "error",
      command: { dry_run: false },
      error: { status: 403 },
    });
  });
});

describe("replay store", () => {
  const replay = () => {
    const { replay } = createAppStores(createFixtureDataSource({ delayMs: 0 }));
    replay.getState().reset(3);
    return replay;
  };

  it("moves within bounds", () => {
    const store = replay();
    const { next, previous, last, first, goTo } = store.getState();

    previous();
    expect(store.getState().cursor).toBe(0);
    next();
    next();
    next();
    expect(store.getState().cursor).toBe(2);
    first();
    expect(store.getState().cursor).toBe(0);
    last();
    expect(store.getState().cursor).toBe(2);
    goTo(1);
    expect(store.getState().cursor).toBe(1);
    goTo(99);
    expect(store.getState().cursor).toBe(2);
  });

  it("plays to the end and stops; playing at the end starts over", () => {
    const store = replay();
    store.getState().play();

    store.getState().tick();
    store.getState().tick();
    expect(store.getState()).toMatchObject({ cursor: 2, playing: false });

    store.getState().toggle();
    expect(store.getState()).toMatchObject({ cursor: 0, playing: true });
    store.getState().toggle();
    expect(store.getState().playing).toBe(false);
  });

  it("does nothing without steps", () => {
    const store = replay();
    store.getState().reset(0);
    store.getState().play();
    store.getState().next();

    expect(store.getState()).toMatchObject({ cursor: null, playing: false });
  });

  it("changes the speed", () => {
    const store = replay();
    store.getState().setSpeed(4);

    expect(store.getState().speed).toBe(4);
  });
});
