import uuid
from typing import Any

from flow_tracer_api.generated.trace_schema import TracePayload
from flow_tracer_api.schemas import TraceRequest
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import ValidationError

from flowdoo_mcp import trace_view
from flowdoo_mcp.errors import odoo_errors_as_tool_errors
from flowdoo_mcp.server import MAX_STORED_TRACES, AppContext, ToolContext, mcp
from flowdoo_mcp.status import OdooStatus, check_status


@mcp.tool()
async def run_trace(
    ctx: ToolContext,
    model: str,
    method: str,
    record_ids: list[int] | None = None,
    kwargs: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run a method in the real Odoo as a dry run, keep the trace and return its overview.

    Always rolled back at the end. Refuses a database that is not ready to trace or not
    neutralised. Leave `record_ids` empty for model-level methods; `kwargs` are the
    method's keyword arguments as JSON values. A failing workflow is a valid result: see
    `error` and `failures`. If the call times out, the run may still finish in Odoo.

    The overview lists counts per kind, model and module, every changed field with its
    values, the top-level calls and where failures start. Use find_steps and get_step with
    the returned `trace_id` to go deeper.
    """
    app = ctx.request_context.lifespan_context
    _ensure_traceable(await check_status(app.client, app.expected_login))
    request = TraceRequest(
        trace_id=uuid.uuid4(),
        model=model,
        method=method,
        record_ids=tuple(record_ids or ()),
        context=context or {},
        call_kwargs=kwargs or {},
        dry_run=True,
    )
    trace = await _record(app, request)
    app.keep_trace(trace)
    return trace_view.overview(trace)


@mcp.tool()
async def list_traces(ctx: ToolContext) -> list[dict[str, Any]]:
    """List the traces kept in this session, oldest first."""
    traces = ctx.request_context.lifespan_context.traces
    return [trace_view.summary(trace) for trace in traces.values()]


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
    kind: str | None = None,
    field: str | None = None,
    failed_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Find steps of a kept trace, in execution order. All given filters must match exactly.

    `field` matches steps that changed a field of that name, `kind` is e.g. method_call,
    orm_write or compute. Each step shows its call, module, MRO position, super() call,
    shortened arguments and result, field changes and error. `total` tells how many matched;
    if `next_offset` is set, call again with it as `offset` or narrow the filters. Use
    get_step for everything about one step.
    """
    return trace_view.find_steps(
        _stored_trace(ctx.request_context.lifespan_context, trace_id),
        model=model,
        method=method,
        module=module,
        kind=kind,
        field=field,
        failed_only=failed_only,
        limit=limit,
        offset=offset,
    )


@mcp.tool()
async def get_step(ctx: ToolContext, trace_id: str, step_id: str) -> dict[str, Any]:
    """Show one step of a kept trace in full: all field changes, arguments, result, error.

    Also returns the call path leading to it, its direct children to walk the tree, and the
    implementations of the same method that ran in this trace with their MRO position and
    super() call, which show where a hook is possible.
    """
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


def _stored_trace(app: AppContext, trace_id: str) -> dict[str, Any]:
    trace = app.traces.get(trace_id)
    if trace is None:
        raise ToolError(
            f"No trace {trace_id!r} in this session; use list_traces. Traces are lost when the "
            f"server stops, and only the latest {MAX_STORED_TRACES} are kept."
        )
    return trace
