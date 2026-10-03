"""In-memory fakes for service tests (no database)."""

import copy
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import TracebackType
from typing import Any, Self

from flow_tracer_api.domain import TraceStatus
from flow_tracer_api.models import Trace
from flow_tracer_api.repositories import TraceCreate, TraceFilter, TraceUpdate
from flow_tracer_api.services.ports import GatewayResult, TraceRequest

FIXED_NOW = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)


@dataclass
class _Row:
    id: uuid.UUID
    status: TraceStatus
    entrypoint_model: str
    entrypoint_method: str
    dry_run: bool
    started_at: datetime
    created_at: datetime
    schema_version: str | None = None
    odoo_version: str | None = None
    finished_at: datetime | None = None
    error: str | None = None
    payload: dict[str, Any] | None = None

    def to_orm(self) -> Trace:
        # Transient ORM instance, never attached to a session.
        return Trace(**self.__dict__)


class FakeTraceRepository:
    def __init__(self, rows: dict[uuid.UUID, _Row]) -> None:
        self.rows = rows

    async def create(self, data: TraceCreate) -> Trace:
        row = _Row(
            id=data.id or uuid.uuid4(),
            status=data.status,
            entrypoint_model=data.entrypoint_model,
            entrypoint_method=data.entrypoint_method,
            dry_run=data.dry_run,
            started_at=data.started_at,
            created_at=FIXED_NOW,
        )
        self.rows[row.id] = row
        return row.to_orm()

    async def get(self, trace_id: uuid.UUID) -> Trace | None:
        row = self.rows.get(trace_id)
        return row.to_orm() if row else None

    def _matching(self, filters: TraceFilter) -> list[_Row]:
        return [
            r
            for r in self.rows.values()
            if (filters.status is None or r.status == filters.status)
            and (filters.entrypoint_model is None or r.entrypoint_model == filters.entrypoint_model)
            and (
                filters.entrypoint_method is None
                or r.entrypoint_method == filters.entrypoint_method
            )
        ]

    async def list_by(
        self, filters: TraceFilter, *, limit: int, offset: int = 0
    ) -> Sequence[Trace]:
        rows = sorted(self._matching(filters), key=lambda r: r.created_at, reverse=True)
        return [r.to_orm() for r in rows[offset : offset + limit]]

    async def count(self, filters: TraceFilter) -> int:
        return len(self._matching(filters))

    async def update(self, trace_id: uuid.UUID, changes: TraceUpdate) -> Trace | None:
        row = self.rows.get(trace_id)
        if row is None:
            return None
        for name, value in changes.changed_fields().items():
            setattr(row, name, value)
        return row.to_orm()

    async def delete(self, trace_id: uuid.UUID) -> bool:
        return self.rows.pop(trace_id, None) is not None


@dataclass
class FakeUnitOfWork:
    """Rows only survive a block if ``commit()`` was called, like the real one."""

    committed: dict[uuid.UUID, _Row] = field(default_factory=dict)
    commits: int = 0

    def __post_init__(self) -> None:
        self.traces = FakeTraceRepository(copy.deepcopy(self.committed))

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
        self.committed = copy.deepcopy(self.traces.rows)
        self.commits += 1

    async def rollback(self) -> None:
        self.traces.rows = copy.deepcopy(self.committed)


class FakeOdooGateway:
    def __init__(
        self,
        result: GatewayResult | None = None,
        error: BaseException | None = None,
        on_call: Any = None,
    ) -> None:
        self.result = result or GatewayResult(payload={"steps": []}, odoo_version="19.0")
        self.error = error
        self.on_call = on_call
        self.requests: list[TraceRequest] = []

    async def run_trace(self, request: TraceRequest) -> GatewayResult:
        self.requests.append(request)
        if self.on_call is not None:
            self.on_call(request)
        if self.error is not None:
            raise self.error
        return self.result
