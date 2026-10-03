"""Fixtures for tests against the real Postgres from ``docker compose up -d db``.

Test databases are derived from DATABASE_URL (``<name>_test``) and created on demand,
so the development database is never touched.
"""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import make_url, text
from sqlalchemy.engine import URL, Connection
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from flow_tracer_api.core.config import get_settings

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def _base_url() -> URL:
    try:
        raw = get_settings().database_url.get_secret_value()
    except Exception as exc:  # pragma: no cover - configuration error path
        raise pytest.UsageError(
            "Integration tests need DATABASE_URL (see .env.example) and a running "
            "'docker compose up -d db'."
        ) from exc
    return make_url(raw)


def derive_database_url(suffix: str) -> URL:
    base = _base_url()
    return base.set(database=f"{base.database}_{suffix}")


async def ensure_database(url: URL) -> None:
    """Create the database ``url`` points to, if it does not exist yet."""
    admin = create_async_engine(_base_url(), isolation_level="AUTOCOMMIT", poolclass=NullPool)
    try:
        async with admin.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": url.database},
            )
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    finally:
        await admin.dispose()


@pytest.fixture(scope="session")
async def test_database_url() -> URL:
    url = derive_database_url("test")
    await ensure_database(url)
    return url


@pytest.fixture(scope="session")
async def engine(test_database_url: URL) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(test_database_url, poolclass=NullPool)
    yield engine
    await engine.dispose()


def alembic_config(connection: Connection) -> Config:
    """Alembic config bound to an existing sync connection (we are inside an event loop)."""
    config = Config(ALEMBIC_INI)
    config.attributes["connection"] = connection
    config.attributes["configure_logger"] = False
    return config


async def run_alembic(conn: AsyncConnection, action: str, revision: str) -> None:
    def _run(sync_conn: Connection) -> None:
        getattr(command, action)(alembic_config(sync_conn), revision)

    await conn.run_sync(_run)


@pytest.fixture(scope="session")
async def migrated_engine(engine: AsyncEngine) -> AsyncEngine:
    """Test database at migration head. The migrations are the schema's source of truth."""
    async with engine.begin() as conn:
        await run_alembic(conn, "upgrade", "head")
    return engine


@pytest.fixture
async def db_session(migrated_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Session inside an outer transaction that is rolled back after each test.

    ``create_savepoint`` lets code under test call ``commit()``/``rollback()`` without
    ending the outer transaction, so every test starts from an empty schema.
    """
    async with migrated_engine.connect() as conn:
        outer = await conn.begin()
        session = AsyncSession(
            bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield session
        finally:
            await session.close()
            await outer.rollback()
