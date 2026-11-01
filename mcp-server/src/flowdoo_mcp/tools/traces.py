import uuid
from typing import Any

from flow_tracer_api.integrations.odoo.errors import OdooClientError
from flow_tracer_api.schemas import OdooConnectionStatus, TraceRequest
from flow_tracer_api.services.common.ports import PayloadValidationError
from mcp.server.mcpserver.exceptions import ToolError

from flowdoo_mcp import trace_view
from flowdoo_mcp.server import AppContext, ToolContext, mcp


@mcp.tool()
async def run_trace(
    ctx: ToolContext,
    model: str,
    method: str,
    record_ids: list[int] | None = None,
    kwargs: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run a method in the real Odoo as a dry run, record it and return an overview.

    Always rolled back at the end. Refuses a database that is not ready to trace or not
    neutralised. Leave `record_ids` empty for model-level methods; `kwargs` are the
    method's keyword arguments as JSON values. A failing workflow is a valid result: see
    `error` and `failed_steps`. If the call times out, the run may still finish in Odoo.
    """
    app = ctx.request_context.lifespan_context
    _ensure_traceable(await app.connection.check())
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
    app.traces[trace["trace_id"]] = trace
    return trace_view.overview(trace)


@mcp.tool()
async def list_traces(ctx: ToolContext) -> list[dict[str, Any]]:
    """List the traces recorded since this server started, oldest first."""
    traces = ctx.request_context.lifespan_context.traces
    return [trace_view.summary(trace) for trace in traces.values()]


@mcp.tool()
async def trace_overview(ctx: ToolContext, trace_id: str) -> dict[str, Any]:
    """Summarise a trace: step counts, models and modules involved, changed fields, errors."""
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
) -> dict[str, Any]:
    """Find steps of a trace, in execution order. All given filters must match exactly.

    `field` matches steps that changed a field of that name, `kind` is e.g. method_call,
    orm_write or compute. `total` tells how many matched; narrow the filters if it is
    above `limit`. Use get_step for the details of a step.
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
    )


@mcp.tool()
async def get_step(ctx: ToolContext, trace_id: str, step_id: str) -> dict[str, Any]:
    """Show one step in full: field changes, MRO position, super() call, error.

    Also returns the call path leading to it and its direct children, to walk the tree.
    """
    trace = _stored_trace(ctx.request_context.lifespan_context, trace_id)
    detail = trace_view.step_detail(trace, step_id)
    if detail is None:
        raise ToolError(f"Trace {trace_id} has no step {step_id!r}")
    return detail


def _ensure_traceable(status: OdooConnectionStatus) -> None:
    if not status.ok:
        raise ToolError("Odoo is not ready to trace: " + "; ".join(status.problems))
    if status.database_neutralized is not True:
        raise ToolError(
            "Refusing to trace: the database is not known to be neutralised (odoo neutralize), "
            "so mail servers, crons and payment providers would stay active"
        )


async def _record(app: AppContext, request: TraceRequest) -> dict[str, Any]:
    try:
        result = await app.gateway.run_trace(request)
        return app.validator.validate(result.payload).payload
    except OdooClientError as exc:
        raise ToolError(exc.message) from exc
    except PayloadValidationError as exc:
        raise ToolError(f"The recorder's answer is not a valid trace: {exc}") from exc


def _stored_trace(app: AppContext, trace_id: str) -> dict[str, Any]:
    trace = app.traces.get(trace_id)
    if trace is None:
        raise ToolError(
            f"No trace {trace_id!r} on this server; use list_traces. "
            "Traces are lost when the server stops."
        )
    return trace
