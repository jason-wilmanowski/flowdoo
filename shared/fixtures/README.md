# Trace fixtures

Example traces that follow `../schemas/trace.schema.json` (v0.2.0). The frontend is
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

## Registry fixture

`registry-sale-stock-account.json` is the answer of `GET /odoo/models` (all 428 models)
plus `GET /odoo/models/{model}` for 34 central models (sales, inventory, accounting, mail),
**recorded** from the test Odoo (Odoo 19.0-20260926, 64 modules incl. `sale_stock` and
`account`, demo data). Keys: `odoo_version`, `modules` (installed), `models`, `details`
(model name -> detail). The frontend's overview works on it without backend and Odoo.
Re-record it when the registry routes change.

