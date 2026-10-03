"""Which code the recorder observes (ADR 0001).

Every function defined in an addon model class, plus the ORM entry points of
``BaseModel``. Each code object maps to the class that defines it, so module and MRO
position of a step are exact. The index is built once per registry.
"""

import inspect
import threading
from typing import NamedTuple

from odoo.models import BaseModel

ORM_ENTRY_POINTS = ("create", "write", "unlink")
_SKIPPED_CODE_FLAGS = inspect.CO_GENERATOR | inspect.CO_COROUTINE | inspect.CO_ASYNC_GENERATOR
_INDEX_ATTRIBUTE = "_flow_tracer_target_index"
_BUILD_LOCK = threading.Lock()


class Target(NamedTuple):
    cls: type
    module: str | None  # None for BaseModel (Odoo core, not an addon)
    method: str
    kind: str  # method_call, onchange, constraint or orm_*; compute is decided per model


class TargetIndex:
    """Code object -> Target, plus lazily cached MRO data per model class."""

    __slots__ = ("_implementations", "computes", "targets")

    def __init__(self, registry):
        self.targets: dict = {}
        self.computes: dict[tuple[str, str], tuple[str, ...]] = {}
        self._implementations: dict[tuple[type, str], tuple[type, ...]] = {}
        seen: set[type] = set()
        for model_name, model_cls in registry.items():
            for cls in model_cls.__mro__:
                if cls not in seen and cls.__module__.startswith("odoo.addons."):
                    seen.add(cls)
                    self._add_class(cls)
            computed: dict[str, list[str]] = {}
            for fname, field in model_cls._fields.items():
                if isinstance(field.compute, str):
                    computed.setdefault(field.compute, []).append(fname)
            for method, fnames in computed.items():
                self.computes[(model_name, method)] = tuple(fnames)
        for name in ORM_ENTRY_POINTS:
            fn = inspect.unwrap(BaseModel.__dict__[name])
            self.targets[fn.__code__] = Target(BaseModel, None, name, f"orm_{name}")

    def _add_class(self, cls: type) -> None:
        module = getattr(cls, "_module", None)
        for name, attr in vars(cls).items():
            if isinstance(attr, (classmethod, staticmethod)):
                continue  # no recordset to attach a step to
            if not inspect.isfunction(attr):
                continue
            fn = inspect.unwrap(attr)
            code = fn.__code__
            if code.co_flags & _SKIPPED_CODE_FLAGS or code in self.targets:
                continue
            self.targets[code] = Target(cls, module, name, _static_kind(name, fn))

    def implementations(self, model_cls: type, method: str) -> tuple[type, ...]:
        """Classes of ``model_cls``'s MRO that define ``method``, most derived first."""
        key = (model_cls, method)
        found = self._implementations.get(key)
        if found is None:
            found = tuple(c for c in model_cls.__mro__ if method in vars(c))
            self._implementations[key] = found
        return found

    def mro_position(self, model_cls: type, target: Target) -> int | None:
        try:
            return self.implementations(model_cls, target.method).index(target.cls)
        except ValueError:
            return None


def _static_kind(name: str, fn) -> str:
    if name in ORM_ENTRY_POINTS:
        return f"orm_{name}"
    if getattr(fn, "_onchange", None):
        return "onchange"
    if getattr(fn, "_constrains", None):
        return "constraint"
    return "method_call"


def get_index(registry) -> TargetIndex:
    """Index for ``registry``; a reloaded registry is a new object and gets a new index."""
    index = getattr(registry, _INDEX_ATTRIBUTE, None)
    if index is None:
        with _BUILD_LOCK:
            index = getattr(registry, _INDEX_ATTRIBUTE, None)
            if index is None:
                index = TargetIndex(registry)
                setattr(registry, _INDEX_ATTRIBUTE, index)
    return index
