# Flowdoo MCP server

Lets Claude Code, and other MCP clients, run dry runs in your Odoo 19 and read the trace.
It talks to Odoo directly and needs neither the Flowdoo containers nor their database, only
the `flow_tracer` addon in your Odoo.

## Setup

Create `mcp-server/.env` (git-ignored). Use a development database that was neutralised
with `odoo neutralize`; `run_trace` refuses any other.

```
ODOO_URL=http://localhost:8069
ODOO_DB=my_dev_database
ODOO_API_KEY=my-api-key
# Optional: the login the key must belong to, seconds to wait for a run (default 30)
ODOO_LOGIN=admin
FLOWDOO_TIMEOUT=120
```

Register the server in Claude Code:

```
claude mcp add --transport stdio flowdoo -- uv run --directory /absolute/path/to/mcp-server flowdoo-mcp
```

## Tools

| Tool | Answers |
|---|---|
| `odoo_status` | Reachable, Odoo 19.0, valid key, addon switched on, neutralised database |
| `describe_entrypoint` | Parameters of a method before tracing it |
| `list_models` | Models by a part of their name or description, page by page |
| `describe_model` | Inheritance and fields of a model, filtered by name, module or stored |
| `run_trace` | Records a dry run of records given by id or exact name, keeps the trace and returns its overview |
| `explain_field` | Who changed a field in a kept trace: values, the business method behind it, call path |
| `list_traces` | The traces kept in this session |
| `trace_overview` | Counts per kind, model and module, changed values with their method, filled fields per model, top-level calls, where failures start |
| `find_steps` | Steps by model, method, module, kind, changed field, record, subtree or failure, page by page |
| `get_step` | One step in full, its call path and children, the implementations of its method that ran |

## Sessions and sizes

The server is meant for one session, typically one feature. Traces live in its memory until
the process stops, at most the latest 20 of them and 100,000 steps in total. Asking about a kept trace does not run the
workflow again, so step ids stay valid.

Every answer stays in the client's context and is sent again each round, so answers leave out
empty values and framework noise. Trace answers are made for language models: lists of steps and changes are cut at about
20,000 characters and say how to get the rest (`next_offset`, `changes_total`). `describe_model` follows the same limit
and says `fields_total`. `find_steps`
shortens long arguments and results; `get_step` shows them as recorded.

A dry run leaves no records behind, but database sequences are not rolled back: ids and
document numbers such as `WH/OUT/00123` get higher with every run.

A trace records ORM changes and method calls. Writes through direct SQL (`cr.execute`) do not appear
as changes.

## Development

```
uv sync
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest
```
