from typing import Any

from flow_tracer_api.schemas import EntrypointSignature, ModelDetail, OdooConnectionStatus

from flowdoo_mcp.errors import backend_errors_as_tool_errors
from flowdoo_mcp.server import ToolContext, mcp

MODEL_LIST_LIMIT = 100


@mcp.tool()
async def odoo_status(ctx: ToolContext) -> OdooConnectionStatus:
    """Check whether Flowdoo can reach the user's Odoo and is ready to trace.

    Call this first, before any other Flowdoo tool. `ok` is true only if everything works:
    Odoo reachable, version 19.0, API key valid, the flow_tracer addon installed and
    switched on, the recorder available and the key's user an administrator. `problems`
    says what blocks tracing, `warnings` what could not be verified or should be known
    (e.g. a database that is not neutralised, so mails and crons stay active).
    """
    return await ctx.request_context.lifespan_context.connection.check()


@mcp.tool()
async def describe_entrypoint(ctx: ToolContext, model: str, method: str) -> EntrypointSignature:
    """Show what a method expects, before tracing it.

    Returns its parameters (only keyword arguments can be passed), the module of the most
    derived implementation and whether it is a model-level method, called without record ids.
    """
    with backend_errors_as_tool_errors():
        return await ctx.request_context.lifespan_context.entrypoints.describe(model, method)


@mcp.tool()
async def list_models(ctx: ToolContext, search: str = "") -> dict[str, Any]:
    """Find models of the connected Odoo by a part of their technical name or description.

    Returns at most 100 models; `total` tells how many matched, so narrow `search` if it
    is higher.
    """
    with backend_errors_as_tool_errors():
        registry = await ctx.request_context.lifespan_context.registry.list_models()
    needle = search.casefold()
    matches = [
        {"model": item.model, "description": item.description, "module": item.module}
        for item in registry.models
        if needle in item.model.casefold() or needle in (item.description or "").casefold()
    ]
    return {"total": len(matches), "models": matches[:MODEL_LIST_LIMIT]}


@mcp.tool()
async def describe_model(ctx: ToolContext, model: str) -> ModelDetail:
    """Show the fields, relations and inheritance of one model."""
    with backend_errors_as_tool_errors():
        return await ctx.request_context.lifespan_context.registry.describe_model(model)
