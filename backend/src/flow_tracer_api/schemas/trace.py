import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from flow_tracer_api.domain import TraceStatus

# Lengths mirror the columns of the ``traces`` table.
OdooModelName = Annotated[str, Field(min_length=1, max_length=128)]
OdooMethodName = Annotated[str, Field(min_length=1, max_length=128)]


class StartTraceCommand(BaseModel):
    """Request to record one workflow run in the user's Odoo."""

    model_config = ConfigDict(
        frozen=True, str_strip_whitespace=True, validate_by_name=True, validate_by_alias=True
    )

    entrypoint_model: OdooModelName
    entrypoint_method: OdooMethodName
    # Empty for model-level (@api.model) methods.
    record_ids: tuple[int, ...] = ()
    context: dict[str, Any] = Field(default_factory=dict)
    # Keyword arguments of the method (JSON values; recordsets as ids), like Odoo's JSON-2.
    # Named call_kwargs in Python (a field called "kwargs" clashes with __init__(**kwargs)).
    call_kwargs: dict[str, Any] = Field(default_factory=dict, alias="kwargs")
    # Dry run (rollback at the end) is the default; see CLAUDE.md section 6.
    dry_run: bool = True


class TraceListQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: TraceStatus | None = None
    entrypoint_model: str | None = None
    entrypoint_method: str | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class TraceSummary(BaseModel):
    """Trace metadata without the (potentially large) payload."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: uuid.UUID
    status: TraceStatus
    entrypoint_model: str
    entrypoint_method: str
    dry_run: bool
    schema_version: str | None
    odoo_version: str | None
    started_at: datetime
    finished_at: datetime | None
    created_at: datetime
    error: str | None


class TraceDetail(TraceSummary):
    # Opaque until the trace schema exists (see services.ports.TracePayloadValidator).
    payload: dict[str, Any] | None


class TracePage(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[TraceSummary]
    total: int
    limit: int
    offset: int
