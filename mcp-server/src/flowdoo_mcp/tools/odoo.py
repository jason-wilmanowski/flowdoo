from typing import Annotated, Any

from flow_tracer_api.integrations.odoo.client import OdooJson2Client
from flow_tracer_api.schemas import EntrypointSignature, ModelDetail, ModelList
from pydantic import Field

from flowdoo_mcp.errors import odoo_errors_as_tool_errors
from flowdoo_mcp.server import ToolContext, mcp
from flowdoo_mcp.status import OdooStatus, check_status

SIGNATURE_ROUTE = "/flow_tracer/v1/signature"
MODELS_ROUTE = "/flow_tracer/v1/models"
MODEL_ROUTE = "/flow_tracer/v1/model"
MODEL_LIST_LIMIT = 100


@mcp.tool()
async def odoo_status(ctx: ToolContext) -> OdooStatus:
    """Check whether Flowdoo can reach the user's Odoo and is ready to trace.

    Call this first, before any other Flowdoo tool. `ok` is true only if everything works:
    Odoo reachable, version 19.0, API key valid, the flow_tracer addon installed and
    switched on, the recorder available and the key's user an administrator. `problems`
    says what blocks tracing, `warnings` what could not be verified or should be known
    (e.g. a database that is not neutralised, which run_trace refuses).
    """
    app = ctx.request_context.lifespan_context
    return await check_status(app.client, app.expected_login)


@mcp.tool()
async def describe_entrypoint(ctx: ToolContext, model: str, method: str) -> EntrypointSignature:
    """Show what a method expects, before tracing it.

    Returns its parameters (only keyword arguments can be passed), the module of the most
    derived implementation and whether it is a model-level method, called without record ids.
    """
    with odoo_errors_as_tool_errors():
        return await entrypoint_signature(
            ctx.request_context.lifespan_context.client, model, method
        )


async def entrypoint_signature(
    client: OdooJson2Client, model: str, method: str
) -> EntrypointSignature:
    answer = await client.post(
        SIGNATURE_ROUTE,
        {"model": model, "method": method},
        target=f"{model}.{method} signature",
    )
    return EntrypointSignature.model_validate(answer)


@mcp.tool()
async def list_models(
    ctx: ToolContext, search: str = "", offset: Annotated[int, Field(ge=0)] = 0
) -> dict[str, Any]:
    """Find models of the connected Odoo by a part of their technical name or description.

    Returns at most 100 models per call; `total` tells how many matched. If `next_offset`
    is set, call again with it as `offset` or narrow `search`.
    """
    with odoo_errors_as_tool_errors():
        answer = await ctx.request_context.lifespan_context.client.post(
            MODELS_ROUTE, {}, target="model registry"
        )
    needle = search.casefold()
    matches = [
        {"model": item.model, "description": item.description, "module": item.module}
        for item in ModelList.model_validate(answer).models
        if needle in item.model.casefold() or needle in (item.description or "").casefold()
    ]
    next_offset = offset + MODEL_LIST_LIMIT
    return {
        "total": len(matches),
        "offset": offset,
        "next_offset": next_offset if next_offset < len(matches) else None,
        "models": matches[offset:next_offset],
    }


@mcp.tool()
async def describe_model(ctx: ToolContext, model: str) -> ModelDetail:
    """Show the fields, relations and inheritance of one model."""
    with odoo_errors_as_tool_errors():
        answer = await ctx.request_context.lifespan_context.client.post(
            MODEL_ROUTE, {"model": model}, target=f"{model} model"
        )
    return ModelDetail.model_validate(answer)
