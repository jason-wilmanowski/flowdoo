import uuid
from http import HTTPStatus
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from flow_tracer_api.domain import TraceStatus
from flow_tracer_api.repositories import TraceRepository
from flow_tracer_api.schemas import (
    GatewayResult,
    StartTraceCommand,
    TraceDetail,
    TraceListQuery,
    TraceRequest,
)
from flow_tracer_api.services import (
    NonDryRunNotAllowedError,
    OdooGatewayUnavailableError,
    TraceNotFoundError,
    TraceService,
)
from flow_tracer_api.services.payload_validation import SchemaPayloadValidator
from flow_tracer_api.services.ports import OdooGateway, OdooGatewayError
from tests.fixtures import load_fixture
from tests.unit.fakes import (
    FIXED_NOW,
    FakeOdooGateway,
    FakeSession,
    FakeTraceRepository,
    answer_for,
)

CONFIRM = StartTraceCommand(
    entrypoint_model="sale.order",
    entrypoint_method="action_confirm",
    record_ids=(7,),
    context={"lang": "en_US"},
)


def _service(
    session: FakeSession, gateway: FakeOdooGateway, *, allow_non_dry_run: bool = False
) -> TraceService:
    # Static check that the fakes satisfy the protocols the service depends on.
    repository: TraceRepository = FakeTraceRepository(session)
    typed_gateway: OdooGateway = gateway
    return TraceService(
        cast(AsyncSession, session),
        typed_gateway,
        SchemaPayloadValidator(),
        allow_non_dry_run=allow_non_dry_run,
        clock=lambda: FIXED_NOW,
        trace_repository=repository,
    )


async def test_start_trace_succeeds_and_stores_payload() -> None:
    session = FakeSession()
    payload = load_fixture("trace-medium")
    gateway = FakeOdooGateway(GatewayResult(payload=payload, odoo_version="19.0"))

    result = await _service(session, gateway).start_trace(CONFIRM)

    assert type(result) is TraceDetail
    assert result.status is TraceStatus.SUCCEEDED
    assert result.payload == answer_for(gateway.requests[0], payload)
    assert result.payload["trace_id"] == str(result.id)
    assert result.odoo_version == "19.0"
    assert result.schema_version == "0.1.0"
    assert result.started_at == FIXED_NOW
    assert result.finished_at == FIXED_NOW
    assert result.error is None
    assert result.dry_run is True
    assert session.commits == 2
    assert session.committed[result.id].status is TraceStatus.SUCCEEDED


async def test_start_trace_passes_request_to_gateway() -> None:
    gateway = FakeOdooGateway()

    result = await _service(FakeSession(), gateway).start_trace(CONFIRM)

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
    session = FakeSession()
    seen: list[TraceStatus] = []

    def check_committed(request: TraceRequest) -> None:
        seen.append(session.committed[request.trace_id].status)

    await _service(session, FakeOdooGateway(on_call=check_committed)).start_trace(CONFIRM)

    assert seen == [TraceStatus.RUNNING]


async def test_gateway_error_marks_trace_failed() -> None:
    session = FakeSession()
    gateway = FakeOdooGateway(error=OdooGatewayError("flow_tracer addon is not installed"))

    result = await _service(session, gateway).start_trace(CONFIRM)

    assert result.status is TraceStatus.FAILED
    assert result.error == "flow_tracer addon is not installed"
    assert result.payload is None
    assert result.finished_at == FIXED_NOW
    assert session.committed[result.id].status is TraceStatus.FAILED


async def test_invalid_payload_marks_trace_failed() -> None:
    gateway = FakeOdooGateway(GatewayResult(payload={"value": float("nan")}), echo_request=False)

    result = await _service(FakeSession(), gateway).start_trace(CONFIRM)

    assert result.status is TraceStatus.FAILED
    assert result.error is not None
    assert "not valid JSON" in result.error


async def test_unexpected_error_marks_trace_failed_and_propagates() -> None:
    session = FakeSession()
    gateway = FakeOdooGateway(error=KeyError("bug"))

    with pytest.raises(KeyError):
        await _service(session, gateway).start_trace(CONFIRM)

    [row] = session.committed.values()
    assert row.status is TraceStatus.FAILED
    assert row.error == "Internal error while recording"


