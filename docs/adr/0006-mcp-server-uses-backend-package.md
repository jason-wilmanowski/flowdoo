# ADR 0006: A lightweight, stateless MCP server on parts of the backend package

- **Status:** accepted
- **Date:** 2026-11-01

## Context

The MCP server needs the backend's Odoo client, trace gateway and data types. So far the
parts of the repository never import each other. The server must work without the Flowdoo
containers and their database, and it should stay small: no database, no repositories, no
state between calls.

## Decision

- `mcp-server` depends on `backend` as an editable path dependency, one way only, and imports
  just `flow_tracer_api`'s `integrations.odoo`, `schemas` and `generated`.
- It does not import `flow_tracer_api.services`: that package loads `TraceService` and with
  it SQLAlchemy. The tools follow the services but call the addon's routes themselves, and
  `flowdoo_mcp.status` holds the essential checks of the connection service. A test asserts
  that importing the tools loads neither the services nor SQLAlchemy or FastAPI.
- `tool.uv.exclude-dependencies` keeps the backend's database and web dependencies from being
  installed.
- Every tool call is a plain request and response with its own Odoo client. No lifespan
  state, no stored traces. `run_trace` returns an overview and the steps matching its filters.
- `run_trace` always runs as a dry run and refuses a database that is not known to be
  neutralised.

## Consequences

- The install stays small, and no shared library has to be extracted yet.
- The route names and the connection checks exist twice, in a shorter form here. Excluded
  dependencies also mean that a new backend import can fail only at runtime; the test above
  and the tool tests catch that, so they belong in CI.
- Every further question about a run is a new dry run. Step ids and counts can differ between
  runs, and document numbers can be drawn again. Answers cannot refer to an earlier run.
