# Trace fixtures

Example traces that follow `../schemas/trace.schema.json` (v0.1.0). The frontend is
developed and tested against them; backend tests validate them against the schema.

| File | Content |
|---|---|
| `trace-small.json` | `sale.order.action_confirm` with only `sale` installed: 4 steps, one write |
| `trace-medium.json` | Same entrypoint with `sale_stock`: override chain with `super()`, ORM create, compute, blocked mail |
| `trace-error.json` | Confirming an order that is already confirmed: `UserError` on the entrypoint |

**Hand-written, not recorded.** Method names, modules and the error message come from the
Odoo 19 source (`sale`, `sale_stock`), but call chains are shortened and ids, values and
durations are made up. They show the shape of a trace, not real Odoo behaviour. Recorded
fixtures will be added once the flow_tracer addon exists.
