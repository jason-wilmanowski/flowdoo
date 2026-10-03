"""Fixtures for tests against the real Postgres from ``docker compose up -d db``.

Test databases are derived from DATABASE_URL (``<name>_test``) and created on demand,
so the development database is never touched.
"""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import make_url, text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from flow_tracer_api.core.config import get_settings


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
