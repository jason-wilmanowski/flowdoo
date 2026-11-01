"""Views of a recorded trace, sized for a language model.

A whole trace is far too large to hand over at once (hundreds of KB). The overview says what
happened, find_steps pages through steps in detail, and step_detail shows one step in full.
Lists of steps and changes are cut at MAX_ANSWER_CHARS, and an answer says when it was cut.
"""

import json
from collections import Counter
from typing import Any

Trace = dict[str, Any]
Step = dict[str, Any]

MAX_ANSWER_CHARS = 20_000
MAX_LISTED_CALLS = 30
MAX_LISTED_FIELDS = 100
MAX_LISTED_TRANSITIONS = 3
MAX_LISTED_FAILURES = 5
MAX_LISTED_CHILDREN = 50
MAX_LISTED_RECORD_IDS = 20
MAX_SHORT_CHANGES = 5
MAX_SHORT_TEXT = 200
MAX_INLINE_VALUE = 80


def summary(trace: Trace) -> dict[str, Any]:
    entrypoint = trace["entrypoint"]
    return {
        "trace_id": trace["trace_id"],
        "entrypoint": f"{entrypoint['model']}.{entrypoint['method']}",
        "started_at": trace["started_at"],
        "step_count": len(trace["steps"]),
        "error": trace["error"],
    }


def overview(trace: Trace) -> dict[str, Any]:
    """What ran, how much of it, which values changed, whether and where it failed."""
    steps = _in_order(trace)
    failed = [step for step in steps if step["error"]]
    entrypoint = trace["entrypoint"]
    return {
        **summary(trace),
        "record_ids": entrypoint["record_ids"],
        "kwargs": entrypoint["kwargs"],
        "context": entrypoint["context"],
        "dry_run": trace["dry_run"],
        "odoo_version": trace["odoo_version"],
        "duration_ms": sum(step["duration_ms"] for step in steps if not step["parent_id"]),
        "kinds": _counts(step["kind"] for step in steps),
        "models": _counts(step["model"] for step in steps),
        "modules": _counts(step["module"] for step in steps if step["module"]),
        **_field_changes(steps),
        **_top_level_calls(steps),
        "failed_total": len(failed),
        **_failure_origins(steps, failed),
        "warnings": trace.get("warnings", []),
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
    offset: int = 0,
) -> dict[str, Any]:
    """Steps matching all given filters in execution order, one page at a time."""
    expected = {"model": model, "method": method, "module": module, "kind": kind}
    wanted = {key: value for key, value in expected.items() if value is not None}
    matches = [
        step
        for step in _in_order(trace)
        if all(step[key] == value for key, value in wanted.items())
        and (field is None or any(change["field"] == field for change in step["changes"]))
        and (not failed_only or step["error"])
    ]
    shown = _fitting([_short(step) for step in matches[offset : offset + limit]])
    next_offset = offset + len(shown)
    return {
        "total": len(matches),
        "offset": offset,
        "next_offset": next_offset if next_offset < len(matches) else None,
        "steps": shown,
    }


def step_detail(trace: Trace, step_id: str) -> dict[str, Any] | None:
    """One step in full, with its call path, children and overrides; None if unknown."""
    steps = _in_order(trace)
    step = next((candidate for candidate in steps if candidate["id"] == step_id), None)
    if step is None:
        return None
    children = [other for other in steps if other["parent_id"] == step_id]
    return {
        "step": {**step, "changes": _fitting(step["changes"])},
        "changes_total": len(step["changes"]),
        "path": _path(steps, step),
        "children_total": len(children),
        "children": [_label(child) for child in children[:MAX_LISTED_CHILDREN]],
        "implementations_seen": _implementations(steps, step),
    }


def _in_order(trace: Trace) -> list[Step]:
    return sorted(trace["steps"], key=lambda step: step["seq"])


def _counts(values: Any) -> dict[str, int]:
    return dict(Counter(values).most_common())


def _field_changes(steps: list[Step]) -> dict[str, Any]:
    """One line per changed field, cut to fit into one answer."""
    grouped: dict[str, list[tuple[Step, dict[str, Any]]]] = {}
    for step in steps:
        for change in step["changes"]:
            grouped.setdefault(f"{change['model']}.{change['field']}", []).append((step, change))
    lines = [_field_change_line(name, changes) for name, changes in grouped.items()]
    return {
        "changed_fields_total": len(lines),
        "changed_fields": _fitting(lines[:MAX_LISTED_FIELDS]),
    }


