"""TraceService on a real session: the service builds SqlAlchemyTraceRepository itself."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flow_tracer_api.domain import TraceStatus
from flow_tracer_api.models import Trace
from flow_tracer_api.schemas import GatewayResult, StartTraceCommand, TraceListQuery
from flow_tracer_api.services import TraceService
from flow_tracer_api.services.payload_validation import SchemaPayloadValidator
from flow_tracer_api.services.ports import OdooGatewayError
from tests.fixtures import load_fixture
from tests.unit.fakes import FakeOdooGateway, answer_for

pytestmark = pytest.mark.integration

CONFIRM = StartTraceCommand(entrypoint_model="sale.order", entrypoint_method="action_confirm")


async def test_start_trace_persists_through_injected_session(db_session: AsyncSession) -> None:
    payload = load_fixture("trace-small")
    gateway = FakeOdooGateway(GatewayResult(payload=payload, odoo_version="19.0"))
    service = TraceService(db_session, gateway, SchemaPayloadValidator())

    result = await service.start_trace(CONFIRM)

    db_session.expunge_all()
    row = await db_session.scalar(select(Trace).where(Trace.id == result.id))
    assert row is not None
    assert row.status is TraceStatus.SUCCEEDED
    assert row.payload == answer_for(gateway.requests[0], payload)
    assert row.schema_version == "0.1.0"
    assert row.odoo_version == "19.0"
    assert row.finished_at is not None
    assert await service.get_trace(result.id) == result


async def test_gateway_failure_is_persisted(db_session: AsyncSession) -> None:
    gateway = FakeOdooGateway(error=OdooGatewayError("Odoo unreachable"))
    service = TraceService(db_session, gateway, SchemaPayloadValidator())

    result = await service.start_trace(CONFIRM)

    db_session.expunge_all()
    row = await db_session.get(Trace, result.id)
    assert row is not None
    assert row.status is TraceStatus.FAILED
    assert row.error == "Odoo unreachable"


async def test_delete_and_list(db_session: AsyncSession) -> None:
    service = TraceService(db_session, FakeOdooGateway(), SchemaPayloadValidator())
    first = await service.start_trace(CONFIRM)
    await service.start_trace(CONFIRM)

    await service.delete_trace(first.id)

    page = await service.list_traces(TraceListQuery())
    assert page.total == 1
    assert first.id not in {item.id for item in page.items}
