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
    """Run a method in the real Odoo as a dry run, always rolled back; returns an overview.

    Give the records as `record_ids` or by exact `record_names`, none for model-level methods.
    Private methods cannot be started. `kwargs` are keyword arguments as JSON values. A failing
    run is a valid result, see `error` and `failures`. Sequences are not rolled back. Use
    explain_field, find_steps and get_step with the returned `trace_id` to go deeper.
    """
    app = ctx.request_context.lifespan_context
    _ensure_traceable(await check_status(app.client, app.expected_login))
    ids = [*(record_ids or ()), *await _ids_of_names(app, model, record_names or [])]
    request = TraceRequest(
        trace_id=uuid.uuid4(),
        model=model,
        method=method,
        record_ids=tuple(ids),
        context=context or {},
        call_kwargs=kwargs or {},
        dry_run=True,
    )
    trace = await _record(app, request)
    trace["warnings"] = await _empty_recordset_warnings(app, request)
    app.keep_trace(trace)
    return trace_view.overview(trace)


@mcp.tool()
async def explain_field(
    ctx: ToolContext,
    trace_id: str,
    field: str,
    model: str | None = None,
    record_id: int | None = None,
) -> dict[str, Any]:
    """Who changed a field in a kept trace: values, the business method behind it, call path.

    The fastest way to find where a value comes from. Direct SQL writes are not recorded.
    """
    trace = _stored_trace(ctx.request_context.lifespan_context, trace_id)
    return trace_view.explain_field(trace, field, model=model, record_id=record_id)


@mcp.tool()
async def list_traces(ctx: ToolContext) -> dict[str, Any]:
    """List the traces kept in this session, oldest first."""
    traces = ctx.request_context.lifespan_context.traces
    return {"traces": [trace_view.summary(trace) for trace in traces.values()]}


@mcp.tool()
async def trace_overview(ctx: ToolContext, trace_id: str) -> dict[str, Any]:
    """Show a kept trace's overview again, as run_trace returned it."""
    return trace_view.overview(_stored_trace(ctx.request_context.lifespan_context, trace_id))


@mcp.tool()
async def find_steps(
    ctx: ToolContext,
    trace_id: str,
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
    """Find steps of a kept trace in execution order; all filters must match exactly.

    `under` keeps a step and everything below it. `mro_position` counts the implementations of
    that method on the server, 0 is the most derived. If `next_offset` is set, narrow the
    filters or call again with it as `offset`.
    """
    return trace_view.find_steps(
        _stored_trace(ctx.request_context.lifespan_context, trace_id),
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


@mcp.tool()
async def get_step(ctx: ToolContext, trace_id: str, step_id: str) -> dict[str, Any]:
    """One step of a kept trace in full, its call path, children and the overrides that ran."""
    trace = _stored_trace(ctx.request_context.lifespan_context, trace_id)
    detail = trace_view.step_detail(trace, step_id)
    if detail is None:
        raise ToolError(f"Trace {trace_id} has no step {step_id!r}")
    return detail


def _ensure_traceable(status: OdooStatus) -> None:
    if not status.ok:
        raise ToolError("Odoo is not ready to trace: " + "; ".join(status.problems))
    if status.database_neutralized is not True:
        raise ToolError(
            "Refusing to trace: the database is not known to be neutralised (odoo neutralize), "
            "so mail servers, crons and payment providers would stay active"
        )


async def _record(app: AppContext, request: TraceRequest) -> dict[str, Any]:
    with odoo_errors_as_tool_errors():
        result = await app.gateway.run_trace(request)
    try:
        TracePayload.model_validate(result.payload)
    except ValidationError as exc:
        raise ToolError(
            f"The recorder's answer is not a valid trace: {exc.error_count()} errors"
        ) from exc
    return result.payload


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
            f"No trace {trace_id!r} in this session; use list_traces. Traces are lost when the "
            f"server stops, and only the latest {MAX_STORED_TRACES} are kept."
        )
    return trace
