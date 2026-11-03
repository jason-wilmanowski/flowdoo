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
from flowdoo_mcp.server import MAX_STORED_STEPS, MAX_STORED_TRACES, AppContext, mcp

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
        "run_trace",
        "compare_runs",
        "explain_field",
        "find_steps",
        "resolve_method",
        "describe_model",
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
        found = await call(client, "find_steps", trace_id=trace_id, failed_only=True)
        step = await call(client, "find_steps", trace_id=trace_id, step_id="s2")

    assert overview["trace_id"] == trace_id
    assert overview["failures"][0]["step"] == "s1"
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

    # The route of flow_tracer_mcp has no such parameter, it always runs dry.
    assert bodies[-1]["dry_run"] is True


@pytest.mark.anyio
async def test_traces_are_gone_with_the_session(use_odoo: UseOdoo) -> None:
    trace = load_fixture("trace-small")
    use_odoo(ready_odoo(trace))

    async with Client(mcp) as client:
        await call(client, "run_trace", model="sale.order", method="action_confirm")
    async with Client(mcp) as client:
        message = await error_of(client, "find_steps", trace_id=trace["trace_id"], step_id="s1")

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
async def test_an_invalid_trace_is_rejected_and_not_kept(use_odoo: UseOdoo) -> None:
    use_odoo(ready_odoo({"steps": []}))

    async with Client(mcp) as client:
        message = await error_of(client, "run_trace", model="sale.order", method="action_confirm")

    assert "not a valid trace" in message


@pytest.mark.anyio
async def test_unknown_trace_and_step_explain_themselves(use_odoo: UseOdoo) -> None:
    trace = load_fixture("trace-small")
    use_odoo(ready_odoo(trace))

    async with Client(mcp) as client:
        await call(client, "run_trace", model="sale.order", method="action_confirm")
        unknown_trace = await error_of(client, "find_steps", trace_id="nope", step_id="s1")
        unknown_step = await error_of(
            client, "find_steps", trace_id=trace["trace_id"], step_id="nope"
        )

    assert "No trace" in unknown_trace
    assert "no step" in unknown_step


@pytest.mark.anyio
@pytest.mark.parametrize("paging", [{"limit": 0}, {"limit": -1}, {"offset": -1}])
async def test_find_steps_refuses_paging_that_cannot_advance(
    use_odoo: UseOdoo, paging: dict[str, int]
) -> None:
    trace = load_fixture("trace-small")
    use_odoo(ready_odoo(trace))

    async with Client(mcp) as client:
        await call(client, "run_trace", model="sale.order", method="action_confirm")
        message = await error_of(client, "find_steps", trace_id=trace["trace_id"], **paging)

    assert next(iter(paging)) in message


def signature(*, model_level: bool) -> dict[str, Any]:
    return {
        "model": "sale.order",
        "method": "action_confirm",
        "model_level": model_level,
        "module": "sale",
        "summary": None,
        "parameters": [],
    }


@pytest.mark.anyio
async def test_run_trace_warns_about_a_record_method_without_records(use_odoo: UseOdoo) -> None:
    answers = ready_odoo(load_fixture("trace-small"))
    answers["/flow_tracer/v1/signature"] = signature(model_level=False)
    use_odoo(answers)

    async with Client(mcp) as client:
        overview = await call(client, "run_trace", model="sale.order", method="action_confirm")

    assert "empty recordset" in overview["warnings"][0]


@pytest.mark.anyio
async def test_run_trace_does_not_warn_about_a_model_level_method(use_odoo: UseOdoo) -> None:
    answers = ready_odoo(load_fixture("trace-small"))
    answers["/flow_tracer/v1/signature"] = signature(model_level=True)
    use_odoo(answers)

    async with Client(mcp) as client:
        overview = await call(client, "run_trace", model="res.partner", method="create")

    assert "warnings" not in overview


@pytest.mark.anyio
async def test_run_trace_with_records_does_not_ask_for_the_signature(use_odoo: UseOdoo) -> None:
    seen = use_odoo(ready_odoo(load_fixture("trace-small")))

    async with Client(mcp) as client:
        await call(client, "run_trace", model="sale.order", method="action_confirm", record_ids=[1])

    assert "/flow_tracer/v1/signature" not in seen


