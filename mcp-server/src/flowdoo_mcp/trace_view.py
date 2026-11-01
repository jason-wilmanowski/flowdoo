"""Compact views of a recorded trace: a whole trace is far too large to hand to a model."""

from collections import Counter
from typing import Any

Trace = dict[str, Any]
Step = dict[str, Any]

MAX_LISTED_CHILDREN = 50


def overview(trace: Trace) -> dict[str, Any]:
    """What ran, how much of it, what it touched and whether it failed."""
    steps = trace["steps"]
    return {
        **summary(trace),
        "record_ids": trace["entrypoint"]["record_ids"],
        "dry_run": trace["dry_run"],
        "odoo_version": trace["odoo_version"],
        "kinds": dict(Counter(step["kind"] for step in steps)),
        "models": sorted({step["model"] for step in steps}),
        "modules": sorted({step["module"] for step in steps if step["module"]}),
        "changed_fields": sorted(
            {f"{change['model']}.{change['field']}" for step in steps for change in step["changes"]}
        ),
        "failed_steps": [step["id"] for step in steps if step["error"]],
    }


def summary(trace: Trace) -> dict[str, Any]:
    entrypoint = trace["entrypoint"]
    return {
        "trace_id": trace["trace_id"],
        "entrypoint": f"{entrypoint['model']}.{entrypoint['method']}",
        "started_at": trace["started_at"],
        "step_count": len(trace["steps"]),
        "error": trace["error"],
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
    limit: int = 50,
) -> dict[str, Any]:
    """Steps matching all given filters, in execution order, as one short line each."""
    expected = {"model": model, "method": method, "module": module, "kind": kind}
    wanted = {key: value for key, value in expected.items() if value is not None}
    matches = [
        step
        for step in sorted(trace["steps"], key=lambda step: step["seq"])
        if all(step[key] == value for key, value in wanted.items())
        and (field is None or any(change["field"] == field for change in step["changes"]))
        and (not failed_only or step["error"])
    ]
    return {"total": len(matches), "steps": [_short(step) for step in matches[:limit]]}


def step_detail(trace: Trace, step_id: str) -> dict[str, Any] | None:
    """One step in full, with the path to it and its direct children; None if unknown."""
    by_id = {step["id"]: step for step in trace["steps"]}
    step = by_id.get(step_id)
    if step is None:
        return None
    children = [other for other in trace["steps"] if other["parent_id"] == step_id]
    children.sort(key=lambda child: child["seq"])
    return {
        "step": step,
        "path": _path(by_id, step),
        "children_total": len(children),
        "children": [_label(child) for child in children[:MAX_LISTED_CHILDREN]],
    }


def _path(by_id: dict[str, Step], step: Step) -> list[str]:
    """The calls leading to ``step``, outermost first."""
    path: list[str] = []
    parent_id = step["parent_id"]
    while parent_id is not None:
        parent = by_id[parent_id]
        path.append(_label(parent))
        parent_id = parent["parent_id"]
    path.reverse()
    return path


def _short(step: Step) -> dict[str, Any]:
    return {
        "id": step["id"],
        "parent_id": step["parent_id"],
        "kind": step["kind"],
        "call": f"{step['model']}.{step['method']}",
        "module": step["module"],
        "changed": sorted({change["field"] for change in step["changes"]}),
        "failed": step["error"] is not None,
    }


def _label(step: Step) -> str:
    return f"{step['id']} {step['model']}.{step['method']}"
