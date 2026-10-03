# Spike: recorder mechanism (M1)

Throw-away measurement scripts behind [ADR 0001](../../docs/adr/0001-recorder-mechanism.md).
They are kept for reproducibility, not as production code.

- `measure.py`: compares `sys.monitoring`, wrapping, `sys.setprofile` and the Odoo
  profiler on `sale.order.action_confirm` (run time, step count, enable/disable cost).
- `changes.py`: field changes from the ORM cache, infrastructure noise, and why wrapping
  sees more steps (needs `measure.py` first).

## Run

```sh
# database with sale_stock and demo data (once)
docker compose --profile test run --rm odoo-test \
  odoo -d odoo_trace --with-demo -i sale_stock --stop-after-init

printf 'exec(open("/spikes/recorder/measure.py").read())\nexec(open("/spikes/recorder/changes.py").read())\n' \
  | docker compose --profile test run --rm -T -v ./spikes:/spikes:ro odoo-test \
      odoo shell -d odoo_trace --no-http
```

Every run happens in a savepoint that is rolled back; the database is not changed.
