from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from flow_tracer_api.repositories.sqlalchemy.trace_repository import SqlAlchemyTraceRepository


class SqlAlchemyUnitOfWork:
    """Unit of work on top of a session supplied by the caller (e.g. ``core.SessionDep``).

    The session's lifetime belongs to whoever created it; this class only decides about
    the transaction. Leaving the ``async with`` block without ``commit()`` rolls back,
    so persisting is always an explicit decision of the service.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.traces = SqlAlchemyTraceRepository(session)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.rollback()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
