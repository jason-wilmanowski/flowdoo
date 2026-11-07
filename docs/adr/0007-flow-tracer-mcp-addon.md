# ADR 0007: A separate addon and answer tools for the MCP server

- **Status:** accepted
- **Date:** 2026-11-07
- **Extends:** [ADR 0006](0006-mcp-server-uses-backend-package.md), whose list of tools it replaces

## Context

Benchmarks with Claude Code compared three setups on the same Odoo tasks: source code and
`odoo shell` only, the same plus curl recipes for the `flow_tracer` routes, and the same plus
the MCP server. On easy tasks in little code, the MCP server cost more tokens and helped no
one. On hard tasks across many modules, trace data led to more correct answers than reading
code alone, through curl and MCP alike. The first tools returned data the client still had to
work through, and every tool description costs context in each round, even unused.

Some answers need more than the recorder gives: the active overrides of a method with file
and line, how a field gets its value, and writes that bypass the ORM through `cr.execute`.
`flow_tracer` is meant to stay small and installable anywhere, and should not change for the
MCP server.

## Decision

- **Separate addon `flow_tracer_mcp`**, depending only on `flow_tracer`. It adds read-only
  routes for methods and fields, and a trace route that also lists direct SQL writes. It reuses
  the access checks of `flow_tracer`: the same switch in the Odoo configuration and
  administrators only.
- **Direct SQL writes** are noted while a trace runs by wrapping `Cursor.execute` for the
  recording thread. Only operation, table, columns and the calling code are kept, never
  parameters. Writes issued by the ORM are left out.
- **Six tools that answer questions:** `run_trace`, `compare_runs`, `explain_field`,
  `find_steps`, `resolve_method`, `describe_model`. Status, model lists, entrypoint signatures and
  separate trace readers were removed or merged, since they cost context without a measured
  benefit.
- **Without the addon** the server falls back to the routes of `flow_tracer`: traces work, but
  without direct SQL, `resolve_method` and field graphs.

## Consequences

- Users who want all answers install two addons. The status of `flow_tracer` does not show
  whether `flow_tracer_mcp` is installed.
- Wrapping `Cursor.execute` is a heuristic: code that writes through other paths is not seen,
  and the caller is the first frame outside the database layer.
- The server is a tool for debugging complex flows, not for every task. The README says so.
- The addon's tests run locally against Odoo, not in CI, like those of `flow_tracer`.
