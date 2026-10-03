# ADR 0003: Frontend type generation and the OpenAPI source

- **Status:** accepted
- **Date:** 2026-10-03

## Context

The frontend must not hand-write types for the trace payload or the API (CLAUDE.md section
3). The trace payload is defined by `shared/schemas/trace.schema.json`; the API DTOs
(`TraceSummary`, `TraceDetail`, `TracePage`, `StartTraceCommand`, `OdooConnectionStatus`, …)
are defined by the backend's FastAPI app and described by its OpenAPI document.

## Decision

`pnpm gen:types` in `frontend/` (`scripts/gen-types.mjs`) writes three checked-in files to
`src/generated/`:

| File | Source | Tool |
|---|---|---|
| `trace.ts` | `shared/schemas/trace.schema.json` | `json-schema-to-typescript` |
| `openapi.json` | the backend's FastAPI app | `scripts/dump_openapi.py` via `uv run --project ../backend` |
| `api.ts` | `openapi.json` | `openapi-typescript` |

**OpenAPI source: the FastAPI app itself, not a running server.** `dump_openapi.py` builds the
app with dummy settings and prints `app.openapi()`. No server, database or Odoo is needed and
the backend is not changed. The document reflects exactly the backend code in the same
checkout, so a backend change and its frontend types land in one review. The JSON is checked
in too, so API changes show up as a readable diff.

Alternatives not taken: fetching `/openapi.json` from a running API (needs the stack running,
including in CI, and can drift from the checkout); adding an export command to the backend
(a backend change for a frontend concern).

## Consequences

- `pnpm gen:types` needs `uv` and the backend's dependencies (`uv sync` in `backend/`).
- CI job "Frontend · generated types up to date" regenerates and fails on any diff.
- After a schema or API change (e.g. schema 0.2.0 with `kwargs` and
  `GET /odoo/entrypoints/{model}/{method}`), run `pnpm gen:types` and commit the result.
