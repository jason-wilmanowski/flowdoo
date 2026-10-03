"""Async SQLAlchemy engine and session factory.

One session per request (see ``core.dependencies``) is injected into the services,
which build their repositories on it and decide when to commit.
Creating an engine does not open a connection; that happens on first use.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from flow_tracer_api.core.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    # expire_on_commit=False: loaded attributes stay readable after commit,
    # so services can map ORM rows to DTOs without lazy IO.
    return async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def session_scope(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Open a session (e.g. for one request) and always close it.

    This scope never commits: committing is the service layer's decision. On error the
    open transaction is rolled back explicitly; on normal exit, closing the session
    discards anything that was not committed.
    """
    async with session_factory() as session:
        try:
            yield session
        except BaseException:
            await session.rollback()
            raise
