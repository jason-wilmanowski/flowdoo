"""Keeps sensitive values out of traces, which leave Odoo and may get stored elsewhere.

A field or parameter is sensitive if its name contains one of the name parts. Add parts with
``flow_tracer_masked_fields = email,phone`` in the [options] section of the Odoo configuration.
Only names are checked, so a secret inside a free text or an exception message can still pass.
"""

from collections.abc import Mapping
from functools import lru_cache

from odoo.tools import config

CONFIG_KEY = "flow_tracer_masked_fields"
MASKED = "***"
DEFAULT_PARTS = (
    "api_key",
    "apikey",
    "card_number",
    "credit_card",
    "passwd",
    "password",
    "private_key",
    "secret",
    "token",
    "totp",
)
MAX_PARTS = 200
MAX_PART_LENGTH = 128
MAX_DEPTH = 6
MAX_WALKED_ITEMS = 16


def masked_fields() -> list[str]:
    """The name parts in force, as the trace reports them."""
    return list(_parts(str(config.get(CONFIG_KEY) or "")))


@lru_cache(maxsize=8)
def _parts(configured: str) -> tuple[str, ...]:
    extra = (part.strip().casefold() for part in configured.split(","))
    usable = {part for part in extra if part and len(part) <= MAX_PART_LENGTH}
    return tuple(sorted({*DEFAULT_PARTS, *usable}))[:MAX_PARTS]


def is_sensitive(name) -> bool:
    if not isinstance(name, str):
        return False
    lowered = name.casefold()
    return any(part in lowered for part in _parts(str(config.get(CONFIG_KEY) or "")))


def masked(value, depth: int = 0):
    """A copy of a value with sensitive keys of nested dicts masked, for arguments and results."""
    if depth >= MAX_DEPTH:
        return value
    if isinstance(value, Mapping):
        return {
            key: MASKED if is_sensitive(key) and item is not None else masked(item, depth + 1)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        walked = [masked(item, depth + 1) for item in value[:MAX_WALKED_ITEMS]]
        rebuilt = [*walked, *value[MAX_WALKED_ITEMS:]]
        return tuple(rebuilt) if isinstance(value, tuple) else rebuilt
    return value


def masked_field_value(field_name: str, value):
    """Masks a field value, but keeps null, which shows that the field was empty."""
    return MASKED if value is not None and is_sensitive(field_name) else value
