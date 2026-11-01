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
| `list_models` | Models by a part of their name or description |
| `describe_model` | Fields, inheritance and relations of a model |
| `run_trace` | Records a dry run, keeps the trace and returns an overview |
| `list_traces` | The traces recorded since the server started |
| `trace_overview` | Number of steps, models and modules involved, changed fields, errors |
| `find_steps` | Steps by model, method, module, kind, changed field or failure |
| `get_step` | All details of one step, its call path and its children |

Traces are kept in memory only and are lost when the server stops.

## Development

```
uv sync
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest
```
