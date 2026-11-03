"""Views of a recorded trace, sized for a language model.

Every answer stays in the client's context and is sent again each round, so views leave out
empty values and framework noise. The overview says what happened, explain_field who changed
a value, find_steps pages through steps, and step_detail shows one step in full. Lists are cut
at MAX_ANSWER_CHARS, and an answer says when it was cut.
"""

import difflib
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
MAX_LISTED_COUNTS = 10
MAX_LISTED_CHANGES = 30
MAX_SHORT_CHANGES = 5
MAX_SHORT_TEXT = 200
MAX_INLINE_VALUE = 80
MAX_ECHOED_INPUT = 300
MAX_ERROR_TEXT = 300
MIN_SHOWN_DURATION_MS = 10
MAX_LISTED_SQL = 15
MAX_LISTED_DIFFERENCES = 15
MAX_COMPARED_STEPS = 6000

ORM_KINDS = frozenset({"orm_create", "orm_write", "orm_unlink"})
# Called around nearly every field computation, they say nothing about the workflow.
NOISE_METHODS = frozenset({"_compute_field_value", "_track_prepare"})
TRUNCATED_ERROR = "flow_tracer.TraceTruncated"
GENERATED_FIELDS = frozenset({"name", "message_id", "origin", "reference", "date_order"})
NO_CHANGE_HINT = (
    "No change of this field was recorded. A trace records ORM changes only: a direct SQL write "
    "(cr.execute) does not appear, so search the code for the field if it should have changed."
)


def summary(trace: Trace) -> dict[str, Any]:
    entrypoint = trace["entrypoint"]
    return {
        "trace_id": trace["trace_id"],
        "entrypoint": f"{entrypoint['model']}.{entrypoint['method']}",
        "record_ids": entrypoint["record_ids"][:MAX_LISTED_RECORD_IDS],
        "kwargs": _echoed(entrypoint["kwargs"]),
        "step_count": len(trace["steps"]),
        "error": _run_error(trace),
    }


def overview(trace: Trace) -> dict[str, Any]:
    """What ran, how much of it, which values changed, whether and where it failed."""
    steps = _in_order(trace)
    failed = [step for step in steps if step["error"]]
    answer = {
        **summary(trace),
        "context": _echoed(trace["entrypoint"]["context"]),
        "duration_ms": round(sum(s["duration_ms"] for s in steps if not s["parent_id"]), 1),
        "kinds": _counts(step["kind"] for step in steps),
        "models": _counts(step["model"] for step in steps),
        "modules": _counts(step["module"] for step in steps if step["module"]),
        **_field_changes(steps),
        **_top_level_calls(steps),
        "failed_total": len(failed),
        **_failure_origins(steps, failed),
    }
    if trace.get("raw_sql_writes"):
        answer["raw_sql_writes"] = _sql_lines(trace["raw_sql_writes"])
    if _is_truncated(trace):
        answer["recording_truncated"] = trace["error"]["message"]
    if trace.get("warnings"):
        answer["warnings"] = trace["warnings"]
    return answer


def explain_field(
    trace: Trace, field: str, *, model: str | None = None, record_id: int | None = None
) -> dict[str, Any]:
    """Every change of a field, each with the business method behind it and its call path."""
    steps = _in_order(trace)
    by_id = {step["id"]: step for step in steps}
    found = [
        _explained_change(step, change, by_id, steps)
        for step in steps
        for change in step["changes"]
        if change["field"] == field
        and (model is None or change["model"] == model)
        and (record_id is None or change["record_id"] == record_id)
    ]
    shown = fitting(found[:MAX_LISTED_CHANGES])
    answer: dict[str, Any] = {"field": field, "changes_total": len(found), "changes": shown}
    sql = [
        line
        for line in _sql_lines(trace.get("raw_sql_writes", []))
        if f" {field}" in line or f",{field}" in line
    ]
    if sql:
        answer["raw_sql_writes"] = sql
    if not found and not sql:
        answer["hint"] = NO_CHANGE_HINT
    return answer


