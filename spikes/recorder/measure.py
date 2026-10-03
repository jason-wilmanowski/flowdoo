"""Spike M1: compare recording mechanisms on sale.order.action_confirm (Odoo 19).

Run inside the test Odoo (database with sale_stock + demo data), see README.md:
    exec(open("/spikes/recorder/measure.py").read())
Every run happens in a savepoint that is rolled back, so the database stays unchanged.
"""

import functools
import inspect
import statistics
import sys
import time
from collections import Counter
from contextlib import closing

from odoo.orm.models import BaseModel

ORDER_ID = 1
RUNS = 7
SKIP_FLAGS = inspect.CO_GENERATOR | inspect.CO_COROUTINE | inspect.CO_ASYNC_GENERATOR

admin_env = env(user=env.ref("base.user_admin").id)  # noqa: F821 - provided by odoo shell


def run_once(e):
    order = e["sale.order"].browse(ORDER_ID)
    assert order.state == "draft", order.state
    with closing(e.cr.savepoint()):  # closing() rolls the savepoint back
        start = time.perf_counter()
        order.action_confirm()
        e.flush_all()  # pending recomputes / SQL, like a real commit would run
        elapsed = time.perf_counter() - start
    assert e["sale.order"].browse(ORDER_ID).state == "draft"
    return elapsed


def timed(label, runs=RUNS):
    run_once(admin_env)  # warm-up
    samples = [run_once(admin_env) for _ in range(runs)]
    median = statistics.median(samples) * 1000
    print(f"{label:<44} median {median:8.1f} ms  (min {min(samples) * 1000:.1f})")
    return median


# --------------------------------------------------------------------------- targets
def collect_targets(e):
    """Code object -> (defining class, module, method name) for every function defined in
    an addon model class, plus the ORM entry points create/write/unlink of BaseModel."""
    targets, seen_classes = {}, set()
    collisions = 0
    for model_name in e.registry:
        for cls in type(e[model_name]).__mro__:
            if cls in seen_classes or not cls.__module__.startswith("odoo.addons."):
                continue
            seen_classes.add(cls)
            for name, attr in vars(cls).items():
                fn = attr.__func__ if isinstance(attr, (classmethod, staticmethod)) else attr
                fn = inspect.unwrap(fn) if inspect.isfunction(fn) else None
                if fn is None or fn.__code__.co_flags & SKIP_FLAGS:
                    continue
                if fn.__code__ in targets:
                    collisions += 1
                    continue
                targets[fn.__code__] = (cls, getattr(cls, "_module", None), name)
    for name in ("create", "write", "unlink"):
        fn = inspect.unwrap(BaseModel.__dict__[name])
        targets[fn.__code__] = (BaseModel, None, name)
    return targets, len(seen_classes), collisions


start = time.perf_counter()
TARGETS, N_CLASSES, COLLISIONS = collect_targets(admin_env)
print(
    f"targets: {len(TARGETS)} functions in {N_CLASSES} addon classes "
    f"(collisions skipped: {COLLISIONS}), collected in {(time.perf_counter() - start) * 1000:.0f} ms"
)


# --------------------------------------------------------------------------- recorder core
class Session:
    def __init__(self):
        self.steps = []  # (depth, module, model, method, n_records)
        self.stack = []

    def start(self, code, self_obj):
        _cls, module, name = TARGETS[code]
        model = getattr(self_obj, "_name", None)
        self.steps.append((len(self.stack), module, model, name))
        self.stack.append(code)

    def end(self, code):
        while self.stack:
            if self.stack.pop() is code:
                break


SESSION = None


# --------------------------------------------------------------------------- A: sys.monitoring
mon = sys.monitoring
TOOL = mon.PROFILER_ID
E = mon.events


def _m_start(code, _offset):
    if SESSION is not None:
        frame = sys._getframe(1)
        SESSION.start(code, frame.f_locals.get("self") or frame.f_locals.get("cls"))


def _m_return(code, _offset, _retval):
    if SESSION is not None:
        SESSION.end(code)


def _m_unwind(code, _offset, _exc):
    if SESSION is not None and code in TARGETS:
        SESSION.end(code)


def monitoring_on():
    mon.use_tool_id(TOOL, "flowdoo-spike")
    mon.register_callback(TOOL, E.PY_START, _m_start)
    mon.register_callback(TOOL, E.PY_RETURN, _m_return)
    mon.register_callback(TOOL, E.PY_UNWIND, _m_unwind)
    for code in TARGETS:
        mon.set_local_events(TOOL, code, E.PY_START | E.PY_RETURN)
    mon.set_events(TOOL, E.PY_UNWIND)  # PY_UNWIND is not a local event in 3.12


