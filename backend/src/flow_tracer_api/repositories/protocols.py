"""Interfaces the service layer depends on. Implementations live in ``sqlalchemy/``."""

import uuid
from collections.abc import Sequence
from types import TracebackType
from typing import Protocol, Self

from flow_tracer_api.models import Trace
from flow_tracer_api.repositories.params import TraceCreate, TraceFilter, TraceUpdate


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


class UnitOfWork(Protocol):
    """One transaction scope. Nothing is persisted unless ``commit()`` is called.

    Usage in services::

        async with uow:
            trace = await uow.traces.create(...)
            await uow.commit()
    """

    @property
    def traces(self) -> TraceRepository: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
