from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from flow_tracer_api.repositories import UnitOfWork
from flow_tracer_api.repositories.sqlalchemy import SqlAlchemyUnitOfWork
from flow_tracer_api.schemas import TraceCreate

pytestmark = pytest.mark.integration

NEW = TraceCreate(
    entrypoint_model="sale.order",
    entrypoint_method="action_confirm",
    started_at=datetime(2026, 10, 3, 12, 0, tzinfo=UTC),
)


@pytest.fixture
def uow(db_session: AsyncSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(db_session)


async def test_commit_persists(uow: UnitOfWork) -> None:
    async with uow:
        trace = await uow.traces.create(NEW)
        await uow.commit()

    async with uow:
        assert await uow.traces.get(trace.id) is not None


async def test_leaving_without_commit_rolls_back(uow: UnitOfWork) -> None:
    async with uow:
        trace = await uow.traces.create(NEW)

    async with uow:
        assert await uow.traces.get(trace.id) is None


async def test_exception_rolls_back_and_propagates(uow: UnitOfWork) -> None:
    trace_ids = []

    async def failing() -> None:
        async with uow:
            trace_ids.append((await uow.traces.create(NEW)).id)
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await failing()

    async with uow:
        assert await uow.traces.get(trace_ids[0]) is None


async def test_explicit_rollback_discards_pending_changes(uow: UnitOfWork) -> None:
    async with uow:
        trace = await uow.traces.create(NEW)
        await uow.rollback()
        assert await uow.traces.get(trace.id) is None
