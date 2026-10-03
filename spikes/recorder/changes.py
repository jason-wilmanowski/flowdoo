"""Spike M1, part 2: field changes and step noise with the sys.monitoring recorder.

Reuses the definitions of measure.py (exec it first). Checks:
* why wrapping (B) sees more steps than sys.monitoring (A)
* reading old/new values from the ORM cache without fetching or recomputing
* how much of the trace is framework noise
"""

from collections import Counter

MISSING = object()


def model_of(frame):
    obj = frame.f_locals.get("self", MISSING)  # NOT `or`: empty recordsets are falsy
    return getattr(obj, "_name", None) if obj is not MISSING else None


def peek(record_env, model_name, ids, fnames):
    """Values straight from the ORM cache; MISSING if not loaded. Never fetches/computes."""
    model = record_env[model_name]
    out = {}
    for fname in fnames:
        field = model._fields.get(fname)
        if field is None:
            continue
        cache = field._get_cache(record_env)
        for rid in ids:
            out[(rid, fname)] = cache.get(rid, MISSING)
    return out


COMPUTE_FIELDS = {}  # (model, method) -> [field names]
for model_name in admin_env.registry:
    for fname, field in admin_env[model_name]._fields.items():
        if isinstance(field.compute, str):
            COMPUTE_FIELDS.setdefault((model_name, field.compute), []).append(fname)


class ChangeSession(Session):
    def __init__(self):
        super().__init__()
        self.open = []  # parallel to stack: (model, method, records, before)
        self.changes = []  # (model, id, field, old, new, via)
        self.unknown_old = 0

    def start(self, code, frame):
        _cls, module, name = TARGETS[code]
        obj = frame.f_locals.get("self", MISSING)
        model = getattr(obj, "_name", None) if obj is not MISSING else None
        self.steps.append((len(self.stack), module, model, name))
        self.stack.append(code)
        before = None
        if model and _cls is BaseModel and name == "write":
            fnames = list(frame.f_locals["vals"])
            before = (fnames, peek(obj.env, model, obj.ids, fnames))
        elif model and (model, name) in COMPUTE_FIELDS:
            fnames = COMPUTE_FIELDS[(model, name)]
            before = (fnames, peek(obj.env, model, obj.ids, fnames))
        self.open.append((model, name, obj if model else None, before))

    def end(self, code, retval=None):
        while self.stack:
            popped = self.stack.pop()
            model, name, obj, before = self.open.pop()
            if popped is code:
                break
        if before is None:
            return
        fnames, old = before
        records = obj
        new = peek(records.env, model, records.ids, fnames)
        for (rid, fname), new_value in new.items():
            old_value = old[(rid, fname)]
            if old_value is MISSING:
                self.unknown_old += 1
            if new_value is not MISSING and new_value != old_value:
                self.changes.append((model, rid, fname, old_value, new_value, name))


def _c_start(code, _offset):
    if SESSION is not None:
        SESSION.start(code, sys._getframe(1))


def _c_return(code, _offset, retval):
    if SESSION is not None:
        SESSION.end(code, retval)


mon.use_tool_id(TOOL, "flowdoo-spike")
mon.register_callback(TOOL, E.PY_START, _c_start)
mon.register_callback(TOOL, E.PY_RETURN, _c_return)
mon.register_callback(TOOL, E.PY_UNWIND, _m_unwind)
for code in TARGETS:
    mon.set_local_events(TOOL, code, E.PY_START | E.PY_RETURN)
mon.set_events(TOOL, E.PY_UNWIND)
try:
    run_once(admin_env)
    SESSION = session = ChangeSession()
    t = run_once(admin_env)
    SESSION = None
finally:
    monitoring_off()

print(
    f"\nrecorded with changes: {t * 1000:.1f} ms, {len(session.steps)} steps, "
    f"{len(session.changes)} changes, {session.unknown_old} old values not in cache"
)
for change in session.changes[:25]:
    model, rid, fname, old, new, via = change
    old = "<not loaded>" if old is MISSING else old
    print(f"  {model}({rid}).{fname}: {old!r} -> {new!r}   via {via}")

models = Counter(m for _d, _mod, m, _n in session.steps)
print("\nsteps per model (top 15):", models.most_common(15))
INFRA = (
    "ir.",
    "res.users",
    "res.groups",
    "decimal.precision",
    "base",
    "res.lang",
    "mail.followers",
)
noise = sum(n for m, n in models.items() if m is None or m.startswith(INFRA))
print(f"steps on ir.*/res.users/res.groups/decimal.precision/... or without model: {noise}")

wrap_only = Counter(f"{m}.{n}" for _d, _mod, m, n in wrap_session.steps) - Counter(
    f"{m}.{n}" for _d, _mod, m, n in mon_session.steps
)
print("\nsteps only seen by wrapping (top 8):", wrap_only.most_common(8))
