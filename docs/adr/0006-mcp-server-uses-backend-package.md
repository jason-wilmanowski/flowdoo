# ADR 0006: A lightweight MCP server on parts of the backend package

- **Status:** accepted
- **Date:** 2026-11-01

## Context

The MCP server needs the backend's Odoo client, trace gateway and data types. So far the
parts of the repository never import each other. The server must work without the Flowdoo
containers and their database, and it should stay small: no database and no repositories. A
session usually covers one feature, so traces only have to last as long as the process.

## Decision

- `mcp-server` depends on `backend` as an editable path dependency, one way only, and imports
  just `flow_tracer_api`'s `integrations.odoo`, `schemas` and `generated`.
- It does not import `flow_tracer_api.services`: that package loads `TraceService` and with
  it SQLAlchemy. The tools follow the services but call the addon's routes themselves, and
  `flowdoo_mcp.status` holds the essential checks of the connection service. A test asserts
  that importing the tools loads neither the services nor SQLAlchemy or FastAPI.
- `tool.uv.exclude-dependencies` keeps the backend's database and web dependencies from being
  installed.
- A lifespan holds one Odoo client, the gateway and the recorded traces in memory, at most the
  latest 20. `run_trace` returns an overview; `trace_overview`, `find_steps` and `get_step`
  read the kept trace without running the workflow again.
- `run_trace` always runs as a dry run and refuses a database that is not known to be
  neutralised.

## Consequences

- The install stays small, and no shared library has to be extracted yet.
- The route names and the connection checks exist twice, in a shorter form here. Excluded
  dependencies also mean that a new backend import can fail only at runtime; the test above
  and the tool tests catch that, so they belong in CI.
- Traces are gone when the server stops. Storing them as files can follow when needed.
