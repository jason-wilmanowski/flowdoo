import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from flow_tracer_api.models import Trace
from flow_tracer_api.repositories.params import TraceCreate, TraceFilter, TraceUpdate


class SqlAlchemyTraceRepository:
    """CRUD for ``traces``. Flushes when it needs DB state, never commits."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: TraceCreate) -> Trace:
        values: dict[str, Any] = {
            "entrypoint_model": data.entrypoint_model,
            "entrypoint_method": data.entrypoint_method,
            "started_at": data.started_at,
            "dry_run": data.dry_run,
            "status": data.status,
        }
        if data.id is not None:
            values["id"] = data.id
        trace = Trace(**values)
        self._session.add(trace)
        await self._session.flush()
        await self._session.refresh(trace)
        return trace

    async def get(self, trace_id: uuid.UUID) -> Trace | None:
        return await self._session.get(Trace, trace_id)

    async def list_by(
        self, filters: TraceFilter, *, limit: int, offset: int = 0
    ) -> Sequence[Trace]:
        statement = (
            select(Trace)
            .where(*_conditions(filters))
            .order_by(Trace.created_at.desc(), Trace.id)
            .limit(limit)
            .offset(offset)
        )
        return (await self._session.scalars(statement)).all()

    async def count(self, filters: TraceFilter) -> int:
        statement = select(func.count()).select_from(Trace).where(*_conditions(filters))
        return (await self._session.scalar(statement)) or 0

    async def update(self, trace_id: uuid.UUID, changes: TraceUpdate) -> Trace | None:
        trace = await self.get(trace_id)
        if trace is None:
            return None
        for name, value in changes.changed_fields().items():
            setattr(trace, name, value)
        await self._session.flush()
        return trace

    async def delete(self, trace_id: uuid.UUID) -> bool:
        trace = await self.get(trace_id)
        if trace is None:
            return False
        await self._session.delete(trace)
        await self._session.flush()
        return True


def _conditions(filters: TraceFilter) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if filters.status is not None:
        conditions.append(Trace.status == filters.status)
    if filters.entrypoint_model is not None:
        conditions.append(Trace.entrypoint_model == filters.entrypoint_model)
    if filters.entrypoint_method is not None:
        conditions.append(Trace.entrypoint_method == filters.entrypoint_method)
    return conditions
