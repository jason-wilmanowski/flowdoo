import uuid
from typing import Any

from flow_tracer_api.generated.trace_schema import TracePayload
from flow_tracer_api.integrations.odoo.client import OdooJson2Client
from flow_tracer_api.integrations.odoo.gateway import FlowTracerGateway
from flow_tracer_api.schemas import TraceRequest
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import ValidationError

from flowdoo_mcp import trace_view
from flowdoo_mcp.config import get_settings
from flowdoo_mcp.server import mcp, odoo_client
from flowdoo_mcp.status import OdooStatus, check_status


@mcp.tool()
async def run_trace(
    model: str,
    method: str,
    record_ids: list[int] | None = None,
    kwargs: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    step_model: str | None = None,
    step_method: str | None = None,
    step_module: str | None = None,
    step_kind: str | None = None,
    step_field: str | None = None,
    failed_only: bool = False,
    step_limit: int = 20,
) -> dict[str, Any]:
    """Run a method in the real Odoo as a dry run and return an overview of what happened.

    Always rolled back at the end. Refuses a database that is not ready to trace or not
    neutralised. Leave `record_ids` empty for model-level methods; `kwargs` are the
    method's keyword arguments as JSON values. A failing workflow is a valid result: see
    `error` and `failed_steps`. If the call times out, the run may still finish in Odoo.

    Nothing is kept: to see steps, pass the `step_*` filters or `failed_only`, which must
    all match exactly. `step_field` matches steps that changed a field of that name,
    `step_kind` is e.g. method_call, orm_write or compute. Asking again runs it again, and
    step ids can differ between runs. `steps_total` tells how many matched; narrow the
    filters if it is above `step_limit`.
    """
    request = TraceRequest(
        trace_id=uuid.uuid4(),
        model=model,
        method=method,
        record_ids=tuple(record_ids or ()),
        context=context or {},
        call_kwargs=kwargs or {},
        dry_run=True,
    )
    async with odoo_client() as client:
        _ensure_traceable(await check_status(client))
        trace = await _record(client, request)
    return {
        **trace_view.overview(trace),
        **trace_view.find_steps(
            trace,
            model=step_model,
            method=step_method,
            module=step_module,
            kind=step_kind,
            field=step_field,
            failed_only=failed_only,
            limit=step_limit,
        ),
    }


def _ensure_traceable(status: OdooStatus) -> None:
    if not status.ok:
        raise ToolError("Odoo is not ready to trace: " + "; ".join(status.problems))
    if status.database_neutralized is not True:
        raise ToolError(
            "Refusing to trace: the database is not known to be neutralised (odoo neutralize), "
            "so mail servers, crons and payment providers would stay active"
        )


async def _record(client: OdooJson2Client, request: TraceRequest) -> dict[str, Any]:
    gateway = FlowTracerGateway(client=client, timeout_seconds=get_settings().flowdoo_timeout)
    result = await gateway.run_trace(request)
    try:
        TracePayload.model_validate(result.payload)
    except ValidationError as exc:
        raise ToolError(
            f"The recorder's answer is not a valid trace: {exc.error_count()} errors"
        ) from exc
    return result.payload