def _field_change_line(name: str, changes: list[tuple[Step, dict[str, Any]]]) -> str:
    """Per record the value before its first and after its last change; equal ones merged."""
    first_old: dict[int, Any] = {}
    last_new: dict[int, Any] = {}
    for _, change in changes:
        first_old.setdefault(change["record_id"], change["old"])
        last_new[change["record_id"]] = change["new"]
    transitions = list(
        dict.fromkeys(
            f"{_inline(first_old[record])} -> {_inline(last_new[record])}" for record in first_old
        )
    )
    shown = transitions[:MAX_LISTED_TRANSITIONS]
    if len(transitions) > len(shown):
        shown.append(f"+{len(transitions) - len(shown)} more")
    records = f"{len(first_old)} records, " if len(first_old) > 1 else ""
    return f"{name}: {', '.join(shown)} ({records}{len(changes)}x, first in {changes[0][0]['id']})"


def _top_level_calls(steps: list[Step]) -> dict[str, Any]:
    """The roots and what they call directly: the outline of the run."""
    root_ids = {step["id"] for step in steps if not step["parent_id"]}
    calls = [step for step in steps if not step["parent_id"] or step["parent_id"] in root_ids]
    return {
        "top_level_calls_total": len(calls),
        "top_level_calls": [_label(step) for step in calls[:MAX_LISTED_CALLS]],
    }


def _failure_origins(steps: list[Step], failed: list[Step]) -> dict[str, Any]:
    """Errors travel up the call tree, so report where they start: no failed child below."""
    parents_of_failed = {step["parent_id"] for step in failed}
    origins = [step for step in failed if step["id"] not in parents_of_failed]
    return {
        "failures_total": len(origins),
        "failures": [
            {"step": step["id"], "error": step["error"], "path": _path(steps, step)}
            for step in origins[:MAX_LISTED_FAILURES]
        ],
    }


def _fitting(items: list[Any]) -> list[Any]:
    """As many of ``items`` as fit into one answer, at least one."""
    shown: list[Any] = []
    size = 0
    for item in items:
        # Tool results are sent as indented JSON, nested in the answer, so measure that form.
        size += len(json.dumps({"answer": {"items": [item]}}, indent=2))
        if shown and size > MAX_ANSWER_CHARS:
            break
        shown.append(item)
    return shown


def _path(steps: list[Step], step: Step) -> list[str]:
    """The calls leading to ``step``, outermost first."""
    by_id = {candidate["id"]: candidate for candidate in steps}
    path: list[str] = []
    parent = by_id.get(step["parent_id"])
    # The bound protects against a cycle in the recorder's answer.
    while parent is not None and len(path) < len(steps):
        path.append(_label(parent))
        parent = by_id.get(parent["parent_id"])
    path.reverse()
    return path


def _implementations(steps: list[Step], step: Step) -> list[dict[str, Any]]:
    """Implementations of this method that ran in this trace, most derived first."""
    seen = {
        (other["mro_position"], other["module"], other["calls_super"])
        for other in steps
        if other["model"] == step["model"] and other["method"] == step["method"]
    }
    ordered = sorted(seen, key=lambda item: (item[0] is None, item[0] or 0, item[1] or ""))
    return [
        {"mro_position": position, "module": module, "calls_super": calls_super}
        for position, module, calls_super in ordered
    ]


def _short(step: Step) -> dict[str, Any]:
    record_ids = step["record_ids"]
    return {
        "id": step["id"],
        "parent_id": step["parent_id"],
        "kind": step["kind"],
        "call": f"{step['model']}.{step['method']}",
        "module": step["module"],
        "mro_position": step["mro_position"],
        "calls_super": step["calls_super"],
        "record_ids_total": len(record_ids),
        "record_ids": record_ids[:MAX_LISTED_RECORD_IDS],
        "args": _cut(step["args_summary"]),
        "returns": _cut(step["return_summary"]),
        "duration_ms": step["duration_ms"],
        "changes_total": len(step["changes"]),
        "changes": [_short_change(change) for change in step["changes"][:MAX_SHORT_CHANGES]],
        "error": step["error"],
    }


def _short_change(change: dict[str, Any]) -> str:
    return (
        f"{change['model']}({change['record_id']}).{change['field']}: "
        f"{_inline(change['old'])} -> {_inline(change['new'])}"
    )


def _label(step: Step) -> str:
    changed = sorted({change["field"] for change in step["changes"]})
    suffix = f" changed={','.join(changed[:MAX_SHORT_CHANGES])}" if changed else ""
    failed = " FAILED" if step["error"] else ""
    return f"{step['id']} {step['kind']} {step['model']}.{step['method']}{suffix}{failed}"


def _inline(value: Any) -> str:
    return _cut(repr(value), MAX_INLINE_VALUE) or ""


def _cut(text: str | None, limit: int = MAX_SHORT_TEXT) -> str | None:
    if text is None or len(text) <= limit:
        return text
    return f"{text[:limit]}... [{len(text) - limit} more characters, see get_step]"
