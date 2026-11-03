"""What the server has resolved for a method or a field, read from the registry."""

import inspect
import re

ADDON_PATH = re.compile(r"(?:/addons/|/mnt/[^/]+/)(.+)$")


def source_path(filename):
    found = ADDON_PATH.search(filename)
    return found.group(1) if found else filename


def describe_method(env, model, method):
    """Every implementation in the MRO that defines the method, most derived first."""
    model_cls = type(env[model])
    implementations = []
    for cls in model_cls.__mro__:
        function = vars(cls).get(method)
        if function is None or not inspect.isfunction(inspect.unwrap(function)):
            continue
        code = inspect.unwrap(function).__code__
        implementations.append(
            {
                "position": len(implementations),
                "module": _module_of(cls),
                "file": source_path(code.co_filename),
                "line": code.co_firstlineno,
                # Heuristic: the name appears in the code, the call may still be conditional.
                "calls_super": "super" in code.co_names,
            }
        )
    if not implementations:
        raise AttributeError(f"The method '{model}.{method}' does not exist")
    function = inspect.unwrap(
        next(c.__dict__[method] for c in model_cls.__mro__ if method in c.__dict__)
    )
    return {
        "model": model,
        "method": method,
        "private": method.startswith("_"),
        "signature": str(inspect.signature(function)),
        "implementations": implementations,
    }


def describe_field(env, model, field_name):
    """How a field gets its value and which stored fields follow it."""
    records = env[model]
    field = records._fields.get(field_name)
    if field is None:
        raise AttributeError(f"The field '{model}.{field_name}' does not exist")
    depends = field.get_depends(records)[0] if field.compute or field.related else ()
    return {
        "model": model,
        "field": field_name,
        "type": field.type,
        "stored": bool(field.store),
        "compute": field.compute if isinstance(field.compute, str) else None,
        "related": ".".join(field.related) if field.related else None,
        "depends_on": list(depends),
        "recomputes": sorted(_dependents(env, field))[:50],
    }


def _module_of(cls):
    found = re.match(r"odoo\.addons\.([^.]+)", cls.__module__)
    return found.group(1) if found else cls.__module__


def _dependents(env, field):
    found = set()
    _collect(env.registry.get_trigger_tree([field]), found)
    return found


def _collect(tree, found):
    found.update(f"{item.model_name}.{item.name}" for item in tree.root)
    for child in tree.values():
        _collect(child, found)
