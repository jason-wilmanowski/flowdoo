import uuid
from typing import Annotated, Any, Literal

from flow_tracer_api.generated.trace_schema import TracePayload
from flow_tracer_api.integrations.odoo.errors import OdooClientError
from flow_tracer_api.schemas import TraceRequest
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field, ValidationError

from flowdoo_mcp import trace_view
from flowdoo_mcp.errors import odoo_errors_as_tool_errors
from flowdoo_mcp.server import MAX_STORED_TRACES, AppContext, ToolContext, mcp
from flowdoo_mcp.status import OdooStatus, check_status
from flowdoo_mcp.tools.odoo import entrypoint_signature

TRACE_ROUTE = "/flow_tracer_mcp/v1/trace"

StepKind = Literal[
    "method_call",
    "orm_create",
    "orm_write",
    "orm_unlink",
    "compute",
    "onchange",
    "constraint",
    "automation",
]


@mcp.tool()
async def run_trace(
    ctx: ToolContext,
    model: str,
    method: str,
    record_ids: list[int] | None = None,
    record_names: list[str] | None = None,
    kwargs: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run a public method in the real Odoo as a dry run, rolled back; returns an overview.

    Records by id or exact name, none for model-level methods. Sequences are not rolled back.
    """
    app = ctx.request_context.lifespan_context
    _ensure_traceable(await check_status(app.client, app.expected_login))
    ids = [*(record_ids or ()), *await _ids_of_names(app, model, record_names or [])]
    trace = await _record_and_keep(app, _request(model, method, ids, kwargs, context))
    return trace_view.overview(trace)


@mcp.tool()
async def compare_runs(
    ctx: ToolContext,
    model: str | None = None,
    method: str | None = None,
    record_a: str | int | None = None,
    record_b: str | int | None = None,
    kwargs: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    trace_a: str | None = None,
    trace_b: str | None = None,
) -> dict[str, Any]:
    """Why does a run differ from another? First different step, calls and values that differ.

    Give a method and two records (id or exact name), or two kept traces, e.g. from before and
    after a code change.
    """
    app = ctx.request_context.lifespan_context
    if trace_a and trace_b:
        return trace_view.compare_traces(_stored_trace(app, trace_a), _stored_trace(app, trace_b))
    if not model or not method or record_a is None or record_b is None:
        raise ToolError("Give model, method, record_a and record_b, or trace_a and trace_b")
    _ensure_traceable(await check_status(app.client, app.expected_login))
    ids = [await _id_of(app, model, record) for record in (record_a, record_b)]
    # The first run fills caches, and would show calls that only differ because of that.
    await _record(app, _request(model, method, [ids[0]], kwargs, context))
    first = await _record_and_keep(app, _request(model, method, [ids[0]], kwargs, context))
    second = await _record_and_keep(app, _request(model, method, [ids[1]], kwargs, context))
    return trace_view.compare_traces(first, second)


@mcp.tool()
async def explain_field(
    ctx: ToolContext,
    trace_id: str,
    field: str,
    model: str | None = None,
    record_id: int | None = None,
) -> dict[str, Any]:
    """Who changed a field in a kept trace: values, business method, call path, direct SQL."""
    trace = _stored_trace(ctx.request_context.lifespan_context, trace_id)
    return trace_view.explain_field(trace, field, model=model, record_id=record_id)


@mcp.tool()
async def find_steps(
    ctx: ToolContext,
    trace_id: str,
    step_id: str | None = None,
    model: str | None = None,
    method: str | None = None,
    module: str | None = None,
    kind: StepKind | None = None,
    field: str | None = None,
    record_id: int | None = None,
    under: str | None = None,
    exclude_modules: list[str] | None = None,
    failed_only: bool = False,
    limit: Annotated[int, Field(ge=1)] = 20,
    offset: Annotated[int, Field(ge=0)] = 0,
) -> dict[str, Any]:
    """Steps of a kept trace in order, exact filters; `step_id` gives one in full with its path.

    `under` keeps a step and all below it. `mro_position` counts implementations, 0 is most derived.
    """
    trace = _stored_trace(ctx.request_context.lifespan_context, trace_id)
    if step_id:
        detail = trace_view.step_detail(trace, step_id)
        if detail is None:
            raise ToolError(f"Trace {trace_id} has no step {step_id!r}")
        return detail
    return trace_view.find_steps(
        trace,
        model=model,
        method=method,
        module=module,
        kind=kind,
        field=field,
        record_id=record_id,
        under=under,
        exclude_modules=exclude_modules,
        failed_only=failed_only,
        limit=limit,
        offset=offset,
    )


def _request(
    model: str,
    method: str,
    ids: list[int],
    kwargs: dict[str, Any] | None,
    context: dict[str, Any] | None,
) -> TraceRequest:
    return TraceRequest(
        trace_id=uuid.uuid4(),
        model=model,
        method=method,
        record_ids=tuple(ids),
        context=context or {},
        call_kwargs=kwargs or {},
        dry_run=True,
    )


async def _record_and_keep(app: AppContext, request: TraceRequest) -> dict[str, Any]:
    trace = await _record(app, request)
    warnings = await _empty_recordset_warnings(app, request)
    if warnings:
        trace["warnings"] = warnings
    app.keep_trace(trace)
    return trace


def _ensure_traceable(status: OdooStatus) -> None:
    if not status.ok:
        raise ToolError("Odoo is not ready to trace: " + "; ".join(status.problems))
    if status.database_neutralized is not True:
        raise ToolError(
            "Refusing to trace: the database is not known to be neutralised (odoo neutralize), "
            "so mail servers, crons and payment providers would stay active"
        )


async def _record(app: AppContext, request: TraceRequest) -> dict[str, Any]:
    payload, writes = await _recorded_payload(app, request)
    try:
        TracePayload.model_validate(payload)
    except ValidationError as exc:
        raise ToolError(
            f"The recorder's answer is not a valid trace: {exc.error_count()} errors"
        ) from exc
    return {**payload, "raw_sql_writes": writes}


async def _recorded_payload(
    app: AppContext, request: TraceRequest
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """With the flow_tracer_mcp addon also the direct SQL writes, without it only the trace."""
    try:
        answer = await app.client.post(
            TRACE_ROUTE,
            {
                "trace_id": str(request.trace_id),
                "model": request.model,
                "method": request.method,
                "record_ids": list(request.record_ids),
                "context": dict(request.context),
                "kwargs": dict(request.call_kwargs),
            },
            timeout_seconds=app.timeout_seconds,
            target="flow_tracer_mcp trace",
        )
    except OdooClientError:
        with odoo_errors_as_tool_errors():
            result = await app.gateway.run_trace(request)
        return result.payload, []
    return answer["trace"], answer["raw_sql_writes"]


async def _id_of(app: AppContext, model: str, record: str | int) -> int:
    if isinstance(record, int):
        return record
    return (await _ids_of_names(app, model, [record]))[0]


async def _ids_of_names(app: AppContext, model: str, names: list[str]) -> list[int]:
    """Clients know orders by name, and looking up each id costs them a round."""
    ids = []
    for name in names:
        with odoo_errors_as_tool_errors():
            found = await app.client.call(model, "name_search", name=name, operator="=", limit=2)
        if len(found) != 1:
            raise ToolError(f"{len(found)} {model} records are named {name!r}, expected one")
        ids.append(found[0][0])
    return ids


async def _empty_recordset_warnings(app: AppContext, request: TraceRequest) -> list[str]:
    """Only a hint: if it cannot be checked, the recorded trace still counts."""
    if request.record_ids:
        return []
    try:
        signature = await entrypoint_signature(app.client, request.model, request.method)
    except OdooClientError:
        return []
    if signature.model_level:
        return []
    return [
        f"{request.model}.{request.method} works on records, but ran on an empty recordset "
        "because no record_ids were given, so most of its logic probably did not run"
    ]


def _stored_trace(app: AppContext, trace_id: str) -> dict[str, Any]:
    trace = app.traces.get(trace_id)
    if trace is None:
        raise ToolError(
            f"No trace {trace_id!r} in this session. Traces are lost when the server stops, and "
            f"only the latest {MAX_STORED_TRACES} are kept."
        )
    return trace
