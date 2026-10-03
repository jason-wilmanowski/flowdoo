"""Inputs of the trace repository (create, partial update, filter)."""

import uuid
from datetime import datetime
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, model_validator

from flow_tracer_api.domain import TraceStatus


class TraceCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    entrypoint_model: str
    entrypoint_method: str
    started_at: datetime
    dry_run: bool = True
    status: TraceStatus = TraceStatus.PENDING
    id: uuid.UUID | None = None


class TraceUpdate(BaseModel):
    """Partial update: only fields passed explicitly are written.

    ``TraceUpdate(error=None)`` sets ``error`` to NULL, ``TraceUpdate()`` changes nothing.
    """

    model_config = ConfigDict(frozen=True)

    status: TraceStatus | None = None
    schema_version: str | None = None
    odoo_version: str | None = None
    finished_at: datetime | None = None
    error: str | None = None
    payload: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _status_is_not_nullable(self) -> Self:
        if "status" in self.model_fields_set and self.status is None:
            raise ValueError("status cannot be set to None")
        return self

    def changed_fields(self) -> dict[str, Any]:
        """Explicitly set fields with their Python values (enums stay enums)."""
        return {name: getattr(self, name) for name in self.model_fields_set}


class TraceFilter(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: TraceStatus | None = None
    entrypoint_model: str | None = None
    entrypoint_method: str | None = None
