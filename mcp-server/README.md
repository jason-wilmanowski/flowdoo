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
# Optional: seconds to wait for a run (default 30)
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
| `list_models` | Models by a part of their name or description |
| `describe_model` | Fields, inheritance and relations of a model |
| `run_trace` | Records a dry run and returns an overview plus the steps matching its filters |

Every call is a plain request and response: the server keeps nothing. To look at other steps
of a workflow, call `run_trace` again with other filters. That is a new dry run, so step ids
and step counts can differ between runs (Odoo's caches, for example, are warm the second
time).

## Development

```
uv sync
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest
```
