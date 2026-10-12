import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from flow_tracer_api.domain import TraceStatus
from flow_tracer_api.repositories import TraceRepository
from flow_tracer_api.repositories.sqlalchemy import SqlAlchemyTraceRepository
from flow_tracer_api.schemas import (
    GatewayResult,
    StartTraceCommand,
    TraceCreate,
    TraceDetail,
    TraceFilter,
    TraceListQuery,
    TracePage,
    TraceRequest,
    TraceSummary,
    TraceUpdate,
    ValidatedPayload,
)
from flow_tracer_api.services.common.errors import (
    NonDryRunNotAllowedError,
    OdooGatewayUnavailableError,
    TraceNotFoundError,
)
from flow_tracer_api.services.common.ports import (
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

        No DB transaction stays open while Odoo works: the trace is committed as ``running``
        first, Odoo is called outside any transaction, then the outcome is committed.
        """
        self._ensure_dry_run_allowed(command)
        gateway = self._require_gateway()
        trace_id = await self._create_running_trace(command)
        return await self._record(gateway, self._trace_request(trace_id, command))

    async def get_trace(self, trace_id: uuid.UUID) -> TraceDetail:
        trace = await self._traces.get(trace_id)
        if trace is None:
            raise TraceNotFoundError(
                message=f"Trace {trace_id} not found", status_code=HTTPStatus.NOT_FOUND
            )
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
            raise TraceNotFoundError(
                message=f"Trace {trace_id} not found", status_code=HTTPStatus.NOT_FOUND
            )
        await self._session.commit()

    def _ensure_dry_run_allowed(self, command: StartTraceCommand) -> None:
        if not command.dry_run and not self._allow_non_dry_run:
            raise NonDryRunNotAllowedError(
                message=(
                    "dry_run=false is disabled. It writes to the Odoo database and is only "
                    "allowed when explicitly enabled for a development setup."
                ),
                status_code=HTTPStatus.FORBIDDEN,
            )

    def _require_gateway(self) -> OdooGateway:
        if self._gateway is None:
            raise OdooGatewayUnavailableError(
                message="No connection to Odoo is configured, traces cannot be started",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            )
        return self._gateway

    async def _create_running_trace(self, command: StartTraceCommand) -> uuid.UUID:
        """Store the trace as ``running`` and commit, before Odoo is called."""
        trace = await self._traces.create(
            TraceCreate(
                entrypoint_model=command.entrypoint_model,
                entrypoint_method=command.entrypoint_method,
                dry_run=command.dry_run,
                status=TraceStatus.RUNNING,
                started_at=self._clock(),
            )
        )
        await self._session.commit()
        return trace.id

    @staticmethod
    def _trace_request(trace_id: uuid.UUID, command: StartTraceCommand) -> TraceRequest:
        return TraceRequest(
            trace_id=trace_id,
            model=command.entrypoint_model,
            method=command.entrypoint_method,
            record_ids=command.record_ids,
            context=command.context,
            call_kwargs=command.call_kwargs,
            dry_run=command.dry_run,
        )

    async def _record(self, gateway: OdooGateway, request: TraceRequest) -> TraceDetail:
        """Run the trace in Odoo and store the outcome, a failure as well as a success."""
        try:
            result, validated = await self._run_in_odoo(gateway, request)
        except (OdooGatewayError, PayloadValidationError) as exc:
            return await self._finish(
                request.trace_id, TraceUpdate(status=TraceStatus.FAILED, error=str(exc))
            )
        except Exception:
            # Never leave a trace stuck in "running"; the original error still propagates.
            logger.exception("Unexpected error while recording trace %s", request.trace_id)
            await self._finish(
                request.trace_id,
                TraceUpdate(status=TraceStatus.FAILED, error="Internal error while recording"),
            )
            raise
        return await self._finish(
            request.trace_id,
            TraceUpdate(
                status=TraceStatus.SUCCEEDED,
                payload=validated.payload,
                schema_version=validated.schema_version,
                odoo_version=result.odoo_version,
            ),
        )

    async def _run_in_odoo(
        self, gateway: OdooGateway, request: TraceRequest
    ) -> tuple[GatewayResult, ValidatedPayload]:
        """Call the recorder and accept its answer only as a valid trace of this very run."""
        result = await gateway.run_trace(request)
        validated = self._validator.validate(result.payload)
        self._check_answers_request(request, validated.payload)
        return result, validated

    async def _finish(self, trace_id: uuid.UUID, changes: TraceUpdate) -> TraceDetail:
        changes = TraceUpdate(**changes.changed_fields(), finished_at=self._clock())
        trace = await self._traces.update(trace_id, changes)
        if trace is None:
            raise TraceNotFoundError(
                message=f"Trace {trace_id} was deleted while it was being recorded",
                status_code=HTTPStatus.CONFLICT,
            )
        detail = TraceDetail.model_validate(trace)
        await self._session.commit()
        return detail

    @staticmethod
    def _check_answers_request(request: TraceRequest, payload: dict[str, Any]) -> None:
        """The recorder must have answered exactly this run; otherwise the trace is not stored
        as this trace (e.g. a proxy/cache mix-up or an addon bug)."""
        entrypoint = payload["entrypoint"]
        expected: dict[str, object] = {
            "trace_id": str(request.trace_id),
            "entrypoint.model": request.model,
            "entrypoint.method": request.method,
            "entrypoint.record_ids": list(request.record_ids),
            "entrypoint.kwargs": dict(request.call_kwargs),
            "dry_run": request.dry_run,
        }
        actual: dict[str, object] = {
            "trace_id": str(payload["trace_id"]),
            "entrypoint.model": entrypoint["model"],
            "entrypoint.method": entrypoint["method"],
            "entrypoint.record_ids": list(entrypoint["record_ids"]),
            "entrypoint.kwargs": entrypoint["kwargs"],
            "dry_run": payload["dry_run"],
        }
        wrong = [
            f"{key}={actual[key]!r} (expected {value!r})"
            for key, value in expected.items()
            if actual[key] != value
        ]
        if wrong:
            raise PayloadValidationError(
                "Recorder answered for a different run: " + ", ".join(wrong)
            )
