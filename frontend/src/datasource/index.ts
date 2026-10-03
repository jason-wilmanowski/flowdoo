import { createApiClient } from "@/api/client";
import { createApiDataSource } from "@/datasource/apiDataSource";
import { createFixtureDataSource } from "@/datasource/fixtures/fixtureDataSource";
import type { DataSource, DataSourceKind } from "@/datasource/types";

export { createApiDataSource } from "@/datasource/apiDataSource";
export {
  createFixtureDataSource,
  FIXTURE_MODE_NOTICE,
} from "@/datasource/fixtures/fixtureDataSource";
export type { CallOptions, DataSource, DataSourceKind, Trace } from "@/datasource/types";

/** VITE_DATA_SOURCE: "fixtures" or "api" (default). */
export function configuredDataSourceKind(value = import.meta.env.VITE_DATA_SOURCE): DataSourceKind {
  return value === "fixtures" ? "fixtures" : "api";
}

export function createDataSource(kind: DataSourceKind = configuredDataSourceKind()): DataSource {
  return kind === "fixtures" ? createFixtureDataSource() : createApiDataSource(createApiClient());
}
