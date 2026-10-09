"""Read the model registry for the overview: models, fields, relations, inheritance.

Everything comes from the running registry (not from source files), so it shows exactly
what the installed modules add. Nothing is written.
"""

from ..tracing import values

RELATIONAL = ("many2one", "one2many", "many2many")
SELECTION_MAX = 50


def _registry_classes(env) -> dict[type, str]:
    """The final class of every model in the registry -> model name."""
    return {type(env[name]): name for name in env.registry.models}


def _layers(env, model: str, registry_classes: dict[type, str]) -> tuple[list[str], list[str]]:
    """Modules that define or extend ``model`` (most derived first, the defining one last)
    and the other models it inherits from (mixins, parents), in MRO order."""
    mro = type(env[model]).__mro__
    modules: list[str] = []
    parents: list[str] = []
    in_own_layers = True
    for cls in mro[1:]:
        name = registry_classes.get(cls)
        if name is not None:
            in_own_layers = False
            # every model inherits from "base"; listing it would only add noise
            if name not in (model, "base"):
                parents.append(name)
            continue
        if in_own_layers:
            module = getattr(cls, "_module", None)
            if module and module not in modules:
                modules.append(module)
    return modules, parents


def list_models(env) -> list[dict]:
    """Every model with its modules and relational fields (for the list and the graph)."""
    registry_classes = _registry_classes(env)
    result = []
    for name in sorted(env.registry.models):
        records = env[name]
        modules, parents = _layers(env, name, registry_classes)
        result.append(
            {
                "model": name,
                "description": records._description or None,
                "module": getattr(records, "_original_module", None),
                "modules": modules,
                "abstract": bool(records._abstract),
                "transient": bool(records._transient),
                "parents": parents,
                "delegates": dict(records._inherits),
                "field_count": len(records._fields),
                "relations": [
                    {"field": field.name, "type": field.type, "target": field.comodel_name}
                    for field in records._fields.values()
                    if field.type in RELATIONAL and field.comodel_name
                ],
            }
        )
    return result


def describe_model(env, model: str) -> dict:
    """One model in detail: inheritance and every field. Raises KeyError for unknown models."""
    records = env[model]
    modules, parents = _layers(env, model, _registry_classes(env))
    return {
        "model": model,
        "description": records._description or None,
        "module": getattr(records, "_original_module", None),
        "modules": modules,
        "abstract": bool(records._abstract),
        "transient": bool(records._transient),
        "parents": parents,
        "delegates": dict(records._inherits),
        "fields": [_field(field) for field in records._fields.values()],
    }


def _field(field) -> dict:
    selection = getattr(field, "selection", None)
    return {
        "name": field.name,
        "type": field.type,
        "string": field.string or None,
        "module": getattr(field, "_module", None),
        "target": field.comodel_name if field.type in RELATIONAL else None,
        "inverse": getattr(field, "inverse_name", None) if field.type == "one2many" else None,
        "required": bool(field.required),
        "readonly": bool(field.readonly),
        "stored": bool(field.store),
        "compute": _name_of(field.compute),
        "related": ".".join(field.related)
        if isinstance(field.related, (list, tuple))
        else field.related,
        "selection": (
            [
                [str(key), values.truncate(str(label), 100)]
                for key, label in selection[:SELECTION_MAX]
            ]
            if isinstance(selection, list)
            else None
        ),
    }


def _name_of(compute) -> str | None:
    if compute is None:
        return None
    return compute if isinstance(compute, str) else getattr(compute, "__name__", repr(compute))
