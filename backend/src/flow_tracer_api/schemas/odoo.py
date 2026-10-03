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
