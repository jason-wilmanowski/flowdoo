# flow_tracer (Odoo 19 addon)

Recorder side of [Flowdoo](../../README.md). It is installed into **your existing Odoo 19**
and answers the Flowdoo backend.

> [!WARNING]
> Development databases only. Never install or enable it on a production server.

## State

| Part | State |
|---|---|
| Module skeleton, server switch, `POST /flow_tracer/v1/status` | ✅ |
| Recording a run (`dry_run`, steps, field changes) | ⏳ after the recorder spike (M1) |

The addon has no models, views or access rules yet: traces are not stored in Odoo (the
backend keeps them in its own database), so there is nothing to persist or secure on the
model level.

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

Without step 3 the addon reports `enabled: false` and will refuse to record.

## API

All routes use Odoo 19's JSON-2 request type with an API key, exactly like `/json/2`:

```sh
curl -X POST "$ODOO_URL/flow_tracer/v1/status" \
  -H "Authorization: bearer $ODOO_API_KEY" \
  -H "X-Odoo-Database: $ODOO_DB" \
  -H "Content-Type: application/json" -d '{}'
```

| Route | Answer |
|---|---|
| `POST /flow_tracer/v1/status` | `{"addon_version", "odoo_version", "enabled", "is_admin"}` |

`401` without a valid API key. `is_admin` tells whether the key's user is in the
*Settings* group (`base.group_system`), which recording will require.

## Tests

Run against the test Odoo of the compose profile `test` (its configuration already
enables the switch, see `docker/odoo-test/odoo.conf`):

```sh
docker compose --profile test run --rm odoo-test \
  odoo -d odoo_test -i flow_tracer --test-enable --test-tags /flow_tracer \
  --stop-after-init --http-port 8070
```

Lint (uses `odoo-addons/ruff.toml`): `ruff check odoo-addons && ruff format --check odoo-addons`.