def monitoring_off():
    mon.set_events(TOOL, 0)
    for code in TARGETS:
        mon.set_local_events(TOOL, code, 0)
    for event in (E.PY_START, E.PY_RETURN, E.PY_UNWIND):
        mon.register_callback(TOOL, event, None)
    mon.free_tool_id(TOOL)


# --------------------------------------------------------------------------- B: wrapping
ORIGINALS = []


def _wrap(fn, code):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if SESSION is None:
            return fn(*args, **kwargs)
        SESSION.start(code, args[0] if args else None)
        try:
            return fn(*args, **kwargs)
        finally:
            SESSION.end(code)

    return wrapper


def wrapping_on():
    for code, (cls, _module, name) in TARGETS.items():
        attr = cls.__dict__.get(name)
        if attr is None or isinstance(attr, (classmethod, staticmethod)):
            continue
        if not inspect.isfunction(attr) or inspect.unwrap(attr).__code__ is not code:
            continue
        ORIGINALS.append((cls, name, attr))
        setattr(cls, name, _wrap(attr, code))


def wrapping_off():
    while ORIGINALS:
        cls, name, attr = ORIGINALS.pop()
        setattr(cls, name, attr)


# --------------------------------------------------------------------------- C: setprofile
def _profile(frame, event, _arg):
    if SESSION is None:
        return
    code = frame.f_code
    if code not in TARGETS:
        return
    if event == "call":
        SESSION.start(code, frame.f_locals.get("self"))
    elif event == "return":
        SESSION.end(code)


# --------------------------------------------------------------------------- measurements
def recorded(label, on, off):
    global SESSION
    t = time.perf_counter()
    on()
    enable_ms = (time.perf_counter() - t) * 1000
    try:
        run_once(admin_env)  # warm-up, not recorded
        samples, session = [], None
        for _ in range(RUNS):
            SESSION = session = Session()
            samples.append(run_once(admin_env))
            SESSION = None
        median = statistics.median(samples) * 1000
    finally:
        SESSION = None
        t = time.perf_counter()
        off()
        disable_ms = (time.perf_counter() - t) * 1000
    print(
        f"{label:<44} median {median:8.1f} ms  steps {len(session.steps):6d}  "
        f"enable {enable_ms:.0f} ms / disable {disable_ms:.0f} ms"
    )
    return median, session


print(
    f"\nOdoo {__import__('odoo').release.version}, Python {sys.version.split()[0]}, "
    f"order {admin_env['sale.order'].browse(ORDER_ID).name}, {RUNS} runs each\n"
)
base = timed("baseline (no recorder)")

mon_ms, mon_session = recorded("A sys.monitoring (local events)", monitoring_on, monitoring_off)
base_after_mon = timed("baseline after A disabled")

wrap_ms, wrap_session = recorded("B wrapping (active session)", wrapping_on, wrapping_off)
wrapping_on()
inactive_wrap = timed("B wrapping installed, no session")
wrapping_off()

prof_ms, prof_session = recorded(
    "C sys.setprofile (filter in callback)",
    lambda: sys.setprofile(_profile),
    lambda: sys.setprofile(None),
)

try:
    from odoo.tools.profiler import Profiler

    def profiled_run():
        with Profiler(collectors=["traces_sync"], db=None, profile_session="spike"):
            return run_once(admin_env)

    profiled_run()
    samples = [profiled_run() for _ in range(3)]
    print(f"{'D Odoo profiler traces_sync':<44} median {statistics.median(samples) * 1000:8.1f} ms")
except Exception as exc:  # report, do not hide
    print(f"D Odoo profiler traces_sync: failed: {type(exc).__name__}: {exc}")

print(
    "\nsame steps in A and B:",
    mon_session.steps == wrap_session.steps,
    "| A vs C:",
    mon_session.steps == prof_session.steps,
)

steps = mon_session.steps
by_module = Counter(module for _d, module, _m, _n in steps)
by_method = Counter(f"{model}.{name}" for _d, _mod, model, name in steps)
print(f"\nA: {len(steps)} steps, {len(by_module)} modules, max depth {max(d for d, *_ in steps)}")
print("top modules:", by_module.most_common(12))
print("top methods:", by_method.most_common(15))
print("\nfirst 30 steps (depth, module, model, method):")
for depth, module, model, name in steps[:30]:
    print(f"  {'  ' * depth}{model}.{name}  [{module}]")
