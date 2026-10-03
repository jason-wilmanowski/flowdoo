import { configuredDataSourceKind, type DataSourceKind } from "@/datasource";

export const DATA_SOURCE_STORAGE_KEY = "flowdoo.dataSource";

/** The source picked in the top bar wins over VITE_DATA_SOURCE until switched back. */
export function initialDataSourceKind(
  storage: Pick<Storage, "getItem"> = localStorage,
): DataSourceKind {
  try {
    const stored = storage.getItem(DATA_SOURCE_STORAGE_KEY);
    if (stored === "api" || stored === "fixtures") return stored;
  } catch {
    // storage unavailable: use the configured default
  }
  return configuredDataSourceKind();
}

export function storeDataSourceKind(
  kind: DataSourceKind,
  storage: Pick<Storage, "setItem"> = localStorage,
) {
  try {
    storage.setItem(DATA_SOURCE_STORAGE_KEY, kind);
  } catch {
    // not persisted; the switch still applies for this session
  }
}
