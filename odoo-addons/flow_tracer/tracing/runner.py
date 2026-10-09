"""Run one entrypoint under the recorder and build the trace (schema v0.2.0).

Dry run (default): the run happens inside a savepoint, followed by ``flush_all()`` so
pending recomputes and constraints are part of the flow. Afterwards the savepoint is
rolled back and the transaction's caches, pending computations and post-commit hooks are
discarded. While a dry run is active ``cr.commit()`` raises, so code under trace cannot
persist anything. Side effects are not blocked (ADR 0001): use neutralised databases.
"""

import copy
import datetime
import inspect
from contextlib import contextmanager

from odoo import release
from odoo.service.model import get_public_method

from . import values
from .monitor import CURRENT_SESSION, MONITOR
from .session import TraceSession
from .targets import get_index

SCHEMA_VERSION = "0.2.0"


class DryRunCommitError(RuntimeError):
    pass


class InvalidEntrypoint(ValueError):
    """The call cannot be made as requested (wrong arguments, ids on a model-level method)."""


def prepare_call(env, model: str, method: str, record_ids, context, kwargs):
    """Records to call ``method`` on, checked like Odoo's JSON-2 API does it.

    Raises KeyError (unknown model), AccessError/AttributeError (not callable remotely)
    and InvalidEntrypoint before anything runs.
    """
    records = env[model].with_context(**context).browse(record_ids)
    func = get_public_method(records, method)
    if getattr(func, "_api_model", False) and record_ids:
        raise InvalidEntrypoint(
            f"{model}.{method} is a model-level method: call it without record ids"
        )
    try:
        inspect.signature(func).bind(records, **kwargs)
    except TypeError as exc:
        raise InvalidEntrypoint(f"{model}.{method}: {exc}") from exc
    return records


_UNSET = object()


@contextmanager
def _commit_forbidden(cr):
    """Shadow ``cr.commit`` on the instance; restores whatever was there before (the
    class method, or an instance patch such as Odoo's test framework installs)."""

    def refuse():
        raise DryRunCommitError("cr.commit() is not allowed during a flow_tracer dry run")

    previous = vars(cr).get("commit", _UNSET)
    cr.commit = refuse
    try:
        yield
    finally:
        if previous is _UNSET:
            del cr.commit
        else:
            cr.commit = previous


@contextmanager
def _recording(session: TraceSession, index):
    MONITOR.acquire(index.targets.keys())
    token = CURRENT_SESSION.set(session)
    try:
        yield
    finally:
        CURRENT_SESSION.reset(token)
        MONITOR.release()


def run_trace(
    env, *, trace_id: str, model: str, method: str, record_ids, context, kwargs=None, dry_run=True
):
    """Execute ``model.method(**kwargs)`` on ``record_ids`` and return the trace payload.

    Raises the errors of :func:`prepare_call` and RecorderUnavailable before anything runs.
    """
    kwargs = kwargs or {}
    records = prepare_call(env, model, method, record_ids, context, kwargs)
    index = get_index(env.registry)
    session = TraceSession(index)
    cr = env.cr
    started_at = datetime.datetime.now(datetime.UTC)
    error = None

    savepoint = cr.savepoint()  # flushes pending work of the request first
    try:
        with _commit_forbidden(cr) if dry_run else _nothing(), _recording(session, index):
            try:
                # Odoo may change the values it gets (defaults added to vals); the trace
                # reports the call as it was requested.
                getattr(records, method)(**copy.deepcopy(kwargs))
                env.flush_all()
            except Exception as exc:
                error = values.error_of(exc)
    finally:
        savepoint.close(rollback=dry_run or error is not None)
        if dry_run or error is not None:
            cr.postcommit.clear()  # e.g. bus notifications or mails queued for after commit

    if session.failure is not None:
        error = {
            "type": "flow_tracer.RecorderError",
            "message": values.truncate(
                f"Recording failed: {session.failure!r}", values.MESSAGE_MAX
            ),
        }
    elif session.truncated and error is None:
        error = {
            "type": "flow_tracer.TraceTruncated",
            "message": (
                f"Recording stopped after {session.max_steps} steps; the run itself completed."
            ),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "trace_id": trace_id,
        "odoo_version": release.serie,
        "dry_run": dry_run,
        "started_at": started_at.isoformat(),
        "entrypoint": {
            "model": model,
            "method": method,
            "record_ids": list(record_ids),
            "context": context,
            "kwargs": kwargs,
        },
        "steps": session.steps,
        "error": error,
    }


@contextmanager
def _nothing():
    yield
