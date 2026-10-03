# ADR 0004: Frontend data sources and fixture mode

- **Status:** accepted
- **Date:** 2026-10-03

## Context

The frontend must be fully usable with `shared/fixtures/*.json`, without backend and Odoo
(CLAUDE.md section 7), and the same UI must later work against the real API. Presentational
components never call the API; data flows component → store → data source → client.

## Decision

- **One interface, `DataSource`** (`src/datasource/types.ts`) with two implementations:
  - `ApiDataSource` wraps the API client.
  - `FixtureDataSource` works on `shared/fixtures/` only.
  Both raise `AppError` (`src/api/errors.ts`), so stores and UI handle
  errors identically.
- **Typed payloads.** `DataSource` returns `Trace` = the API's `TraceDetail` with `payload`
  typed as the generated `TracePayload`. The API types the payload as an open object; the
  backend validates it against the same schema before storing it. The cast happens in
  exactly one place (`apiDataSource.ts`).
- **Selection:** `VITE_DATA_SOURCE` = `api` (default) or `fixtures`. The UI will show which
  one is active and may switch at runtime (app shell). API is the default because the
  product stack (compose) runs with a backend; fixture mode is the explicit choice for
  frontend work without one.
- **Fixture mode simulates the API's behavior**, not new endpoints:
  - list with the API's filters, paging and order; detail; 404 for unknown ids; delete;
  - `startTrace`: artificial delay (cancellable), refuses `dry_run=false` like the backend's
    default, and records a known entrypoint (`sale.order.action_confirm`) as a new trace
    cloned from the largest matching fixture (the 879-step recording); unknown entrypoints
    become a failed recording with a clear "fixture mode" message;
  - one additional, clearly labelled failed recording (status `failed`, no payload), so the
    "recording failed" state exists next to "Odoo raised" (`trace-error.json`);
  - `odooStatus` is `ok` with a warning that fixture mode is active;
  - `describeEntrypoint` only knows the fixture entrypoints (no invented parameters).
- **Loading:** fixtures are imported on demand as text (`?raw`) and parsed once. The 470 KB
  recording is neither type-checked nor part of the API-mode bundle.
- **Location of `shared/`:** alias `@shared` → `../shared` locally, `FLOWDOO_SHARED_DIR`
  (`/shared`) in the container; Vite's `server.fs.allow` admits exactly that directory.

## Consequences

- Fixtures and fixture-mode traces are validated against `trace.schema.json` (Ajv, JSON Schema
  2020-12) in the tests.
- New API endpoints need a matching method in both implementations.
