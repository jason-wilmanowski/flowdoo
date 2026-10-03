import {
  DATA_SOURCE_STORAGE_KEY,
  initialDataSourceKind,
  storeDataSourceKind,
} from "./dataSourceChoice";

describe("data source choice", () => {
  afterEach(() => {
    localStorage.clear();
  });

  it("uses the configured default without a stored choice", () => {
    expect(initialDataSourceKind()).toBe("api");
  });

  it("prefers a stored choice and ignores unknown values", () => {
    storeDataSourceKind("fixtures");
    expect(localStorage.getItem(DATA_SOURCE_STORAGE_KEY)).toBe("fixtures");
    expect(initialDataSourceKind()).toBe("fixtures");
    localStorage.setItem(DATA_SOURCE_STORAGE_KEY, "mock");
    expect(initialDataSourceKind()).toBe("api");
  });

  it("falls back when storage is unavailable", () => {
    const broken = {
      getItem: () => {
        throw new Error("denied");
      },
    };
    expect(initialDataSourceKind(broken)).toBe("api");
  });
});
