"""Backend -> flow_tracer addon -> real Odoo 19 -> trace stored in Postgres."""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from flow_tracer_api.domain import TraceStatus
from flow_tracer_api.integrations.odoo import FlowTracerGateway, OdooJson2Client
from flow_tracer_api.schemas import StartTraceCommand
from flow_tracer_api.services import TraceService
from flow_tracer_api.services.payload_validation import SCHEMA_VERSION, SchemaPayloadValidator

pytestmark = [pytest.mark.integration, pytest.mark.odoo]


@pytest.fixture
async def contact_id(odoo_client: OdooJson2Client) -> AsyncIterator[int]:
    """A contact whose create_company creates and links a company (base-only flow)."""
    [partner_id] = await odoo_client.call(
        "res.partner",
        "create",
        vals_list=[{"name": "Flowdoo e2e contact", "company_name": "Flowdoo e2e company"}],
    )
    yield partner_id
    await odoo_client.call("res.partner", "unlink", ids=[partner_id])


async def test_trace_is_recorded_validated_and_stored(
    db_session: AsyncSession, odoo_client: OdooJson2Client, contact_id: int
) -> None:
    service = TraceService(
        db_session, FlowTracerGateway(odoo_client, timeout_seconds=120), SchemaPayloadValidator()
    )

    trace = await service.start_trace(
        StartTraceCommand(
            entrypoint_model="res.partner",
            entrypoint_method="create_company",
            record_ids=(contact_id,),
        )
    )

    assert trace.status is TraceStatus.SUCCEEDED, trace.error
    assert trace.odoo_version == "19.0"
    assert trace.schema_version == SCHEMA_VERSION
    assert trace.payload is not None
    assert trace.payload["trace_id"] == str(trace.id)
    steps = trace.payload["steps"]
    assert steps[0]["model"] == "res.partner"
    assert steps[0]["method"] == "create_company"
    assert steps[0]["module"] == "base"
    assert any(
        c["field"] == "parent_id" and c["record_id"] == contact_id
        for s in steps
        for c in s["changes"]
    )
    assert await service.get_trace(trace.id) == trace

    # Dry run: Odoo is unchanged.
    [contact] = await odoo_client.call(
        "res.partner", "read", ids=[contact_id], fields=["parent_id"]
    )
    assert contact["parent_id"] is False


async def test_unknown_method_becomes_a_failed_trace(
    db_session: AsyncSession, odoo_client: OdooJson2Client, contact_id: int
) -> None:
    service = TraceService(
        db_session, FlowTracerGateway(odoo_client, timeout_seconds=120), SchemaPayloadValidator()
    )

    trace = await service.start_trace(
        StartTraceCommand(
            entrypoint_model="res.partner",
            entrypoint_method="no_such_method",
            record_ids=(contact_id,),
        )
    )

    assert trace.status is TraceStatus.FAILED
    assert trace.error is not None
    assert "HTTP 404" in trace.error
    assert "no_such_method" in trace.error
