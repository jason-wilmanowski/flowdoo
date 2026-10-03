"""Infrastructure steps that are not recorded (ADR 0001, "Infrastructure noise").

They run inside almost every business method (access checks, defaults, precision) and
would drown the flow. Their children are attached to the nearest recorded step; field
changes they cause still show up there. Keep this list short and explicit.
"""

NOISE_MODELS = frozenset(
    {
        "decimal.precision",
        "ir.config_parameter",
        "ir.default",
        "ir.model",
        "ir.model.access",
        "ir.model.fields",
        "ir.rule",
    }
)

# Access and SQL helpers called on every model.
NOISE_METHODS = frozenset({"_field_to_sql", "_has_field_access"})


def is_noise(model: str, method: str) -> bool:
    return model in NOISE_MODELS or method in NOISE_METHODS
