import json
import subprocess
import sys
from collections.abc import Callable
from functools import partial
from typing import Any

import httpx
import pytest
from conftest import load_fixture
from flow_tracer_api.integrations.odoo.client import OdooJson2Client
from mcp.client import Client

import flowdoo_mcp.tools  # noqa: F401
from flowdoo_mcp import server
from flowdoo_mcp.config import get_settings
from flowdoo_mcp.server import MAX_STORED_TRACES, AppContext, mcp

ADDON_READY = {"enabled": True, "recorder_available": True, "is_admin": True}

Answers = dict[str, Any]
UseOdoo = Callable[[Answers], list[str]]


def fake_odoo(answers: Answers, seen: list[str]) -> Callable[[httpx.Request], httpx.Response]:
    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        answer = answers.get(request.url.path)
        if answer is None:
            return httpx.Response(404, json={"message": f"no route {request.url.path}"})
        return httpx.Response(200, json=answer)

    return handle


def ready_odoo(trace: dict[str, Any], *, neutralized: int = 1) -> Answers:
    return {
        "/web/webclient/version_info": {
            "result": {"server_version": "19.0-1", "server_serie": "19.0"}
        },
        "/json/2/res.users/context_get": {"uid": 2},
        "/json/2/res.users/read": [{"login": "admin"}],
        "/flow_tracer/v1/status": ADDON_READY,
        "/json/2/ir.ui.view/search_count": neutralized,
        "/flow_tracer/v1/trace": trace,
    }


@pytest.fixture
def use_odoo(monkeypatch: pytest.MonkeyPatch) -> UseOdoo:
    """Answer the real client's requests from a table; returns the paths that were called."""
    monkeypatch.setenv("ODOO_URL", "http://odoo.test")
    monkeypatch.setenv("ODOO_DB", "dev")
    monkeypatch.setenv("ODOO_API_KEY", "key")
    monkeypatch.delenv("ODOO_LOGIN", raising=False)
    get_settings.cache_clear()

    def install(answers: Answers) -> list[str]:
        seen: list[str] = []
        transport = httpx.MockTransport(fake_odoo(answers, seen))
        client = partial(OdooJson2Client, transport=transport)
        monkeypatch.setattr(server, "OdooJson2Client", client)
        return seen

    return install


async def call(client: Client, tool: str, **arguments: Any) -> Any:
    result = await client.call_tool(tool, arguments)
    assert not result.is_error, result.content[0].text
    return json.loads(result.content[0].text)


async def listed_traces(client: Client) -> list[dict[str, Any]]:
    result = await client.call_tool("list_traces", {})
    assert not result.is_error
    return [json.loads(item.text) for item in result.content]


async def error_of(client: Client, tool: str, **arguments: Any) -> str:
    result = await client.call_tool(tool, arguments)
    assert result.is_error
    text: str = result.content[0].text
    return text


def test_importing_the_tools_loads_nothing_of_the_backend_stack() -> None:
    code = (
        "import sys, flowdoo_mcp.main, flowdoo_mcp.tools;"
        "heavy = ('sqlalchemy', 'fastapi', 'flow_tracer_api.services');"
        "print([m for m in heavy if m in sys.modules])"
    )

    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )

    assert result.stdout.strip() == "[]"


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
async def test_a_kept_trace_can_be_read_with_the_other_tools(use_odoo: UseOdoo) -> None:
    trace = load_fixture("trace-error")
    trace_id = trace["trace_id"]
    use_odoo(ready_odoo(trace))

    async with Client(mcp) as client:
        overview = await call(
            client, "run_trace", model="sale.order", method="action_confirm", record_ids=[3]
        )
        listed = await listed_traces(client)
        again = await call(client, "trace_overview", trace_id=trace_id)
        found = await call(client, "find_steps", trace_id=trace_id, failed_only=True)
        step = await call(client, "get_step", trace_id=trace_id, step_id="s2")

    assert overview["trace_id"] == trace_id
    assert overview["dry_run"] is True
    assert overview["failures"][0]["step"] == "s1"
    assert [item["trace_id"] for item in listed] == [trace_id]
    assert again == overview
    assert [item["id"] for item in found["steps"]] == ["s1"]
    assert step["step"]["id"] == "s2"


