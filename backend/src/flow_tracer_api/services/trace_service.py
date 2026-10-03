import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from flow_tracer_api.domain import TraceStatus
from flow_tracer_api.repositories import TraceCreate, TraceFilter, TraceUpdate, UnitOfWork
from flow_tracer_api.schemas import (
    StartTraceCommand,
    TraceDetail,
    TraceListQuery,
    TracePage,
    TraceSummary,
)
from flow_tracer_api.services.errors import NonDryRunNotAllowedError, TraceNotFoundError
from flow_tracer_api.services.ports import (
    OdooGateway,
    OdooGatewayError,
    PayloadValidationError,
    TracePayloadValidator,
    TraceRequest,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TraceService:
    def __init__(
        self,
        uow: UnitOfWork,
        gateway: OdooGateway,
        validator: TracePayloadValidator,
        *,
        allow_non_dry_run: bool = False,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._uow = uow
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

        async with self._uow:
            trace = await self._uow.traces.create(
                TraceCreate(
                    entrypoint_model=command.entrypoint_model,
                    entrypoint_method=command.entrypoint_method,
                    dry_run=command.dry_run,
                    status=TraceStatus.RUNNING,
                    started_at=self._clock(),
                )
            )
            await self._uow.commit()
        trace_id = trace.id

        request = TraceRequest(
            trace_id=trace_id,
            model=command.entrypoint_model,
            method=command.entrypoint_method,
            record_ids=command.record_ids,
            context=command.context,
            dry_run=command.dry_run,
        )
        try:
            result = await self._gateway.run_trace(request)
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
        async with self._uow:
            trace = await self._uow.traces.get(trace_id)
            if trace is None:
                raise TraceNotFoundError(trace_id)
            return TraceDetail.model_validate(trace)

    async def list_traces(self, query: TraceListQuery) -> TracePage:
        filters = TraceFilter(
            status=query.status,
            entrypoint_model=query.entrypoint_model,
            entrypoint_method=query.entrypoint_method,
        )
        async with self._uow:
            traces = await self._uow.traces.list_by(filters, limit=query.limit, offset=query.offset)
            total = await self._uow.traces.count(filters)
            return TracePage(
                items=[TraceSummary.model_validate(t) for t in traces],
                total=total,
                limit=query.limit,
                offset=query.offset,
            )

    async def delete_trace(self, trace_id: uuid.UUID) -> None:
        async with self._uow:
            if not await self._uow.traces.delete(trace_id):
                raise TraceNotFoundError(trace_id)
            await self._uow.commit()

    async def _finish(self, trace_id: uuid.UUID, changes: TraceUpdate) -> TraceDetail:
        changes = TraceUpdate(**changes.changed_fields(), finished_at=self._clock())
        async with self._uow:
            trace = await self._uow.traces.update(trace_id, changes)
            if trace is None:  # deleted while Odoo was running
                raise TraceNotFoundError(trace_id)
            await self._uow.commit()
            return TraceDetail.model_validate(trace)
