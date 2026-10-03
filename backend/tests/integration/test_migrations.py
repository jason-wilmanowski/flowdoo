from collections.abc import AsyncIterator

import pytest
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Connection, inspect
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from flow_tracer_api.models import Base
from tests.integration.conftest import derive_database_url, ensure_database, run_alembic

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
async def migrations_engine() -> AsyncIterator[AsyncEngine]:
    """Separate database, so downgrading does not disturb the other tests."""
    url = derive_database_url("test_migrations")
    await ensure_database(url)
    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.begin() as conn:
        await run_alembic(conn, "downgrade", "base")
    yield engine
    await engine.dispose()


async def _table_names(conn: AsyncConnection) -> set[str]:
    return set(await conn.run_sync(lambda c: inspect(c).get_table_names()))


async def test_upgrade_head_then_downgrade_base(migrations_engine: AsyncEngine) -> None:
    async with migrations_engine.begin() as conn:
        await run_alembic(conn, "upgrade", "head")
        assert "traces" in await _table_names(conn)

    async with migrations_engine.begin() as conn:
        await run_alembic(conn, "downgrade", "base")
        assert await _table_names(conn) <= {"alembic_version"}

    async with migrations_engine.begin() as conn:
        await run_alembic(conn, "upgrade", "head")
        assert "traces" in await _table_names(conn)


async def test_models_match_migrations(migrations_engine: AsyncEngine) -> None:
    def _diff(sync_conn: Connection) -> list[object]:
        return list(compare_metadata(MigrationContext.configure(sync_conn), Base.metadata))

    async with migrations_engine.begin() as conn:
        await run_alembic(conn, "upgrade", "head")
        assert await conn.run_sync(_diff) == []
