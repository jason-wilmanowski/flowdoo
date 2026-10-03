"""Async SQLAlchemy engine and session factory.

Only the repository layer (and the unit of work built on it) may use sessions.
Creating an engine does not open a connection; that happens on first use.
"""

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
