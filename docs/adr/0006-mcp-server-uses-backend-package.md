# ADR 0006: The MCP server reuses the backend package

- **Status:** accepted
- **Date:** 2026-11-01

## Context

The MCP server needs the backend's Odoo client, connection check, entrypoint and registry
lookups and trace validation. So far the parts of the repository never import each other,
and the first plan was to move this code into a small shared library. The server must also
work without the Flowdoo containers and their database, so it cannot call the REST API.

## Decision

- `mcp-server` depends on `backend` as an editable path dependency and calls
  `flow_tracer_api`'s integrations and services directly. It stays a one-way dependency: the
  backend knows nothing about the MCP server.
- It only uses what needs no database (not `TraceService`). Recorded traces stay in memory
  for the lifetime of the server process.
- `run_trace` always runs as a dry run and refuses a database that is not known to be
  neutralised.

## Consequences

- No logic is duplicated, and no shared library has to be extracted yet.
- The server installs the backend's dependencies too (FastAPI, SQLAlchemy, ...), although it
  does not open a database connection. A shared library remains the way out if that hurts.
- Changes to the backend's services can break the MCP server, so its tests belong in CI.
- Traces are gone when the server stops; storing them as files can follow when needed.
