"""Serialise values for the trace (schema v0.2.0 limits) without touching the ORM.

Field values are read from the ORM cache (``Field._get_cache``), never fetched or
computed, so recording does not change what it observes.
"""

import datetime
import json
import reprlib

SUMMARY_MAX = 2000
IDS_MAX = 1000
MESSAGE_MAX = 4000
MISSING = object()

_repr = reprlib.Repr(maxlevel=3, maxdict=8, maxlist=8, maxtuple=8, maxset=8, maxstring=200)
_repr.maxother = 200


def truncate(text: str, limit: int = SUMMARY_MAX) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def short_repr(value) -> str:
    """Bounded repr, even for huge structures or broken ``__repr__``."""
    try:
        return truncate(_repr.repr(value))
    except Exception as exc:  # a broken __repr__ must not break the trace
        return f"<unrepresentable {type(value).__name__}: {type(exc).__name__}>"


def summary(value) -> str | None:
    """Summary of an argument or return value; ``None`` (nothing) stays null."""
    return None if value is None else short_repr(value)


def ids_of(records) -> list[int]:
    """Real database ids (new records have NewId and are left out)."""
    return [i for i in records._ids if isinstance(i, int)][:IDS_MAX]


def peek(env, model_name: str, ids, fnames) -> dict:
    """{(id, field): cache value or MISSING}. Never triggers a fetch or a compute."""
    fields = env[model_name]._fields
    found = {}
    for fname in fnames:
        field = fields.get(fname)
        if field is None:
            continue
        cache = field._get_cache(env)
        for rid in ids:
            found[(rid, fname)] = cache.get(rid, MISSING)
    return found


def read_columns(env, model_name: str, ids, fnames) -> dict:
    """Stored column values straight from the table, without flushing the ORM.

    Used for old values of ``write`` that were not in the cache: what is in the table is
    then the current value (pending changes are always in the cache).
    """
    model = env[model_name]
    fields = model._fields
    columns = [f for f in fnames if f in fields and fields[f].store and fields[f].column_type]
    real_ids = [i for i in ids if isinstance(i, int)]
    if not columns or not real_ids:
        return {}
    env.cr.execute(
        'SELECT id, {} FROM "{}" WHERE id = ANY(%s)'.format(
            ", ".join(f'"{c}"' for c in columns), model._table
        ),
        [real_ids],
    )
    found = {}
    for row in env.cr.fetchall():
        for fname, value in zip(columns, row[1:], strict=True):
            found[(row[0], fname)] = value
    return found


def field_value(field, value):
    """Cache/column value -> schema FieldValue (null, bool, number, string, ids)."""
    if value is None or value is MISSING:
        return None
    if field.type == "boolean":
        return bool(value)
    if value is False:
        return None
    if field.type == "many2one":
        return [value] if isinstance(value, int) else None
    if field.type in ("one2many", "many2many"):
        return [v for v in value if isinstance(v, int)][:IDS_MAX]
    if isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, (datetime.datetime, datetime.date)):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"<binary {len(value)} bytes>"
    if isinstance(value, str):
        return truncate(str(value))
    if isinstance(value, (dict, list)):
        return truncate(json.dumps(value, default=str, ensure_ascii=False))
    return truncate(repr(value))


def error_of(exc: BaseException) -> dict:
    cls = type(exc)
    return {
        "type": truncate(f"{cls.__module__}.{cls.__qualname__}", 256),
        "message": truncate(str(exc), MESSAGE_MAX),
    }
