# ADR 0001: Recorder mechanism

- **Status:** accepted
- **Date:** 2026-10-03
- **Spike:** [`spikes/recorder/`](../../spikes/recorder/)

## Context

The `flow_tracer` addon has to record what happens when an Odoo 19 entrypoint runs (e.g.
`sale.order.action_confirm`): every model method implementation that executes, across all
modules, with its module, its position in the MRO, whether it calls `super()`, and which
field values change. It must not change what it observes (no extra recomputes or side
effects), must not mix up parallel requests, and must cost (almost) nothing while no trace
is being recorded.

## Options measured

Reference: `sale.order.action_confirm` on demo order S00001 (3 storable products) in a
database with `sale_stock` and demo data (64 modules), Odoo 19.0-20260926, Python 3.12.3,
median of 7 runs, each run in a rolled back savepoint and including `flush_all()`.
Instrumented code: 7 984 functions defined in 749 addon model classes, plus
`BaseModel.create/write/unlink`.

| Option | Run time | Steps | Cost without a trace |
|---|---|---|---|
| none (baseline) | 29.6 ms | – | – |
| **A: `sys.monitoring` (PEP 669), local `PY_START`/`PY_RETURN` on the model method code objects** | **30.9 ms (+4 %)** | 1 313 | **none**: events are switched off (4 ms on / 3 ms off) |
| B: wrap the same functions in the model classes | 30.6 ms | 1 637 | wrappers stay in every class; classes are patched globally |
| C: `sys.setprofile`, filter in the callback | 277.6 ms (×9) | 1 313 | – |
| D: Odoo profiler, `traces_sync` collector (`sys.settrace`) | 294.9 ms (×10) | – | – |

With field change capture added to A: 31.6 ms, 79 changes, e.g. `sale.order(1).state:
'draft' -> 'sale'`, `stock.move.state: 'draft' -> 'confirmed'`, `stock.picking(123).sale_id:
None -> 1` (computed).

Observations:

- **A records exactly the code that ran.** B also counts calls answered by `ormcache`
  without running the method (`decimal.precision.precision_get` 192× in B, 96× in A), and
  patching classes affects every request in the process.
- C and D see every Python call in the interpreter and are an order of magnitude slower;
  D also produces stack samples, not model steps or field changes.
- Each override layer is its own step (e.g. `sale.order.write` in `sale_stock` → `sale` →
  `mail` → `BaseModel`), so module and MRO position come from the **defining class** and
  are exact, not guessed.
- About 28 % of the steps are framework infrastructure (`ir.rule`, `ir.model.access`,
  `decimal.precision`, `res.users` access helpers).
- Field values can be read from the ORM cache (`Field._get_cache(env)`) before and after a
  step without fetching or recomputing anything.

## Decision

**Use `sys.monitoring` (option A).**

1. **Targets:** the code objects of all functions defined in addon model classes
   (`odoo.addons.*`, unwrapped from decorators; generators and coroutines skipped) plus
   `BaseModel.create`, `write` and `unlink`. Each code object maps to its defining class,
   module (`_module`) and method name. The map is built per registry.
2. **Events on only while recording:** local `PY_START` and `PY_RETURN` on the targets, the
   global `PY_UNWIND` (not a local event in 3.12) only while at least one trace session is
   active, reference counted. Without a session no callback runs at all.
3. **Session per request in a `contextvars.ContextVar`:** callbacks from other threads or
   requests find no session and return immediately; parallel traces do not mix.
4. **Steps:** one per executed implementation. `module` and `mro_position` come from the
   defining class's position among the implementations of that method in the model's MRO.
   `calls_super` is `true` if the step has a direct child step of the same method on the
   same model with a later MRO position, which is an observation, not a heuristic.
5. **Field changes:** values are read from the ORM cache before and after `write`, `create`
   and compute methods (fields whose `compute` is that method), for the step's records.
   Nothing is fetched or recomputed for the recorder. A value that was not loaded before
   a compute is a first computation, not a change, and is skipped. For `write`, a stored
   column that was not in the cache is read with plain SQL (no flush).
6. **Infrastructure noise:** steps on a short, documented list of infrastructure models
   (access rules, defaults, decimal precision, …) are not recorded; their children attach
   to the nearest recorded step. The list lives in the addon and is covered by tests.
7. **Dry run:** the entrypoint runs in the request's transaction, followed by
   `env.flush_all()` (pending recomputes and constraints are part of the flow), the trace
   is built, then `cr.rollback()` discards everything (data, ORM cache, pre/post-commit
   hooks). While a dry run is active, `cr.commit()` raises, so code under trace cannot
   persist anything.

## Side effects

The recorder does **not** block side effects (mail, HTTP, payment providers, crons).
Decided with the project owner: Flowdoo is explicitly a tool for development databases,
and professional development databases are neutralised (`odoo neutralize` disables mail
servers, crons, payment providers, …). Mails queued in `mail.mail` are rolled back with the
dry run anyway; only calls that leave the process during the run itself would go through.
README and UI warn about this. This replaces the side-effect blocking list of CLAUDE.md §6.
The step kind `side_effect_blocked` stays in the schema but is not produced for now.

## Consequences

- **Python 3.12+ is required for recording** (`sys.monitoring`). Odoo 19 itself supports
  Python 3.10–3.14 and the official Odoo 19 image ships 3.12. On older Pythons the addon
  reports the recorder as unavailable instead of failing obscurely. Option B would be the
  fallback if that turns out to matter.
- A Python tool id (`sys.monitoring.PROFILER_ID`) is used while recording; another
  profiler using the same id at the same time makes recording fail with a clear error.
- Methods implemented in C, in `odoo.orm` (apart from create/write/unlink) or outside model
  classes are not steps. Their effects still show up as field changes of the steps around
  them.
- Traces of large flows can get long. The schema limit (20 000 steps) is enforced; the
  noise list and the frontend (collapsing) keep traces readable.
