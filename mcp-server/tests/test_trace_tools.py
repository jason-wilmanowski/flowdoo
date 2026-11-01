from types import SimpleNamespace
from typing import Any

import pytest
from conftest import load_fixture
from flow_tracer_api.integrations.odoo.errors import OdooUnreachableError
from flow_tracer_api.schemas import GatewayResult, OdooConnectionStatus, TraceRequest
from flow_tracer_api.services.common.payload_validation import SchemaPayloadValidator
from mcp.server.mcpserver.exceptions import ToolError

from flowdoo_mcp.server import mcp
from flowdoo_mcp.tools.traces import get_step, run_trace

READY = OdooConnectionStatus(configured=True, ok=True, database_neutralized=True)


class FakeConnection:
    def __init__(self, status: OdooConnectionStatus) -> None:
        self.status = status

    async def check(self) -> OdooConnectionStatus:
        return self.status


class FakeGateway:
    def __init__(self, answer: dict[str, Any] | Exception) -> None:
        self.answer = answer
        self.requests: list[TraceRequest] = []

    async def run_trace(self, request: TraceRequest) -> GatewayResult:
        self.requests.append(request)
        if isinstance(self.answer, Exception):
            raise self.answer
        return GatewayResult(payload=self.answer)


def tool_context(status: OdooConnectionStatus, gateway: FakeGateway) -> Any:
    app = SimpleNamespace(
        connection=FakeConnection(status),
        gateway=gateway,
        validator=SchemaPayloadValidator(),
        traces={},
    )
    return SimpleNamespace(request_context=SimpleNamespace(lifespan_context=app))


@pytest.mark.anyio
async def test_all_tools_are_registered() -> None:
    names = {tool.name for tool in await mcp.list_tools()}

    assert names == {
        "odoo_status",
        "describe_entrypoint",
        "list_models",
        "describe_model",
        "run_trace",
        "list_traces",
        "trace_overview",
        "find_steps",
        "get_step",
    }


@pytest.mark.anyio
async def test_run_trace_is_always_a_dry_run_and_keeps_the_trace() -> None:
    trace = load_fixture("trace-small")
    gateway = FakeGateway(trace)
    ctx = tool_context(READY, gateway)

    overview = await run_trace(ctx, "sale.order", "action_confirm", record_ids=[1])

    assert gateway.requests[0].dry_run is True
    assert gateway.requests[0].record_ids == (1,)
    assert overview["trace_id"] == trace["trace_id"]
    assert ctx.request_context.lifespan_context.traces == {trace["trace_id"]: trace}


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("status", "message"),
    [
        (
            OdooConnectionStatus(configured=True, problems=["addon missing"]),
            "addon missing",
        ),
        (
            OdooConnectionStatus(configured=True, ok=True, database_neutralized=False),
            "neutralised",
        ),
        (
            OdooConnectionStatus(configured=True, ok=True, database_neutralized=None),
            "neutralised",
        ),
    ],
)
async def test_run_trace_refuses_before_calling_odoo(
    status: OdooConnectionStatus, message: str
) -> None:
    gateway = FakeGateway(load_fixture("trace-small"))

    with pytest.raises(ToolError, match=message):
        await run_trace(tool_context(status, gateway), "sale.order", "action_confirm")

    assert gateway.requests == []


@pytest.mark.anyio
async def test_run_trace_rejects_an_invalid_trace_and_keeps_nothing() -> None:
    ctx = tool_context(READY, FakeGateway({"steps": []}))

    with pytest.raises(ToolError, match="not a valid trace"):
        await run_trace(ctx, "sale.order", "action_confirm")

    assert ctx.request_context.lifespan_context.traces == {}


@pytest.mark.anyio
async def test_run_trace_passes_on_odoo_errors() -> None:
    ctx = tool_context(READY, FakeGateway(OdooUnreachableError("Cannot reach Odoo")))

    with pytest.raises(ToolError, match="Cannot reach Odoo"):
        await run_trace(ctx, "sale.order", "action_confirm")


@pytest.mark.anyio
async def test_get_step_of_an_unknown_trace_or_step() -> None:
    trace = load_fixture("trace-small")
    ctx = tool_context(READY, FakeGateway(trace))
    await run_trace(ctx, "sale.order", "action_confirm")

    with pytest.raises(ToolError, match="No trace"):
        await get_step(ctx, "nope", "s1")
    with pytest.raises(ToolError, match="no step"):
        await get_step(ctx, trace["trace_id"], "nope")
