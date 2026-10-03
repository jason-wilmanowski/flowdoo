"""Describe an entrypoint before tracing it: which keyword arguments it takes.

Same reachability rules as JSON-2 (``get_public_method``). Only keyword arguments can be
passed, as in JSON-2; positional-only and ``*args`` parameters are reported but cannot be
filled.
"""

import inspect

from odoo.service.model import get_public_method

from . import values
from .targets import get_index


def describe_entrypoint(env, model: str, method: str) -> dict:
    records = env[model]
    func = get_public_method(records, method)
    index = get_index(env.registry)
    implementations = index.implementations(type(records), method)
    module = getattr(implementations[0], "_module", None) if implementations else None
    parameters = []
    for position, (name, param) in enumerate(inspect.signature(func).parameters.items()):
        if position == 0:  # self
            continue
        has_default = param.default is not inspect.Parameter.empty
        parameters.append(
            {
                "name": name,
                "kind": param.kind.name.lower(),
                "required": not has_default
                and param.kind not in (param.VAR_POSITIONAL, param.VAR_KEYWORD),
                "default": values.short_repr(param.default) if has_default else None,
                "annotation": (
                    None
                    if param.annotation is inspect.Parameter.empty
                    else values.truncate(inspect.formatannotation(param.annotation), 200)
                ),
            }
        )
    doc = inspect.getdoc(func) or ""
    return {
        "model": model,
        "method": method,
        "model_level": bool(getattr(func, "_api_model", False)),
        "module": module,
        "summary": values.truncate(doc.strip().splitlines()[0], 500) if doc.strip() else None,
        "parameters": parameters,
    }
