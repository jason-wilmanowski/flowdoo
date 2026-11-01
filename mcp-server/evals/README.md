# A/B comparison: Claude Code with and without Flowdoo

Measures what the MCP server changes for an AI client: tokens, cost, turns, duration and
whether the answer is right.

## Setup of the comparison

- **Same in both arms:** prompt, model, a copy of the Odoo source, and `odoo shell` on the test
  server. An agent without Flowdoo is not helpless, so this is the fair baseline.
- **Only difference:** the `flowdoo` arm also has the MCP server.
- **Isolation:** runs start in a folder outside the repo, without settings from this project.
- **Order:** runs are shuffled, so drift over time does not favour one arm.
- **Repeats:** three per task and arm by default. Results are medians.

## Tasks

`tasks.json` holds the prompts and the rubric, fixed before the first run.

| Category | Tasks | Expectation |
|---|---|---|
| `flow` | `hook_after_delivery`, `write_chain`, `created_records` | Flowdoo should help |
| `neutral` | `failure_diagnosis` | Small difference |
| `branches` | `no_delivery_conditions` | A trace shows one path only, so reading code should matter |
| `control` | `delivery_button` | No benefit, shows the cost of the extra tools |

The rubric was checked against the Odoo source. The counts in `created_records` were checked
by counting table rows in a rolled-back `odoo shell` run as admin, not only against a trace.

## Procedure

Needs the `odoo-test` container and `mcp-server/.env`. Run from `mcp-server/`:

```
python3 evals/ab_eval.py prepare                 # copies the Odoo source, about 1.5 GB
python3 evals/ab_eval.py run --dry-run           # lists the runs and the cost limit
python3 evals/ab_eval.py run --reps 1            # pilot
python3 evals/ab_eval.py run --reps 3            # keeps finished runs, adds the rest
python3 evals/ab_eval.py sheet                   # blind grading sheet
python3 evals/ab_eval.py report                  # results table
```

Grade `results/grading_sheet.md` by filling `results/grades.todo` with `true` or `false`, ideally
without opening `results/blind.key` or the result files. `results/` is git-ignored.

## Limits

- **Selection:** five of the six tasks concern backend flows, so the results apply to that work
  and not to Odoo development as a whole.
- **No code changes:** the tasks only ask for answers, so rework after a wrong change is not
  measured.
- **Small sample:** three repeats show a direction, not statistical significance.
- **One database:** demo data on one server, with one small order.
- **Blinding is partial:** step ids and tool names are hidden, but style can still give an arm
  away.
- **Costs:** `cost_usd` is what the CLI reports, not necessarily what a subscription pays.
