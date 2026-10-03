# Trace fixtures

Example traces that follow `../schemas/trace.schema.json` (v0.1.0). The frontend is
developed and tested against them; backend tests validate them against the schema.

| File | Content |
|---|---|
| `trace-small.json` | `sale.order.action_confirm` with only `sale` installed: 4 steps, one write |
| `trace-medium.json` | Same entrypoint with `sale_stock`: override chain with `super()`, ORM create, compute, blocked mail |
| `trace-error.json` | Confirming an order that is already confirmed: `UserError` on the entrypoint |
| `recorded-sale-order-action-confirm.json` | **Recorded**, not hand-written: `sale.order.action_confirm` on demo order S00001 (`sale_stock` + demo data, Odoo 19.0-20260926), dry run, through backend → flow_tracer addon. 879 steps. |

**The `trace-*` files are hand-written, not recorded.** Method names, modules and the error message come from the
Odoo 19 source (`sale`, `sale_stock`), but call chains are shortened and ids, values and
durations are made up. They show the shape of a trace, not real Odoo behaviour.

`recorded-*` files are real recordings. Values come from Odoo's demo data (fictional
companies and people); re-record them when the schema or the recorder changes.
