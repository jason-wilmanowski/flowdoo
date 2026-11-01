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
from mcp.server.mcpserver.exceptions import ToolError

from flowdoo_mcp import server
from flowdoo_mcp.config import get_settings
from flowdoo_mcp.server import mcp
from flowdoo_mcp.tools.traces import run_trace

ADDON_READY = {"enabled": True, "recorder_available": True, "is_admin": True}

Answers = dict[str, Any]


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
        "/flow_tracer/v1/status": ADDON_READY,
        "/json/2/ir.ui.view/search_count": neutralized,
        "/flow_tracer/v1/trace": trace,
    }


@pytest.fixture
def use_odoo(monkeypatch: pytest.MonkeyPatch) -> Callable[[Answers], list[str]]:
    """Answer the real client's requests from a table; returns the paths that were called."""
    monkeypatch.setenv("ODOO_URL", "http://odoo.test")
    monkeypatch.setenv("ODOO_DB", "dev")
    monkeypatch.setenv("ODOO_API_KEY", "key")
    get_settings.cache_clear()

    def install(answers: Answers) -> list[str]:
        seen: list[str] = []
        transport = httpx.MockTransport(fake_odoo(answers, seen))
        monkeypatch.setattr(
            server, "OdooJson2Client", partial(OdooJson2Client, transport=transport)
        )
        return seen

    return install


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
    }


@pytest.mark.anyio
async def test_run_trace_is_a_dry_run_and_returns_overview_and_filtered_steps(
    use_odoo: Callable[[Answers], list[str]],
) -> None:
    trace = load_fixture("trace-error")
    use_odoo(ready_odoo(trace))

    result = await run_trace("sale.order", "action_confirm", record_ids=[3], failed_only=True)

    assert result["trace_id"] == trace["trace_id"]
    assert result["dry_run"] is True
    assert [step["id"] for step in result["steps"]] == ["s1"]


@pytest.mark.anyio
async def test_run_trace_refuses_a_database_that_is_not_neutralised(
    use_odoo: Callable[[Answers], list[str]],
) -> None:
    seen = use_odoo(ready_odoo(load_fixture("trace-small"), neutralized=0))

    with pytest.raises(ToolError, match="neutralised"):
        await run_trace("sale.order", "action_confirm")

    assert "/flow_tracer/v1/trace" not in seen


@pytest.mark.anyio
async def test_run_trace_refuses_when_the_addon_is_switched_off(
    use_odoo: Callable[[Answers], list[str]],
) -> None:
    answers = ready_odoo(load_fixture("trace-small"))
    answers["/flow_tracer/v1/status"] = {**ADDON_READY, "enabled": False}
    seen = use_odoo(answers)

    with pytest.raises(ToolError, match="switched off"):
        await run_trace("sale.order", "action_confirm")

    assert "/flow_tracer/v1/trace" not in seen


@pytest.mark.anyio
async def test_run_trace_rejects_an_invalid_trace(
    use_odoo: Callable[[Answers], list[str]],
) -> None:
    use_odoo(ready_odoo({"steps": []}))

    with pytest.raises(ToolError, match="not a valid trace"):
        await run_trace("sale.order", "action_confirm")


@pytest.mark.anyio
async def test_odoo_errors_reach_the_model_through_the_protocol(
    use_odoo: Callable[[Answers], list[str]],
) -> None:
    use_odoo({})

    async with Client(mcp) as client:
        result = await client.call_tool("describe_model", {"model": "nope"})

    assert result.is_error
    assert "no route /flow_tracer/v1/model" in result.content[0].text


@pytest.mark.anyio
async def test_status_reports_problems_instead_of_failing(
    use_odoo: Callable[[Answers], list[str]],
) -> None:
    use_odoo({})

    async with Client(mcp) as client:
        result = await client.call_tool("odoo_status", {})

    status = json.loads(result.content[0].text)
    assert not result.is_error
    assert status["ok"] is False
    assert status["problems"]