@pytest.mark.anyio
async def test_a_failing_signature_check_does_not_lose_the_trace(use_odoo: UseOdoo) -> None:
    use_odoo(ready_odoo(load_fixture("trace-small")))

    async with Client(mcp) as client:
        overview = await call(client, "run_trace", model="sale.order", method="action_confirm")

    assert "warnings" not in overview
    assert overview["step_count"] > 0


@pytest.mark.anyio
async def test_odoo_errors_reach_the_model(use_odoo: UseOdoo) -> None:
    use_odoo({})

    async with Client(mcp) as client:
        message = await error_of(client, "describe_model", model="nope")

    assert "no route /flow_tracer/v1/model" in message


def test_only_the_latest_traces_are_kept() -> None:
    app = AppContext(client=None, gateway=None)  # type: ignore[arg-type]

    for number in range(MAX_STORED_TRACES + 2):
        app.keep_trace({"trace_id": str(number)})

    assert len(app.traces) == MAX_STORED_TRACES
    assert "0" not in app.traces
    assert str(MAX_STORED_TRACES + 1) in app.traces


def test_a_few_huge_traces_are_dropped_before_the_count_limit() -> None:
    app = AppContext(client=None, gateway=None)  # type: ignore[arg-type]
    huge = [{}] * (MAX_STORED_STEPS // 2 + 1)

    for number in range(3):
        app.keep_trace({"trace_id": str(number), "steps": huge})

    assert list(app.traces) == ["2"]


def test_the_newest_trace_is_kept_even_if_it_is_over_the_limit() -> None:
    app = AppContext(client=None, gateway=None)  # type: ignore[arg-type]

    app.keep_trace({"trace_id": "big", "steps": [{}] * (MAX_STORED_STEPS + 1)})

    assert list(app.traces) == ["big"]


@pytest.mark.anyio
async def test_run_trace_finds_records_by_name(use_odoo: UseOdoo) -> None:
    trace = load_fixture("trace-small")
    answers = ready_odoo(trace)
    answers["/json/2/sale.order/name_search"] = [[7, "S00007"]]
    seen = use_odoo(answers)
    bodies: list[dict[str, Any]] = []
    original = OdooJson2Client.post

    async def spy(self: OdooJson2Client, path: str, payload: dict[str, Any], **kw: Any) -> Any:
        if path.endswith("/trace"):
            bodies.append(payload)
        return await original(self, path, payload, **kw)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(OdooJson2Client, "post", spy)
        async with Client(mcp) as client:
            await call(
                client,
                "run_trace",
                model="sale.order",
                method="action_confirm",
                record_names=["S00007"],
            )

    assert bodies[0]["record_ids"] == [7]
    assert "/flow_tracer/v1/signature" not in seen


@pytest.mark.anyio
@pytest.mark.parametrize("found", [[], [[1, "A"], [2, "A"]]])
async def test_run_trace_refuses_a_name_that_is_not_unique(
    use_odoo: UseOdoo, found: list[Any]
) -> None:
    answers = ready_odoo(load_fixture("trace-small"))
    answers["/json/2/sale.order/name_search"] = found
    use_odoo(answers)

    async with Client(mcp) as client:
        message = await error_of(
            client, "run_trace", model="sale.order", method="action_confirm", record_names=["A"]
        )

    assert "expected one" in message


@pytest.mark.anyio
async def test_explain_field_reads_a_kept_trace(use_odoo: UseOdoo) -> None:
    trace = load_fixture("trace-small")
    use_odoo(ready_odoo(trace))

    async with Client(mcp) as client:
        await call(client, "run_trace", model="sale.order", method="action_confirm", record_ids=[1])
        answer = await call(client, "explain_field", trace_id=trace["trace_id"], field="nope")

    assert answer["changes"] == []
    assert "direct SQL" in answer["hint"]


@pytest.mark.anyio
async def test_find_steps_refuses_an_unknown_kind(use_odoo: UseOdoo) -> None:
    trace = load_fixture("trace-small")
    use_odoo(ready_odoo(trace))

    async with Client(mcp) as client:
        await call(client, "run_trace", model="sale.order", method="action_confirm", record_ids=[1])
        message = await error_of(client, "find_steps", trace_id=trace["trace_id"], kind="nope")

    assert "kind" in message


def model_detail() -> dict[str, Any]:
    def field(name: str, *, module: str, stored: bool) -> dict[str, Any]:
        return {
            "name": name,
            "type": "char",
            "string": name.title(),
            "module": module,
            "target": None,
            "inverse": None,
            "required": False,
            "readonly": False,
            "stored": stored,
            "compute": None,
            "related": None,
            "selection": None,
        }

    return {
        "model": "sale.order",
        "description": "Order",
        "module": "sale",
        "modules": ["sale"],
        "abstract": False,
        "transient": False,
        "parents": [],
        "delegates": {},
        "fields": [
            field("state", module="sale", stored=True),
            field("note", module="sale", stored=False),
            field("incoterm", module="sale_stock", stored=True),
        ],
    }


@pytest.mark.anyio
async def test_describe_model_filters_and_leaves_out_empty_values(use_odoo: UseOdoo) -> None:
    use_odoo({"/flow_tracer/v1/model": model_detail()})

    async with Client(mcp) as client:
        everything = await call(client, "describe_model", model="sale.order")
        found = await call(client, "describe_model", model="sale.order", search="STAT")
        stored = await call(client, "describe_model", model="sale.order", stored_only=True)
        module = await call(client, "describe_model", model="sale.order", module="sale_stock")

    assert everything["fields_total"] == 3
    assert "abstract" not in everything
    assert "target" not in everything["fields"][0]
    assert [item["name"] for item in found["fields"]] == ["state"]
    assert [item["name"] for item in stored["fields"]] == ["state", "incoterm"]
    assert [item["name"] for item in module["fields"]] == ["incoterm"]


@pytest.mark.anyio
async def test_a_trace_includes_direct_sql_with_the_mcp_addon(use_odoo: UseOdoo) -> None:
    trace = load_fixture("trace-small")
    write = {
        "operation": "UPDATE",
        "table": "sale_order",
        "columns": ["credit_state"],
        "method": "_release_credit",
        "file": "sale_credit/models/sale_order.py",
        "line": 30,
    }
    answers = ready_odoo(trace)
    answers["/flow_tracer_mcp/v1/trace"] = {"trace": trace, "raw_sql_writes": [write]}
    use_odoo(answers)

    async with Client(mcp) as client:
        overview = await call(
            client, "run_trace", model="sale.order", method="action_confirm", record_ids=[1]
        )
        field = await call(
            client, "explain_field", trace_id=trace["trace_id"], field="credit_state"
        )

    assert "UPDATE sale_order credit_state by _release_credit" in overview["raw_sql_writes"][0]
    assert "_release_credit" in field["raw_sql_writes"][0]
    assert "hint" not in field


@pytest.mark.anyio
async def test_compare_runs_warms_up_and_compares_two_records(use_odoo: UseOdoo) -> None:
    trace = load_fixture("trace-small")
    seen = use_odoo(ready_odoo(trace))

    async with Client(mcp) as client:
        answer = await call(
            client,
            "compare_runs",
            model="sale.order",
            method="action_confirm",
            record_a=1,
            record_b=2,
        )

    assert answer["same_steps"] is True
    assert seen.count("/flow_tracer/v1/trace") == 3


@pytest.mark.anyio
async def test_compare_runs_needs_a_complete_request(use_odoo: UseOdoo) -> None:
    use_odoo({})

    async with Client(mcp) as client:
        message = await error_of(client, "compare_runs", model="sale.order")

    assert "record_a" in message


@pytest.mark.anyio
async def test_resolve_method_and_field_answer_from_the_addon(use_odoo: UseOdoo) -> None:
    method = {
        "implementations": [{"position": 0, "module": "sale", "file": "sale/x.py", "line": 3}]
    }
    field = {"compute": "_c", "depends_on": ["a"], "recomputes": ["m.b"]}
    use_odoo({"/flow_tracer_mcp/v1/method": method, "/flow_tracer_mcp/v1/field": field})

    async with Client(mcp) as client:
        resolved = await call(client, "resolve_method", model="sale.order", method="write")
        graph = await call(client, "describe_model", model="sale.order", field="state")

    assert resolved["implementations"][0]["file"] == "sale/x.py"
    assert graph["recomputes"] == ["m.b"]
