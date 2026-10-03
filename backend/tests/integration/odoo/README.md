# Tests against the Odoo 19 test container

Tests in this folder are marked `odoo` and talk to the real Odoo 19 from the compose
profile `test`. They are skipped (with a reason) unless `ODOO_TEST_URL`, `ODOO_TEST_DB`
and `ODOO_TEST_API_KEY` are set.

One-time setup (from the repository root):

```sh
# 1. Create a database with the flow_tracer addon (mounted from odoo-addons/)
docker compose --profile test up -d odoo-test-db
docker compose --profile test run --rm odoo-test odoo -d odoo_test -i base,flow_tracer --stop-after-init

# 2. Create an API key for the admin user and print it
docker compose --profile test run --rm -T odoo-test odoo shell -d odoo_test --no-http <<'PY'
key = env['res.users.apikeys'].with_user(env.ref('base.user_admin')).sudo()._generate(
    None, 'flow-tracer-tests', None)
env.cr.commit()
print('ODOO_TEST_API_KEY=' + key)
PY

# 3. Put ODOO_TEST_URL=http://localhost:8069, ODOO_TEST_DB=odoo_test and the key into .env
# 4. Start Odoo
docker compose --profile test up -d odoo-test
```

Run only these tests: `uv run pytest -m odoo` (in `backend/`).
