"""Repository interfaces. The SQLAlchemy implementation lives in ``sqlalchemy/``;
service tests swap in in-memory fakes."""

import uuid
from collections.abc import Sequence
from typing import Protocol

from flow_tracer_api.models import Trace
from flow_tracer_api.schemas import TraceCreate, TraceFilter, TraceUpdate


class TraceRepository(Protocol):
    async def create(self, data: TraceCreate) -> Trace:
        """Insert a trace; DB defaults (``created_at``) are loaded on return."""
        ...

    async def get(self, trace_id: uuid.UUID) -> Trace | None: ...

    async def list_by(
        self, filters: TraceFilter, *, limit: int, offset: int = 0
    ) -> Sequence[Trace]:
        """Newest first (``created_at`` desc, then ``id``)."""
        ...

    async def count(self, filters: TraceFilter) -> int: ...

    async def update(self, trace_id: uuid.UUID, changes: TraceUpdate) -> Trace | None:
        """Apply the set fields of ``changes``; ``None`` if the trace does not exist."""
        ...

    async def delete(self, trace_id: uuid.UUID) -> bool:
        """``True`` if a trace was deleted."""
        ...
