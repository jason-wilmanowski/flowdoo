"""One recording: turns monitoring events into the steps of schema v0.2.0.

Invariant: every PY_START of an indexed code object pushes exactly one entry onto
``_stack`` and the matching PY_RETURN/PY_UNWIND pops it, whether or not the call becomes
a step (noise, step limit). Callbacks must never raise into the observed code; a failure
stops the recording and is reported as the trace error.
"""

import inspect
import logging
import time

from odoo.models import BaseModel

from . import values
from .noise import is_noise
from .targets import Target, TargetIndex

_logger = logging.getLogger(__name__)

MAX_STEPS = 20000


class _Open:
    """A running call. ``step`` is None if the call is not recorded."""

    __slots__ = ("code", "records", "started", "step", "watch")

    def __init__(self, code, step=None, records=None, watch=None):
        self.code = code
        self.step = step
        self.records = records
        self.watch = watch  # (field names, values before) for change detection
        self.started = time.perf_counter()


class TraceSession:
    __slots__ = ("_index", "_open_steps", "_stack", "failure", "max_steps", "steps", "truncated")

    def __init__(self, index: TargetIndex, max_steps: int | None = None):
        self._index = index
        self._stack: list[_Open] = []
        self._open_steps: list[dict] = []  # recorded steps that are still running
        self.steps: list[dict] = []
        self.max_steps = MAX_STEPS if max_steps is None else max_steps
        self.truncated = False
        self.failure: BaseException | None = None

    # ------------------------------------------------------------------ events
    def on_start(self, code, frame) -> None:
        target = self._index.targets.get(code)
        if target is None:  # enabled for another registry's session
            return
        if self.failure is not None:
            self._stack.append(_Open(code))
            return
        try:
            self._stack.append(self._start(code, target, frame))
        except Exception as exc:
            self._fail(exc)
            self._stack.append(_Open(code))

    def on_return(self, code, retval) -> None:
        if code in self._index.targets:
            self._end(code, retval=retval)

    def on_unwind(self, code, exc: BaseException) -> None:
        if code in self._index.targets:
            self._end(code, exc=exc)

    # ------------------------------------------------------------------ steps
    def _start(self, code, target: Target, frame) -> _Open:
        local_vars = frame.f_locals  # a fresh dict per access in 3.12: read it once
        records = local_vars.get("self")
        if not isinstance(records, BaseModel):
            return _Open(code)
        model = records._name
        if is_noise(model, target.method):
            return _Open(code)
        if len(self.steps) >= self.max_steps:
            self.truncated = True
            return _Open(code)

        position = self._index.mro_position(type(records), target)
        parent = self._open_steps[-1] if self._open_steps else None
        if (
            parent is not None
            and parent["method"] == target.method
            and parent["model"] == model
            and position is not None
            and parent["mro_position"] is not None
            and position > parent["mro_position"]
        ):
            parent["calls_super"] = True

        computed = self._index.computes.get((model, target.method))
        seq = len(self.steps) + 1
        step = {
            "id": f"s{seq}",
            "parent_id": parent["id"] if parent else None,
            "seq": seq,
            "kind": "compute" if computed else target.kind,
            "model": model,
            "method": target.method,
            "module": target.module,
            "mro_position": position,
            "calls_super": False,
            "record_ids": values.ids_of(records),
            "args_summary": _args_summary(code, local_vars),
            "return_summary": None,
            "changes": [],
            "duration_ms": 0.0,
            "error": None,
        }
        self.steps.append(step)
        self._open_steps.append(step)
        return _Open(code, step, records, self._watch(target, records, local_vars, computed))

    def _watch(self, target: Target, records, local_vars, computed):
        """Field values to compare after the call: write vals, computed fields."""
        if target.cls is BaseModel and target.method == "write":
            fnames = tuple(local_vars.get("vals") or ())
            before = values.peek(records.env, records._name, records._ids, fnames)
            missing = [f for (_rid, f), v in before.items() if v is values.MISSING]
            if missing:
                stored = values.read_columns(records.env, records._name, records._ids, missing)
                before.update(stored)
            return fnames, before
        if target.cls is BaseModel and target.method == "create":
            vals_list = local_vars.get("vals_list") or ()
            if isinstance(vals_list, dict):
                vals_list = [vals_list]
            fnames = tuple(dict.fromkeys(f for vals in vals_list for f in vals))
            return fnames, None  # new records: everything is a change from null
        if computed:
            return computed, values.peek(records.env, records._name, records._ids, computed)
        return None

    def _end(self, code, retval=None, exc=None) -> None:
        while self._stack:
            entry = self._stack.pop()
            if entry.step is not None:
                self._open_steps.pop()
                if self.failure is None:
                    try:
                        self._finish(entry, retval, exc, matched=entry.code is code)
                    except Exception as error:
                        self._fail(error)
            if entry.code is code:
                return

    def _finish(self, entry: _Open, retval, exc, matched: bool) -> None:
        step = entry.step
        step["duration_ms"] = round((time.perf_counter() - entry.started) * 1000, 3)
        if not matched:  # left without its own return event (should not happen)
            return
        if exc is not None:
            step["error"] = values.error_of(exc)
            return
        step["return_summary"] = values.summary(retval)
        if entry.watch is None:
            return
        fnames, before = entry.watch
        records = entry.records
        if before is None:  # create: the returned records are the new ones
            records = retval if isinstance(retval, BaseModel) else records.browse()
        step["changes"] = _changes(records, fnames, before)

    def _fail(self, exc: Exception) -> None:
        _logger.exception("flow_tracer: recording stopped")
        self.failure = exc


def _changes(records, fnames, before) -> list[dict]:
    after = values.peek(records.env, records._name, records._ids, fnames)
    fields = records._fields
    changes = []
    for (rid, fname), new in after.items():
        if new is values.MISSING or not isinstance(rid, int):
            continue
        if before is None:
            old = None
        else:
            old = before.get((rid, fname), values.MISSING)
            if old is values.MISSING or old == new:
                continue  # first computation or unchanged
        field = fields[fname]
        old_value, new_value = values.field_value(field, old), values.field_value(field, new)
        if old_value != new_value:
            changes.append(
                {
                    "model": records._name,
                    "record_id": rid,
                    "field": fname,
                    "old": old_value,
                    "new": new_value,
                }
            )
    return changes[: values.IDS_MAX]


def _args_summary(code, local_vars) -> str | None:
    """Arguments without ``self``, bounded via reprlib."""
    count = (
        code.co_argcount
        + code.co_kwonlyargcount
        + bool(code.co_flags & inspect.CO_VARARGS)
        + bool(code.co_flags & inspect.CO_VARKEYWORDS)
    )
    names = code.co_varnames[1:count]
    if not names:
        return None
    parts = [f"{name}={values.summary(local_vars.get(name))}" for name in names]
    return values.truncate(", ".join(parts))
