import json
import uuid
from collections.abc import Callable

import httpx
import pytest

from flow_tracer_api.integrations.odoo import (
    FlowTracerGateway,
    OdooAuthenticationError,
    OdooCallError,
    OdooJson2Client,
    OdooUnreachableError,
)
from flow_tracer_api.schemas import TraceRequest
from flow_tracer_api.services.ports import OdooGateway, OdooGatewayError
from tests.fixtures import load_fixture

REQUEST = TraceRequest(
    trace_id=uuid.UUID("3f2b8c1e-6d4a-4c1e-9b7a-1a2b3c4d5e01"),
    model="sale.order",
    method="action_confirm",
    record_ids=(1,),
    context={"lang": "en_US"},
    dry_run=True,
)


def _gateway(handler: Callable[[httpx.Request], httpx.Response]) -> FlowTracerGateway:
    client = OdooJson2Client(
        base_url="http://odoo:8069",
        database="dev",
        api_key="secret-key",
        timeout_seconds=10,
        transport=httpx.MockTransport(handler),
    )
    gateway: OdooGateway = FlowTracerGateway(client, timeout_seconds=120)  # satisfies the port
    assert isinstance(gateway, FlowTracerGateway)
    return gateway


async def test_posts_the_run_to_the_addon_and_returns_its_trace() -> None:
    seen: list[httpx.Request] = []
    trace = load_fixture("trace-small")

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=trace)

    result = await _gateway(handler).run_trace(REQUEST)

    assert result.payload == trace
    assert result.odoo_version == "19.0"
    [request] = seen
    assert request.url == "http://odoo:8069/flow_tracer/v1/trace"
    assert request.headers["Authorization"] == "bearer secret-key"
    assert request.headers["X-Odoo-Database"] == "dev"
    assert json.loads(request.content) == {
        "trace_id": "3f2b8c1e-6d4a-4c1e-9b7a-1a2b3c4d5e01",
        "model": "sale.order",
        "method": "action_confirm",
        "record_ids": [1],
        "context": {"lang": "en_US"},
        "dry_run": True,
    }
    assert request.extensions["timeout"]["read"] == 120  # trace timeout, not the default


@pytest.mark.parametrize(
    ("response", "error_type", "fragment"),
    [
        (
            httpx.Response(403, json={"message": "flow_tracer is disabled: set ..."}),
            OdooCallError,
            "flow_tracer trace failed with HTTP 403: flow_tracer is disabled",
        ),
        (
            httpx.Response(401, json={"message": "Invalid apikey"}),
            OdooAuthenticationError,
            "API key",
        ),
        (
            httpx.Response(404, text="<!DOCTYPE html>Not Found"),
            OdooCallError,
            "flow_tracer addon is not installed/up to date",
        ),
        (httpx.Response(200, json=[1, 2]), OdooCallError, "answered with list"),
    ],
)
async def test_failures_become_gateway_errors(
    response: httpx.Response, error_type: type[Exception], fragment: str
) -> None:
    with pytest.raises(error_type, match=fragment) as exc_info:
        await _gateway(lambda request: response).run_trace(REQUEST)

    assert isinstance(exc_info.value, OdooGatewayError)  # what TraceService catches
    assert "secret-key" not in str(exc_info.value)


async def test_timeout_becomes_unreachable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    with pytest.raises(OdooUnreachableError, match="did not answer in time"):
        await _gateway(handler).run_trace(REQUEST)