def compare_traces(first: Trace, second: Trace) -> dict[str, Any]:
    """Where two runs part ways: the first different step and what differs in total."""
    a_steps, b_steps = _comparable(first), _comparable(second)
    answer: dict[str, Any] = {
        "a": summary(first),
        "b": summary(second),
        **_step_differences(first, second, a_steps, b_steps),
    }
    values = _value_differences(a_steps, b_steps)
    if values:
        answer["different_values"] = values[:MAX_LISTED_DIFFERENCES]
    sql_a, sql_b = (
        set(_sql_lines(first.get("raw_sql_writes", []))),
        set(_sql_lines(second.get("raw_sql_writes", []))),
    )
    if sql_a != sql_b:
        answer["raw_sql_only_in_a"] = sorted(sql_a - sql_b)
        answer["raw_sql_only_in_b"] = sorted(sql_b - sql_a)
    return answer


def _comparable(trace: Trace) -> list[Step]:
    return [step for step in _in_order(trace) if step["method"] not in NOISE_METHODS]


def _step_key(step: Step) -> tuple[str, str, str, Any]:
    return (step["kind"], step["model"], step["method"], step["module"])


def _step_differences(first: Trace, second: Trace, a: list[Step], b: list[Step]) -> dict[str, Any]:
    if max(len(a), len(b)) > MAX_COMPARED_STEPS:
        return {"note": f"Too long to compare in detail, limit {MAX_COMPARED_STEPS} steps"}
    keys_a, keys_b = [_step_key(s) for s in a], [_step_key(s) for s in b]
    blocks = difflib.SequenceMatcher(None, keys_a, keys_b, autojunk=False).get_opcodes()
    differing = [block for block in blocks if block[0] != "equal"]
    if not differing:
        return {"same_steps": True}
    only_a = [a[i] for _, i1, i2, _, _ in differing for i in range(i1, i2)]
    only_b = [b[j] for _, _, _, j1, j2 in differing for j in range(j1, j2)]
    _, i1, i2, j1, j2 = differing[0]
    return {
        "same_steps": False,
        "first_difference": {
            "a": _difference_side(first, a[i1]) if i1 < i2 else None,
            "b": _difference_side(second, b[j1]) if j1 < j2 else None,
            "after": _label(a[i1 - 1]) if i1 else None,
        },
        "only_in_a": _call_counts(only_a),
        "only_in_b": _call_counts(only_b),
    }


def _difference_side(trace: Trace, step: Step) -> dict[str, Any]:
    return {"step": _label(step), "module": _module(step), "path": _path(_in_order(trace), step)}


def _call_counts(steps: list[Step]) -> dict[str, int]:
    counted = Counter(f"{step['model']}.{step['method']}" for step in steps)
    return dict(counted.most_common(MAX_LISTED_DIFFERENCES))


def _value_differences(a: list[Step], b: list[Step]) -> list[str]:
    """Last value per field; ids and generated values differ in every run and are left out."""
    first, second = _last_values(a), _last_values(b)
    lines = []
    for name in first.keys() & second.keys():
        (a_value, a_step), (b_value, b_step) = first[name], second[name]
        if (
            a_value != b_value
            and not isinstance(a_value, list)
            and name.split(".")[-1] not in GENERATED_FIELDS
        ):
            lines.append(
                f"{name}: a {_inline(a_value)} ({a_step}), b {_inline(b_value)} ({b_step})"
            )
    return sorted(lines)


def _last_values(steps: list[Step]) -> dict[str, tuple[Any, str]]:
    values: dict[str, tuple[Any, str]] = {}
    for step in steps:
        for change in step["changes"]:
            values[f"{change['model']}.{change['field']}"] = (change["new"], step["id"])
    return values


def _sql_lines(writes: list[dict[str, Any]]) -> list[str]:
    lines = [
        f"{w['operation']} {w['table']} {','.join(w['columns'])} "
        f"by {w['method']} at {w['file']}:{w['line']}"
        for w in writes
    ]
    return list(dict.fromkeys(lines))[:MAX_LISTED_SQL]


