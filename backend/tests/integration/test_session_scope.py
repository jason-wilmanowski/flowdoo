import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from flow_tracer_api.core.db import create_session_factory, session_scope
from flow_tracer_api.core.dependencies import get_session

pytestmark = pytest.mark.integration


async def test_session_scope_yields_working_session(engine: AsyncEngine) -> None:
    async with session_scope(create_session_factory(engine)) as session:
        assert await session.scalar(text("SELECT 1")) == 1


async def test_session_scope_rolls_back_and_reraises(engine: AsyncEngine) -> None:
    factory = create_session_factory(engine)

    async def failing_unit_of_work() -> None:
        async with session_scope(factory) as session:
            await session.execute(text("CREATE TABLE scope_probe (id int)"))
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await failing_unit_of_work()

    async with session_scope(factory) as session:
        assert await session.scalar(text("SELECT to_regclass('public.scope_probe')")) is None


async def test_scope_does_not_commit(engine: AsyncEngine) -> None:
    factory = create_session_factory(engine)
    async with session_scope(factory) as session:
        await session.execute(text("CREATE TABLE uncommitted_probe (id int)"))

    async with session_scope(factory) as session:
        assert await session.scalar(text("SELECT to_regclass('public.uncommitted_probe')")) is None


async def test_get_session_dependency_closes_session(engine: AsyncEngine) -> None:
    dependency = get_session(create_session_factory(engine))
    session = await anext(dependency)
    assert await session.scalar(text("SELECT 1")) == 1
    assert session.in_transaction()

    with pytest.raises(StopAsyncIteration):
        await anext(dependency)
    assert not session.in_transaction()