@pytest.mark.anyio
async def test_run_trace_always_asks_for_a_dry_run(use_odoo: UseOdoo) -> None:
    use_odoo(ready_odoo(load_fixture("trace-small")))
    bodies: list[dict[str, Any]] = []
    original = OdooJson2Client.post

    async def spy(self: OdooJson2Client, path: str, payload: dict[str, Any], **kw: Any) -> Any:
        if path.endswith("/trace"):
            bodies.append(payload)
        return await original(self, path, payload, **kw)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(OdooJson2Client, "post", spy)
        async with Client(mcp) as client:
            await call(client, "run_trace", model="sale.order", method="action_confirm")

    assert bodies[0]["dry_run"] is True


@pytest.mark.anyio
async def test_traces_are_gone_with_the_session(use_odoo: UseOdoo) -> None:
    trace = load_fixture("trace-small")
    use_odoo(ready_odoo(trace))

    async with Client(mcp) as client:
        await call(client, "run_trace", model="sale.order", method="action_confirm")
    async with Client(mcp) as client:
        message = await error_of(client, "get_step", trace_id=trace["trace_id"], step_id="s1")

    assert "No trace" in message


@pytest.mark.anyio
async def test_refuses_a_database_that_is_not_neutralised(use_odoo: UseOdoo) -> None:
    seen = use_odoo(ready_odoo(load_fixture("trace-small"), neutralized=0))

    async with Client(mcp) as client:
        message = await error_of(client, "run_trace", model="sale.order", method="action_confirm")

    assert "neutralised" in message
    assert "/flow_tracer/v1/trace" not in seen


@pytest.mark.anyio
async def test_refuses_when_the_addon_is_switched_off(use_odoo: UseOdoo) -> None:
    answers = ready_odoo(load_fixture("trace-small"))
    answers["/flow_tracer/v1/status"] = {**ADDON_READY, "enabled": False}
    seen = use_odoo(answers)

    async with Client(mcp) as client:
        message = await error_of(client, "run_trace", model="sale.order", method="action_confirm")

    assert "switched off" in message
    assert "/flow_tracer/v1/trace" not in seen


@pytest.mark.anyio
async def test_status_checks_the_expected_login(
    use_odoo: UseOdoo, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ODOO_LOGIN", "someone")
    get_settings.cache_clear()
    use_odoo(ready_odoo(load_fixture("trace-small")))

    async with Client(mcp) as client:
        status = await call(client, "odoo_status")

    assert status["ok"] is False
    assert "ODOO_LOGIN" in status["problems"][0]


@pytest.mark.anyio
async def test_an_invalid_trace_is_rejected_and_not_kept(use_odoo: UseOdoo) -> None:
    use_odoo(ready_odoo({"steps": []}))

    async with Client(mcp) as client:
        message = await error_of(client, "run_trace", model="sale.order", method="action_confirm")
        listed = await listed_traces(client)

    assert "not a valid trace" in message
    assert listed == []


@pytest.mark.anyio
async def test_unknown_trace_and_step_explain_themselves(use_odoo: UseOdoo) -> None:
    trace = load_fixture("trace-small")
    use_odoo(ready_odoo(trace))

    async with Client(mcp) as client:
        await call(client, "run_trace", model="sale.order", method="action_confirm")
        unknown_trace = await error_of(client, "get_step", trace_id="nope", step_id="s1")
        unknown_step = await error_of(
            client, "get_step", trace_id=trace["trace_id"], step_id="nope"
        )

    assert "No trace" in unknown_trace
    assert "no step" in unknown_step


@pytest.mark.anyio
async def test_odoo_errors_reach_the_model(use_odoo: UseOdoo) -> None:
    use_odoo({})

    async with Client(mcp) as client:
        message = await error_of(client, "describe_model", model="nope")

    assert "no route /flow_tracer/v1/model" in message


@pytest.mark.anyio
async def test_status_reports_problems_instead_of_failing(use_odoo: UseOdoo) -> None:
    use_odoo({})

    async with Client(mcp) as client:
        status = await call(client, "odoo_status")

    assert status["ok"] is False
    assert status["problems"]


def test_only_the_latest_traces_are_kept() -> None:
    app = AppContext(client=None, gateway=None)  # type: ignore[arg-type]

    for number in range(MAX_STORED_TRACES + 2):
        app.keep_trace({"trace_id": str(number)})

    assert len(app.traces) == MAX_STORED_TRACES
    assert "0" not in app.traces
    assert str(MAX_STORED_TRACES + 1) in app.traces