def find_steps(
    trace: Trace,
    *,
    model: str | None = None,
    method: str | None = None,
    module: str | None = None,
    kind: str | None = None,
    field: str | None = None,
    record_id: int | None = None,
    under: str | None = None,
    exclude_modules: list[str] | None = None,
    failed_only: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Steps matching all given filters in execution order, one page at a time."""
    steps = _in_order(trace)
    expected = {"model": model, "method": method, "module": module, "kind": kind}
    wanted = {key: value for key, value in expected.items() if value is not None}
    within = _subtree(steps, under) if under else None
    excluded = set(exclude_modules or ())
    matches = [
        step
        for step in steps
        if all(step[key] == value for key, value in wanted.items())
        and (within is None or step["id"] in within)
        and step["module"] not in excluded
        and (field is None or any(change["field"] == field for change in step["changes"]))
        and (record_id is None or _touches_record(step, record_id))
        and (not failed_only or step["error"])
    ]
    shown = fitting([_short(step) for step in matches[offset : offset + limit]])
    next_offset = offset + len(shown)
    return {
        "total": len(matches),
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
        "step": {**step, "changes": fitting(step["changes"])},
        "changes_total": len(step["changes"]),
        "path": _path(steps, step),
        "children_total": len(children),
        "children": [_label(child) for child in children[:MAX_LISTED_CHILDREN]],
        "implementations_seen": _implementations(steps, step),
    }


def _in_order(trace: Trace) -> list[Step]:
    return sorted(trace["steps"], key=lambda step: step["seq"])


def _is_truncated(trace: Trace) -> bool:
    return bool(trace["error"]) and trace["error"].get("type") == TRUNCATED_ERROR


def _run_error(trace: Trace) -> dict[str, Any] | None:
    """A cut recording is no failure: the run completed, so it is reported apart."""
    if not trace["error"] or _is_truncated(trace):
        return None
    return _short_error(trace["error"])


def _short_error(error: dict[str, Any]) -> dict[str, Any]:
    return {**error, "message": _cut(error.get("message"), MAX_ERROR_TEXT)}


def _echoed(values: dict[str, Any]) -> str | None:
    """Input of the client, which it already knows, and which can be very large."""
    return _cut(json.dumps(values, default=str), MAX_ECHOED_INPUT) if values else None


def _counts(values: Any) -> dict[str, int]:
    counted = Counter(values).most_common()
    shown = dict(counted[:MAX_LISTED_COUNTS])
    rest = sum(count for _, count in counted[MAX_LISTED_COUNTS:])
    return {**shown, "(others)": rest} if rest else shown


def _field_changes(steps: list[Step]) -> dict[str, Any]:
    """Changed values one by one; fields only filled on new records as one line per model."""
    grouped: dict[str, list[tuple[Step, dict[str, Any]]]] = {}
    for step in steps:
        for change in step["changes"]:
            grouped.setdefault(f"{change['model']}.{change['field']}", []).append((step, change))
    by_id = {step["id"]: step for step in steps}
    changed = {
        name: changes
        for name, changes in grouped.items()
        if any(change["old"] is not None for _, change in changes)
    }
    lines = [_field_change_line(name, changes, by_id) for name, changes in changed.items()]
    filled = _filled_fields({k: v for k, v in grouped.items() if k not in changed})
    return {
        "changed_fields_total": len(grouped),
        "changed_fields": fitting(lines[:MAX_LISTED_FIELDS]),
        **({"filled_fields": filled} if filled else {}),
    }


def _filled_fields(grouped: dict[str, list[tuple[Step, dict[str, Any]]]]) -> list[str]:
    per_model: dict[str, list[str]] = {}
    for changes in grouped.values():
        per_model.setdefault(changes[0][1]["model"], []).append(changes[0][1]["field"])
    return [f"{model}: {', '.join(fields)}" for model, fields in per_model.items()]


def _field_change_line(
    name: str, changes: list[tuple[Step, dict[str, Any]]], by_id: dict[str, Step]
) -> str:
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
    first = changes[0][0]
    return (
        f"{name}: {', '.join(shown)} ({records}{len(changes)}x, first in {first['id']}, "
        f"by {_business_call(first, by_id)})"
    )


def _business_caller(step: Step, by_id: dict[str, Step]) -> Step:
    """The method a developer would look at: the nearest one above the ORM's write chain."""
    current: Step | None = step
    seen = 0
    while current is not None and current["kind"] in ORM_KINDS and seen < len(by_id):
        current = by_id.get(current["parent_id"])
        seen += 1
    return current or step


def _business_call(step: Step, by_id: dict[str, Step]) -> str:
    caller = _business_caller(step, by_id)
    return f"{caller['model']}.{caller['method']} [{_module(caller)}]"


def _explained_change(
    step: Step, change: dict[str, Any], by_id: dict[str, Step], steps: list[Step]
) -> dict[str, Any]:
    return {
        "step": step["id"],
        "record": f"{change['model']}({change['record_id']})",
        "old": change["old"],
        "new": change["new"],
        "by": _business_call(step, by_id),
        "path": _path(steps, step),
    }


def _top_level_calls(steps: list[Step]) -> dict[str, Any]:
    """The roots and what they call directly: the outline of the run."""
    root_ids = {step["id"] for step in steps if not step["parent_id"]}
    calls = [
        step
        for step in steps
        if (not step["parent_id"] or step["parent_id"] in root_ids)
        and step["method"] not in NOISE_METHODS
    ]
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
            {"step": step["id"], "error": _short_error(step["error"]), "path": _path(steps, step)}
            for step in origins[:MAX_LISTED_FAILURES]
        ],
    }


