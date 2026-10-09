import type { ApiClient } from "@/api/client";
import { createApiDataSource } from "@/datasource/apiDataSource";
import { configuredDataSourceKind, createDataSource } from "@/datasource/index";

function fakeClient(): ApiClient {
  return {
    baseUrl: "http://api.test",
    health: vi.fn(),
    odooStatus: vi.fn().mockResolvedValue({ ok: true }),
    describeEntrypoint: vi.fn().mockResolvedValue({ method: "write" }),
    listModels: vi.fn().mockResolvedValue({ models: [] }),
    describeModel: vi.fn().mockResolvedValue({ model: "res.partner", fields: [] }),
    listTraces: vi.fn().mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 }),
    getTrace: vi.fn().mockResolvedValue({ id: "t1", payload: { steps: [] } }),
    startTrace: vi.fn().mockResolvedValue({ id: "t2", payload: null }),
    deleteTrace: vi.fn().mockResolvedValue(undefined),
  };
}

describe("api data source", () => {
  it("passes every call through to the client", async () => {
    const client = fakeClient();
    const source = createApiDataSource(client);
    const signal = new AbortController().signal;

    expect(source.kind).toBe("api");
    await source.odooStatus({ signal });
    await source.describeEntrypoint("res.partner", "write");
    await source.listModels({ signal });
    await source.describeModel("res.partner");
    await source.listTraces({ limit: 5 });
    expect((await source.getTrace("t1")).payload).toEqual({ steps: [] });
    await source.startTrace({
      entrypoint_model: "a",
      entrypoint_method: "b",
      record_ids: [],
      dry_run: true,
    });
    await expect(source.deleteTrace("t1")).resolves.toBeUndefined();

    expect(client.odooStatus).toHaveBeenCalledWith({ signal });
    expect(client.describeEntrypoint).toHaveBeenCalledWith("res.partner", "write", undefined);
    expect(client.listTraces).toHaveBeenCalledWith({ limit: 5 }, undefined);
    expect(client.listModels).toHaveBeenCalledWith({ signal });
    expect(client.describeModel).toHaveBeenCalledWith("res.partner", undefined);
    expect(client.deleteTrace).toHaveBeenCalledWith("t1", undefined);
  });
});

describe("configuration", () => {
  it("uses the API unless fixtures are asked for", () => {
    expect(configuredDataSourceKind(undefined)).toBe("api");
    expect(configuredDataSourceKind("api")).toBe("api");
    expect(configuredDataSourceKind("fixtures")).toBe("fixtures");
    expect(configuredDataSourceKind("something")).toBe("api");
  });

  it("creates the matching implementation", () => {
    expect(createDataSource("fixtures").kind).toBe("fixtures");
    expect(createDataSource("api").kind).toBe("api");
  });
});
