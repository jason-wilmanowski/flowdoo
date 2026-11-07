# flow_tracer_mcp (Odoo 19 addon)

Extra answers of [Flowdoo](../../README.md) for the [MCP server](../../mcp-server/README.md),
on top of [`flow_tracer`](../flow_tracer/README.md), which stays unchanged
([ADR 0007](../../docs/adr/0007-flow-tracer-mcp-addon.md)). Optional: without it, the MCP server
traces through `flow_tracer` alone.

> [!WARNING]
> Development databases only, like `flow_tracer`. Never install it on production.

## What it adds

| Route | Answers |
|---|---|
| `/flow_tracer_mcp/v1/method` | Active overrides of a method, most derived first: module, file, line, `super()` call |
| `/flow_tracer_mcp/v1/field` | How a field gets its value: compute method, dependencies, stored fields it recomputes |
| `/flow_tracer_mcp/v1/trace` | The trace of `flow_tracer`, always a dry run, plus writes through direct SQL |

Direct SQL writes are listed with operation, table, columns and the calling code, never with
values. Writes of the ORM itself are left out. Whether a call to `super()` happens is read from
the code, so it is a heuristic.

## Install

1. Make `odoo-addons` available in your Odoo's addons path, as for `flow_tracer`.
2. Install it: `odoo -d <db> -i flow_tracer_mcp --stop-after-init`. This also installs
   `flow_tracer` if needed.
3. The routes follow the switch of `flow_tracer` (`flow_tracer_enabled = True`) and answer
   administrators only.

## Tests

```sh
odoo -d <throwaway db> -i flow_tracer_mcp --test-enable --test-tags /flow_tracer_mcp \
  --stop-after-init --http-port=8079
```

They need a running Odoo 19 and are not part of CI.
