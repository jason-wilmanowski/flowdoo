"""Data exchanged with the Odoo gateway port (see ``services.ports.OdooGateway``)."""

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TraceRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    trace_id: uuid.UUID
    model: str
    method: str
    record_ids: tuple[int, ...] = ()
    context: dict[str, Any] = Field(default_factory=dict)
    call_kwargs: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = True


class GatewayResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    # Opaque recorder output; checked by a TracePayloadValidator before it is stored.
    payload: dict[str, Any]
    odoo_version: str | None = None


class ValidatedPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    payload: dict[str, Any]
    schema_version: str | None


class OdooVersionInfo(BaseModel):
    """Subset of Odoo's ``exp_version()``; extra keys are ignored."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    server_version: str
    server_serie: str


class OdooConnectionStatus(BaseModel):
    """Result of checking the configured connection to the user's Odoo.

    ``ok`` is true only if every check passed. ``problems`` explain what blocks tracing,
    ``warnings`` what could not be verified.
    """

    model_config = ConfigDict(frozen=True)

    configured: bool
    url: str | None = None
    database: str | None = None
    reachable: bool = False
    server_version: str | None = None
    version_supported: bool = False
    authenticated: bool = False
    user_login: str | None = None
    addon_installed: bool = False
    addon_state: str | None = None
    # From the addon's status endpoint: server switch, recorder, rights of the key's user.
    tracing_enabled: bool = False
    recorder_available: bool = False
    user_is_admin: bool = False
    # None if it could not be checked.
    database_neutralized: bool | None = None
    ok: bool = False
    problems: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class EntrypointParameter(BaseModel):
    """One parameter of a method; only keyword arguments can be passed (as in JSON-2)."""

    model_config = ConfigDict(frozen=True)

    name: str
    # inspect.Parameter kind, lower case: positional_or_keyword, keyword_only, var_keyword, ...
    kind: str
    required: bool
    # repr of the default value; None if the parameter has no default
    default: str | None
    annotation: str | None


class EntrypointSignature(BaseModel):
    """What a method expects, so a trace can be started with the right kwargs."""

    model_config = ConfigDict(frozen=True)

    model: str
    method: str
    # True for @api.model methods: call them without record ids.
    model_level: bool
    # Module of the most derived implementation.
    module: str | None
    # First line of the docstring.
    summary: str | None
    parameters: list[EntrypointParameter]
