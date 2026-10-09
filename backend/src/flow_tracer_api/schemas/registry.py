"""The model registry of the connected Odoo, as the flow_tracer addon reports it."""

from pydantic import BaseModel, ConfigDict


class ModelRelation(BaseModel):
    """A relational field and the model it points to."""

    model_config = ConfigDict(frozen=True)

    field: str
    # many2one, one2many or many2many
    type: str
    target: str


class ModelSummary(BaseModel):
    """One model in the overview list."""

    model_config = ConfigDict(frozen=True)

    model: str
    description: str | None
    # Module that defined the model.
    module: str | None
    # Modules that define or extend it, most derived first (the defining one last).
    modules: list[str]
    abstract: bool
    transient: bool
    # Other models it inherits from (mixins, parents), in MRO order.
    parents: list[str]
    # _inherits: delegated model -> the many2one field that links to it.
    delegates: dict[str, str]
    field_count: int
    relations: list[ModelRelation]


class ModelList(BaseModel):
    model_config = ConfigDict(frozen=True)

    models: list[ModelSummary]


class ModelField(BaseModel):
    """One field of a model."""

    model_config = ConfigDict(frozen=True)

    name: str
    type: str
    string: str | None
    # Module that defined the field; None for fields of the ORM itself (id, display_name).
    module: str | None
    target: str | None
    # one2many: the many2one on the target that points back.
    inverse: str | None
    required: bool
    readonly: bool
    stored: bool
    # Name of the compute method, if computed.
    compute: str | None
    # Dotted path, if related.
    related: str | None
    # [value, label] pairs of a static selection (at most 50).
    selection: list[list[str]] | None


class ModelDetail(BaseModel):
    """One model in detail."""

    model_config = ConfigDict(frozen=True)

    model: str
    description: str | None
    module: str | None
    modules: list[str]
    abstract: bool
    transient: bool
    parents: list[str]
    delegates: dict[str, str]
    fields: list[ModelField]
