import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from flow_tracer_api.domain import TraceStatus
from flow_tracer_api.repositories import TraceRepository
from flow_tracer_api.repositories.sqlalchemy import SqlAlchemyTraceRepository
from flow_tracer_api.schemas import (
    StartTraceCommand,
    TraceCreate,
    TraceDetail,
    TraceFilter,
    TraceListQuery,
    TracePage,
    TraceRequest,
    TraceSummary,
    TraceUpdate,
)
from flow_tracer_api.services.errors import (
    NonDryRunNotAllowedError,
    OdooGatewayUnavailableError,
    TraceNotFoundError,
)
from flow_tracer_api.services.ports import (
    OdooGateway,
    OdooGatewayError,
    PayloadValidationError,
    TracePayloadValidator,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TraceService:
    """Business logic for traces.

    Gets the request-scoped ``AsyncSession`` injected (see ``api.dependencies``) and builds
    its repository on it. The service owns the transaction: it decides when to
    ``commit()``. Anything not committed is rolled back when the request's session closes.

    ``gateway`` is ``None`` while no Odoo connection is configured; then only
    ``start_trace`` fails, reading and deleting stored traces keeps working.
    """

    def __init__(
        self,
        session: AsyncSession,
        gateway: OdooGateway | None,
        validator: TracePayloadValidator,
        *,
        allow_non_dry_run: bool = False,
        clock: Callable[[], datetime] = _utcnow,
        trace_repository: TraceRepository | None = None,
    ) -> None:
        self._session = session
        # trace_repository is only overridden in tests (in-memory fake).
        self._traces: TraceRepository = trace_repository or SqlAlchemyTraceRepository(session)
        self._gateway = gateway
        self._validator = validator
        self._allow_non_dry_run = allow_non_dry_run
        self._clock = clock

    async def start_trace(self, command: StartTraceCommand) -> TraceDetail:
        """Record one workflow run.

        Three steps, so no DB transaction stays open while Odoo works:
        1. persist the trace as ``running`` and commit,
        2. call Odoo and validate the payload (outside any transaction),
        3. store the outcome (``succeeded`` or ``failed``) and commit.
        """
        if not command.dry_run and not self._allow_non_dry_run:
            raise NonDryRunNotAllowedError
        if self._gateway is None:
            raise OdooGatewayUnavailableError
        gateway = self._gateway

        trace = await self._traces.create(
            TraceCreate(
                entrypoint_model=command.entrypoint_model,
                entrypoint_method=command.entrypoint_method,
                dry_run=command.dry_run,
                status=TraceStatus.RUNNING,
                started_at=self._clock(),
            )
        )
        trace_id = trace.id
        await self._session.commit()

        request = TraceRequest(
            trace_id=trace_id,
            model=command.entrypoint_model,
            method=command.entrypoint_method,
            record_ids=command.record_ids,
            context=command.context,
            dry_run=command.dry_run,
        )
        try:
            result = await gateway.run_trace(request)
            validated = self._validator.validate(result.payload)
        except (OdooGatewayError, PayloadValidationError) as exc:
            return await self._finish(
                trace_id, TraceUpdate(status=TraceStatus.FAILED, error=str(exc))
            )
        except Exception:
            # Never leave a trace stuck in "running"; the original error still propagates.
            logger.exception("Unexpected error while recording trace %s", trace_id)
            await self._finish(
                trace_id,
                TraceUpdate(status=TraceStatus.FAILED, error="Internal error while recording"),
            )
            raise

        return await self._finish(
            trace_id,
            TraceUpdate(
                status=TraceStatus.SUCCEEDED,
                payload=validated.payload,
                schema_version=validated.schema_version,
                odoo_version=result.odoo_version,
            ),
        )

    async def get_trace(self, trace_id: uuid.UUID) -> TraceDetail:
        trace = await self._traces.get(trace_id)
        if trace is None:
            raise TraceNotFoundError(trace_id)
        return TraceDetail.model_validate(trace)

    async def list_traces(self, query: TraceListQuery) -> TracePage:
        filters = TraceFilter(
            status=query.status,
            entrypoint_model=query.entrypoint_model,
            entrypoint_method=query.entrypoint_method,
        )
        traces = await self._traces.list_by(filters, limit=query.limit, offset=query.offset)
        total = await self._traces.count(filters)
        return TracePage(
            items=[TraceSummary.model_validate(t) for t in traces],
            total=total,
            limit=query.limit,
            offset=query.offset,
        )

    async def delete_trace(self, trace_id: uuid.UUID) -> None:
        if not await self._traces.delete(trace_id):
            raise TraceNotFoundError(trace_id)
        await self._session.commit()

    async def _finish(self, trace_id: uuid.UUID, changes: TraceUpdate) -> TraceDetail:
        changes = TraceUpdate(**changes.changed_fields(), finished_at=self._clock())
        trace = await self._traces.update(trace_id, changes)
        if trace is None:  # deleted while Odoo was running
            raise TraceNotFoundError(trace_id)
        detail = TraceDetail.model_validate(trace)
        await self._session.commit()
        return detail