def _subtree(steps: list[Step], root_id: str) -> set[str]:
    """A step and everything below it; a parent always runs before its children."""
    within = {root_id}
    for step in steps:
        if step["parent_id"] in within:
            within.add(step["id"])
    return within


def _touches_record(step: Step, record_id: int) -> bool:
    return record_id in step["record_ids"] or any(
        change["record_id"] == record_id for change in step["changes"]
    )


def fitting(items: list[Any]) -> list[Any]:
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
    parents: list[Step] = []
    parent = by_id.get(step["parent_id"])
    # The bound protects against a cycle in the recorder's answer.
    while parent is not None and len(parents) < len(steps):
        parents.append(parent)
        parent = by_id.get(parent["parent_id"])
    parents.reverse()
    # Overrides of one method repeat its name many times; the outermost one is enough here.
    shown = [
        current
        for previous, current in zip([None, *parents], parents, strict=False)
        if previous is None or _call(previous) != _call(current)
    ]
    return [_label(item) for item in shown]


def _call(step: Step) -> str:
    return f"{step['model']}.{step['method']}"


def _implementations(steps: list[Step], step: Step) -> list[dict[str, Any]]:
    """Implementations of this method that ran in this trace, most derived first."""
    seen: dict[tuple[Any, Any, Any], str] = {}
    for other in steps:
        if other["model"] == step["model"] and other["method"] == step["method"]:
            key = (other["mro_position"], _module(other), other["calls_super"])
            seen.setdefault(key, other["id"])
    ordered = sorted(seen, key=lambda item: (item[0] is None, item[0] or 0, item[1]))
    return [
        {"mro_position": key[0], "module": key[1], "calls_super": key[2], "step": seen[key]}
        for key in ordered
    ]


def _module(step: Step) -> str:
    """The ORM's own create, write and unlink are recorded without a module."""
    if step["module"]:
        return str(step["module"])
    return "base" if step["kind"] in ORM_KINDS else "unknown"


def _short(step: Step) -> dict[str, Any]:
    """Empty values are left out: they make up most of a step and cost tokens every round."""
    record_ids = step["record_ids"]
    short: dict[str, Any] = {
        "id": step["id"],
        "kind": step["kind"],
        "call": f"{step['model']}.{step['method']}",
        "module": _module(step),
        "mro_position": step["mro_position"],
    }
    optional = {
        "parent_id": step["parent_id"],
        "calls_super": step["calls_super"],
        "record_ids": record_ids[:MAX_LISTED_RECORD_IDS],
        "args": _cut(step["args_summary"]),
        "returns": _cut(step["return_summary"]),
        "changes": [_short_change(change) for change in step["changes"][:MAX_SHORT_CHANGES]],
        "error": _short_error(step["error"]) if step["error"] else None,
    }
    short.update({key: value for key, value in optional.items() if value})
    if len(record_ids) > MAX_LISTED_RECORD_IDS:
        short["record_ids_total"] = len(record_ids)
    if len(step["changes"]) > MAX_SHORT_CHANGES:
        short["changes_total"] = len(step["changes"])
    if step["duration_ms"] >= MIN_SHOWN_DURATION_MS:
        short["duration_ms"] = step["duration_ms"]
    return short


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
