"""Compact views of a recorded trace: a whole trace is far too large to hand to a model."""

from collections import Counter
from typing import Any

Trace = dict[str, Any]


def overview(trace: Trace) -> dict[str, Any]:
    """What ran, how much of it, what it touched and whether it failed."""
    steps = trace["steps"]
    entrypoint = trace["entrypoint"]
    return {
        "trace_id": trace["trace_id"],
        "entrypoint": f"{entrypoint['model']}.{entrypoint['method']}",
        "record_ids": entrypoint["record_ids"],
        "dry_run": trace["dry_run"],
        "odoo_version": trace["odoo_version"],
        "started_at": trace["started_at"],
        "step_count": len(steps),
        "error": trace["error"],
        "kinds": dict(Counter(step["kind"] for step in steps)),
        "models": sorted({step["model"] for step in steps}),
        "modules": sorted({step["module"] for step in steps if step["module"]}),
        "changed_fields": sorted(
            {f"{change['model']}.{change['field']}" for step in steps for change in step["changes"]}
        ),
        "failed_steps": [step["id"] for step in steps if step["error"]],
    }


def find_steps(
    trace: Trace,
    *,
    model: str | None = None,
    method: str | None = None,
    module: str | None = None,
    kind: str | None = None,
    field: str | None = None,
    failed_only: bool = False,
    limit: int = 20,
) -> dict[str, Any]:
    """Steps matching all given filters, in execution order; none if no filter is given."""
    expected = {"model": model, "method": method, "module": module, "kind": kind}
    wanted = {key: value for key, value in expected.items() if value is not None}
    if not wanted and field is None and not failed_only:
        return {"steps_total": 0, "steps": []}
    matches = [
        step
        for step in sorted(trace["steps"], key=lambda step: step["seq"])
        if all(step[key] == value for key, value in wanted.items())
        and (field is None or any(change["field"] == field for change in step["changes"]))
        and (not failed_only or step["error"])
    ]
    return {"steps_total": len(matches), "steps": matches[:limit]}
