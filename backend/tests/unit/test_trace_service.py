import uuid

import pytest

from flow_tracer_api.domain import TraceStatus
from flow_tracer_api.repositories import UnitOfWork
from flow_tracer_api.schemas import (
    GatewayResult,
    StartTraceCommand,
    TraceDetail,
    TraceListQuery,
    TraceRequest,
)
from flow_tracer_api.services import NonDryRunNotAllowedError, TraceNotFoundError, TraceService
from flow_tracer_api.services.ports import OdooGateway, OdooGatewayError, OpaquePayloadValidator
from tests.unit.fakes import FIXED_NOW, FakeOdooGateway, FakeUnitOfWork

CONFIRM = StartTraceCommand(
    entrypoint_model="sale.order",
    entrypoint_method="action_confirm",
    record_ids=(7,),
    context={"lang": "en_US"},
)


def _service(
    uow: FakeUnitOfWork, gateway: FakeOdooGateway, *, allow_non_dry_run: bool = False
) -> TraceService:
    # Static check that the fakes satisfy the protocols the service depends on.
    typed_uow: UnitOfWork = uow
    typed_gateway: OdooGateway = gateway
    return TraceService(
        typed_uow,
        typed_gateway,
        OpaquePayloadValidator(),
        allow_non_dry_run=allow_non_dry_run,
        clock=lambda: FIXED_NOW,
    )


async def test_start_trace_succeeds_and_stores_payload() -> None:
    uow = FakeUnitOfWork()
    gateway = FakeOdooGateway(GatewayResult(payload={"steps": [{"id": "s1"}]}, odoo_version="19.0"))

    result = await _service(uow, gateway).start_trace(CONFIRM)

    assert type(result) is TraceDetail
    assert result.status is TraceStatus.SUCCEEDED
    assert result.payload == {"steps": [{"id": "s1"}]}
    assert result.odoo_version == "19.0"
    assert result.schema_version is None  # opaque until the trace schema exists
    assert result.started_at == FIXED_NOW
    assert result.finished_at == FIXED_NOW
    assert result.error is None
    assert result.dry_run is True
    assert uow.commits == 2
    assert uow.committed[result.id].status is TraceStatus.SUCCEEDED


async def test_start_trace_passes_request_to_gateway() -> None:
    gateway = FakeOdooGateway()

    result = await _service(FakeUnitOfWork(), gateway).start_trace(CONFIRM)

    assert gateway.requests == [
        TraceRequest(
            trace_id=result.id,
            model="sale.order",
            method="action_confirm",
            record_ids=(7,),
            context={"lang": "en_US"},
            dry_run=True,
        )
    ]


async def test_trace_is_committed_as_running_before_odoo_is_called() -> None:
    uow = FakeUnitOfWork()
    seen: list[TraceStatus] = []

    def check_committed(request: TraceRequest) -> None:
        seen.append(uow.committed[request.trace_id].status)

    await _service(uow, FakeOdooGateway(on_call=check_committed)).start_trace(CONFIRM)

    assert seen == [TraceStatus.RUNNING]


async def test_gateway_error_marks_trace_failed() -> None:
    uow = FakeUnitOfWork()
    gateway = FakeOdooGateway(error=OdooGatewayError("flow_tracer addon is not installed"))

    result = await _service(uow, gateway).start_trace(CONFIRM)

    assert result.status is TraceStatus.FAILED
    assert result.error == "flow_tracer addon is not installed"
    assert result.payload is None
    assert result.finished_at == FIXED_NOW
    assert uow.committed[result.id].status is TraceStatus.FAILED


async def test_invalid_payload_marks_trace_failed() -> None:
    gateway = FakeOdooGateway(GatewayResult(payload={"value": float("nan")}))

    result = await _service(FakeUnitOfWork(), gateway).start_trace(CONFIRM)

    assert result.status is TraceStatus.FAILED
    assert result.error is not None
    assert "not valid JSON" in result.error


async def test_unexpected_error_marks_trace_failed_and_propagates() -> None:
    uow = FakeUnitOfWork()
    gateway = FakeOdooGateway(error=KeyError("bug"))

    with pytest.raises(KeyError):
        await _service(uow, gateway).start_trace(CONFIRM)

    [row] = uow.committed.values()
    assert row.status is TraceStatus.FAILED
    assert row.error == "Internal error while recording"


async def test_non_dry_run_is_rejected_by_default() -> None:
    uow = FakeUnitOfWork()
    gateway = FakeOdooGateway()

    with pytest.raises(NonDryRunNotAllowedError):
        await _service(uow, gateway).start_trace(CONFIRM.model_copy(update={"dry_run": False}))

    assert uow.committed == {}
    assert gateway.requests == []


async def test_non_dry_run_runs_when_explicitly_allowed() -> None:
    gateway = FakeOdooGateway()
    service = _service(FakeUnitOfWork(), gateway, allow_non_dry_run=True)

    result = await service.start_trace(CONFIRM.model_copy(update={"dry_run": False}))

    assert result.dry_run is False
    assert gateway.requests[0].dry_run is False


async def test_get_trace_returns_dto() -> None:
    uow = FakeUnitOfWork()
    service = _service(uow, FakeOdooGateway())
    started = await service.start_trace(CONFIRM)

    loaded = await service.get_trace(started.id)

    assert loaded == started


async def test_get_trace_unknown_id_raises() -> None:
    with pytest.raises(TraceNotFoundError):
        await _service(FakeUnitOfWork(), FakeOdooGateway()).get_trace(uuid.uuid4())


async def test_list_traces_filters_and_reports_total() -> None:
    uow = FakeUnitOfWork()
    service = _service(uow, FakeOdooGateway())
    await service.start_trace(CONFIRM)
    await service.start_trace(CONFIRM)
    await service.start_trace(
        StartTraceCommand(entrypoint_model="account.move", entrypoint_method="action_post")
    )

    page = await service.list_traces(TraceListQuery(entrypoint_model="sale.order", limit=1))

    assert page.total == 2
    assert page.limit == 1
    assert len(page.items) == 1
    assert page.items[0].entrypoint_model == "sale.order"
    assert not hasattr(page.items[0], "payload")


async def test_delete_trace_commits() -> None:
    uow = FakeUnitOfWork()
    service = _service(uow, FakeOdooGateway())
    started = await service.start_trace(CONFIRM)

    await service.delete_trace(started.id)

    assert started.id not in uow.committed


async def test_delete_unknown_trace_raises() -> None:
    with pytest.raises(TraceNotFoundError):
        await _service(FakeUnitOfWork(), FakeOdooGateway()).delete_trace(uuid.uuid4())
