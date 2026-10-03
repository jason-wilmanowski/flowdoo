"""sys.monitoring integration (PEP 669, Python 3.12+), see ADR 0001.

Events are switched on only while at least one session is recording (reference counted)
and only for the indexed code objects, so without a trace no callback runs at all. The
session of the current request lives in a ContextVar: callbacks fired by other threads
or requests find none and return immediately.
"""

import sys
import threading
from contextvars import ContextVar

CURRENT_SESSION: ContextVar = ContextVar("flow_tracer_session", default=None)

_monitoring = getattr(sys, "monitoring", None)
AVAILABLE = _monitoring is not None
TOOL_ID = _monitoring.PROFILER_ID if AVAILABLE else None


class RecorderUnavailable(RuntimeError):
    pass


def _on_start(code, _offset):
    session = CURRENT_SESSION.get()
    if session is not None:
        session.on_start(code, sys._getframe(1))


def _on_return(code, _offset, retval):
    session = CURRENT_SESSION.get()
    if session is not None:
        session.on_return(code, retval)


def _on_unwind(code, _offset, exc):
    session = CURRENT_SESSION.get()
    if session is not None:
        session.on_unwind(code, exc)


class Monitor:
    def __init__(self):
        self._lock = threading.Lock()
        self._users = 0
        self._codes: set = set()

    def acquire(self, codes) -> None:
        if not AVAILABLE:
            raise RecorderUnavailable("Recording needs Python 3.12+ (sys.monitoring)")
        events = _monitoring.events
        with self._lock:
            if self._users == 0:
                owner = _monitoring.get_tool(TOOL_ID)
                if owner is not None:
                    raise RecorderUnavailable(
                        f"sys.monitoring tool id {TOOL_ID} is in use by {owner!r}"
                    )
                _monitoring.use_tool_id(TOOL_ID, "flow_tracer")
                _monitoring.register_callback(TOOL_ID, events.PY_START, _on_start)
                _monitoring.register_callback(TOOL_ID, events.PY_RETURN, _on_return)
                _monitoring.register_callback(TOOL_ID, events.PY_UNWIND, _on_unwind)
                _monitoring.set_events(TOOL_ID, events.PY_UNWIND)  # not a local event in 3.12
            local = events.PY_START | events.PY_RETURN
            for code in codes:
                if code not in self._codes:
                    _monitoring.set_local_events(TOOL_ID, code, local)
                    self._codes.add(code)
            self._users += 1

    def release(self) -> None:
        events = _monitoring.events
        with self._lock:
            self._users -= 1
            if self._users:
                return
            _monitoring.set_events(TOOL_ID, 0)
            for code in self._codes:
                _monitoring.set_local_events(TOOL_ID, code, 0)
            self._codes.clear()
            for event in (events.PY_START, events.PY_RETURN, events.PY_UNWIND):
                _monitoring.register_callback(TOOL_ID, event, None)
            _monitoring.free_tool_id(TOOL_ID)

    @property
    def active(self) -> bool:
        return self._users > 0


MONITOR = Monitor()
