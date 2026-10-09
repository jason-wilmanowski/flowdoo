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
    funcs = [vars(cls)[method] for cls in implementations] or [func]
    doc = next((d for d in (inspect.getdoc(f) for f in funcs) if d and d.strip()), "")
    return {
        "model": model,
        "method": method,
        "model_level": bool(getattr(func, "_api_model", False)),
        "module": module,
        "summary": summary_of(doc),
        "parameters": merged_parameters(funcs),
    }


def merged_parameters(funcs) -> list[dict]:
    """Parameters of a method along its MRO, most derived implementation first.

    An override often only passes arguments on (``def message_post(self, **kwargs)``);
    then the arguments the next implementation takes are reachable too. Collecting stops
    at the first implementation without ``**kwargs``. ``*args``/``**kwargs`` themselves are
    reported only where the chain ends with them.
    """
    named: dict[str, dict] = {}
    variadic: list[dict] = []
    for func in funcs:
        params = list(inspect.signature(func).parameters.items())[1:]  # without self
        is_variadic = [p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD) for _, p in params]
        for (name, param), variable in zip(params, is_variadic, strict=True):
            if not variable and name not in named:
                named[name] = _describe(name, param)
        # the variadic parameters of the implementation where collecting stops
        variadic = [
            _describe(name, p)
            for (name, p), variable in zip(params, is_variadic, strict=True)
            if variable
        ]
        if not any(p.kind is p.VAR_KEYWORD for _, p in params):
            break
    return [*named.values(), *variadic]


def _describe(name: str, param: inspect.Parameter) -> dict:
    has_default = param.default is not inspect.Parameter.empty
    return {
        "name": name,
        "kind": param.kind.name.lower(),
        "required": not has_default and param.kind not in (param.VAR_POSITIONAL, param.VAR_KEYWORD),
        "default": values.short_repr(param.default) if has_default else None,
        "annotation": (
            None
            if param.annotation is inspect.Parameter.empty
            else values.truncate(inspect.formatannotation(param.annotation), 200)
        ),
    }


def summary_of(doc: str) -> str | None:
    """The first paragraph of a docstring, as one line (up to 500 characters)."""
    paragraph = doc.strip().split("\n\n", 1)[0] if doc.strip() else ""
    text = " ".join(line.strip() for line in paragraph.splitlines() if line.strip())
    return values.truncate(text, 500) if text else None
