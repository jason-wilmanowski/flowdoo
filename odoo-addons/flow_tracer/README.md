# flow_tracer (Odoo 19 addon)

Recorder side of [Flowdoo](../../README.md). It is installed into **your existing Odoo 19**,
runs an entrypoint such as `sale.order.action_confirm`, records every model method
implementation that executes and the field values that change, and returns the trace
([format](../../docs/trace-format.md)) to the Flowdoo backend.

> [!WARNING]
> Development databases only. Tracing runs real business logic. Runs are rolled back by
> default, but side effects such as mails or HTTP calls are **not** blocked: use a
> neutralised database (`odoo neutralize -d <db>`). Never enable this addon on production.
> Numbers from standard `ir.sequence`s (pickings, quotations, …) drawn during a dry run
> stay used, because PostgreSQL sequences ignore rollbacks; the next real document skips
> them.

## Requirements

- Odoo 19.0
- **Python 3.12+** for recording (`sys.monitoring`). The official Odoo 19 image has 3.12.
  On older Pythons the status endpoint reports `recorder_available: false`.
- Depends only on `base`.

## Install

1. Make this folder available in your Odoo's addons path, e.g. mount it in Docker:

   ```yaml
   volumes:
     - /path/to/flowdoo/odoo-addons:/mnt/extra-addons/flowdoo:ro
   ```

   and add that path to `addons_path`.
2. Install the module **Flowdoo Flow Tracer** (`flow_tracer`), e.g.
   `odoo -d <db> -i flow_tracer --stop-after-init`.
3. Enable it on the server, in the `[options]` section of the Odoo configuration file:

   ```ini
   flow_tracer_enabled = True
   ```

   Odoo logs `unknown option 'flow_tracer_enabled' ... stored as-is` at startup. That is
   expected: the option belongs to this addon, not to Odoo core.
4. Restart Odoo.

The addon has no models, views or access rules: traces are not stored in Odoo (the backend
keeps them in its own database). Access is controlled by the server switch, the API key
and the *Settings* group.

## API

All routes use Odoo 19's JSON-2 request type with an API key, exactly like `/json/2`:

```sh
curl -X POST "$ODOO_URL/flow_tracer/v1/trace" \
  -H "Authorization: bearer $ODOO_API_KEY" \
  -H "X-Odoo-Database: $ODOO_DB" \
  -H "Content-Type: application/json" \
  -d '{"trace_id": "3f2b8c1e-6d4a-4c1e-9b7a-1a2b3c4d5e01",
       "model": "sale.order", "method": "action_confirm", "record_ids": [1]}'
```

| Route | Body | Answer |
|---|---|---|
| `POST /flow_tracer/v1/status` | `{}` | `{"addon_version", "odoo_version", "enabled", "is_admin", "recorder_available"}` |
| `POST /flow_tracer/v1/trace` | `trace_id` (UUID), `model`, `method`, `record_ids` (default `[]`), `context` (default `{}`), `kwargs` (default `{}`), `dry_run` (default `true`) | the trace ([format](../../docs/trace-format.md)) |
| `POST /flow_tracer/v1/signature` | `model`, `method` | `{"model", "method", "model_level", "module", "summary", "parameters": [{"name", "kind", "required", "default", "annotation"}]}` |

`/trace` answers:

| Status | When |
|---|---|
| `200` | Trace recorded. A run that raised is still `200`; the exception is the trace's `error`. |
| `400` | Invalid input |
| `401` | Missing or invalid API key |
| `403` | Switch off, user not in *Settings*, or a private method (same rules as JSON-2) |
| `404` | Unknown model or method |
| `422` | The call cannot be made: wrong or missing `kwargs`, or record ids for a model-level method |
| `503` | Recorder unavailable (Python < 3.12, or `sys.monitoring` tool id in use) |

The entrypoint is called as `records.method(**kwargs)`, checked first against the method's
signature, exactly like Odoo's JSON-2 API: keyword arguments only (JSON values, recordsets
as ids), and model-level (`@api.model`) methods without record ids.
`/signature` tells which parameters a method takes before tracing it. When an override
only passes `**kwargs` on (e.g. `sale`'s `message_post`), the parameters of the next
implementations along the MRO are included, up to the first one without `**kwargs`. The
`summary` is the first paragraph of the first docstring found along the MRO. Both routes
need the server switch and the *Settings* group, like `/trace`.

## How recording works

See [ADR 0001](../../docs/adr/0001-recorder-mechanism.md) for the decision and measurements.

| Module | Responsibility |
|---|---|
| `tracing/targets.py` | Which code is observed: every function defined in an addon model class plus `BaseModel.create/write/unlink`, mapped to its defining class (module, MRO position). Built once per registry. |
| `tracing/monitor.py` | `sys.monitoring` events on those code objects, **only while a trace runs** (reference counted). The current session lives in a `ContextVar`, so parallel requests do not mix. |
| `tracing/session.py` | Turns events into steps: call tree, `seq`, kind, `calls_super` (observed: a direct child runs the next implementation of the same method), field changes. |
| `tracing/values.py` | Field values from the ORM cache (never fetched or computed for the recorder) and bounded summaries, within the schema limits. |
| `tracing/noise.py` | Infrastructure models/methods that are not recorded (access rules, defaults, precision). |
| `tracing/runner.py` | Runs the entrypoint in a savepoint, `flush_all()` (pending recomputes are part of the flow), then rolls back (dry run). `cr.commit()` raises during a dry run. |

Field changes are captured for `write`, `create` and compute methods. A field computed for
the first time (not loaded before) is not a change.

**Cost** (`sale.order.action_confirm`, `sale_stock` demo data, 879 recorded steps): 29 ms
without, 50 ms with the recorder. About 12 ms of that is switching the events on and off
per trace, the rest about 10 µs per step. Without a running trace there is no overhead.

## Tests

Run against the test Odoo of the compose profile `test` (its configuration already
enables the switch, see `docker/odoo-test/odoo.conf`):

```sh
docker compose --profile test run --rm odoo-test \
  odoo -d <db> -i flow_tracer --test-enable --test-tags /flow_tracer \
  --stop-after-init --http-port 8070
```

The reference test for `sale.order.action_confirm` runs only in databases with
`sale_stock` (otherwise skipped with a reason). Create one with
`odoo -d odoo_trace --with-demo -i sale_stock,flow_tracer --stop-after-init`.

Lint (uses `odoo-addons/ruff.toml`): `ruff check odoo-addons && ruff format --check odoo-addons`.