async def test_non_dry_run_is_rejected_by_default() -> None:
    session = FakeSession()
    gateway = FakeOdooGateway()

    with pytest.raises(NonDryRunNotAllowedError) as exc_info:
        await _service(session, gateway).start_trace(CONFIRM.model_copy(update={"dry_run": False}))

    assert exc_info.value.status_code == HTTPStatus.FORBIDDEN
    assert "dry_run=false is disabled" in exc_info.value.message

    assert session.committed == {}
    assert gateway.requests == []


async def test_non_dry_run_runs_when_explicitly_allowed() -> None:
    gateway = FakeOdooGateway()
    service = _service(FakeSession(), gateway, allow_non_dry_run=True)

    result = await service.start_trace(CONFIRM.model_copy(update={"dry_run": False}))

    assert result.dry_run is False
    assert gateway.requests[0].dry_run is False


async def test_get_trace_returns_dto() -> None:
    session = FakeSession()
    service = _service(session, FakeOdooGateway())
    started = await service.start_trace(CONFIRM)

    loaded = await service.get_trace(started.id)

    assert loaded == started


async def test_get_trace_unknown_id_raises() -> None:
    with pytest.raises(TraceNotFoundError):
        await _service(FakeSession(), FakeOdooGateway()).get_trace(uuid.uuid4())


async def test_list_traces_filters_and_reports_total() -> None:
    session = FakeSession()
    service = _service(session, FakeOdooGateway())
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
    session = FakeSession()
    service = _service(session, FakeOdooGateway())
    started = await service.start_trace(CONFIRM)

    await service.delete_trace(started.id)

    assert started.id not in session.committed


async def test_delete_unknown_trace_raises() -> None:
    with pytest.raises(TraceNotFoundError):
        await _service(FakeSession(), FakeOdooGateway()).delete_trace(uuid.uuid4())


async def test_start_trace_without_gateway_writes_nothing() -> None:
    session = FakeSession()
    service = TraceService(
        cast(AsyncSession, session),
        None,
        SchemaPayloadValidator(),
        trace_repository=FakeTraceRepository(session),
    )

    with pytest.raises(OdooGatewayUnavailableError) as exc_info:
        await service.start_trace(CONFIRM)

    assert exc_info.value.status_code == HTTPStatus.SERVICE_UNAVAILABLE

    assert session.rows == {}
    assert session.commits == 0


async def test_not_found_errors_carry_404_and_message() -> None:
    service = _service(FakeSession(), FakeOdooGateway())
    missing = uuid.uuid4()

    with pytest.raises(TraceNotFoundError) as on_get:
        await service.get_trace(missing)
    with pytest.raises(TraceNotFoundError) as on_delete:
        await service.delete_trace(missing)

    for exc_info in (on_get, on_delete):
        assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
        assert exc_info.value.message == f"Trace {missing} not found"


async def test_trace_deleted_during_recording_is_409() -> None:
    session = FakeSession()

    def delete_while_running(request: TraceRequest) -> None:
        del session.rows[request.trace_id]

    service = _service(session, FakeOdooGateway(on_call=delete_while_running))

    with pytest.raises(TraceNotFoundError) as exc_info:
        await service.start_trace(CONFIRM)

    assert exc_info.value.status_code == HTTPStatus.CONFLICT
    assert "deleted while it was being recorded" in exc_info.value.message


@pytest.mark.parametrize(
    ("mutate", "fragment"),
    [
        (lambda p: p.update(trace_id="00000000-0000-0000-0000-000000000000"), "trace_id="),
        (lambda p: p.update(dry_run=False), "dry_run=False (expected True)"),
        (lambda p: p["entrypoint"].update(method="action_cancel"), "entrypoint.method="),
        (lambda p: p["entrypoint"].update(record_ids=[99]), "entrypoint.record_ids=[99]"),
    ],
)
async def test_answer_for_another_run_marks_trace_failed(mutate: Any, fragment: str) -> None:
    class WrongAnswerGateway(FakeOdooGateway):
        async def run_trace(self, request: TraceRequest) -> GatewayResult:
            result = await super().run_trace(request)
            mutate(result.payload)
            return result

    session = FakeSession()

    result = await _service(session, WrongAnswerGateway()).start_trace(CONFIRM)

    assert result.status is TraceStatus.FAILED
    assert result.payload is None
    assert result.error is not None
    assert result.error.startswith("Recorder answered for a different run")
    assert fragment in result.error
