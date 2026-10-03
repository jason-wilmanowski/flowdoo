"""FastAPI dependencies for database access (one session per request)."""

from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from flow_tracer_api.core.db import session_scope


def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    """Session factory created in the app lifespan (see ``api.app.create_app``)."""
    return cast(async_sessionmaker[AsyncSession], request.app.state.session_factory)


async def get_session(
    session_factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
) -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped session; it is closed after the response is sent."""
    async with session_scope(session_factory) as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
