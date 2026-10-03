"""ORM mapping of a recorded trace: queryable metadata columns plus the opaque payload."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Index, String, Text, func, true
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from flow_tracer_api.domain import TraceStatus
from flow_tracer_api.models.base import Base

# Stored as VARCHAR + CHECK instead of a native PG enum: adding a state later is a
# plain constraint change instead of an ALTER TYPE migration.
TRACE_STATUS_TYPE = Enum(
    TraceStatus,
    name="trace_status",
    native_enum=False,
    create_constraint=True,
    length=16,
    values_callable=lambda enum: [member.value for member in enum],
    validate_strings=True,
)


class Trace(Base):
    __tablename__ = "traces"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    status: Mapped[TraceStatus] = mapped_column(TRACE_STATUS_TYPE)
    schema_version: Mapped[str | None] = mapped_column(String(32))
    odoo_version: Mapped[str | None] = mapped_column(String(32))
    entrypoint_model: Mapped[str] = mapped_column(String(128))
    entrypoint_method: Mapped[str] = mapped_column(String(128))
    dry_run: Mapped[bool] = mapped_column(default=True, server_default=true())
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    error: Mapped[str | None] = mapped_column(Text)
    # Opaque until the trace schema exists; validated in the service layer, not here.
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    __table_args__ = (
        Index("ix_traces_created_at", "created_at"),
        Index("ix_traces_status", "status"),
        Index("ix_traces_entrypoint", "entrypoint_model", "entrypoint_method"),
    )
