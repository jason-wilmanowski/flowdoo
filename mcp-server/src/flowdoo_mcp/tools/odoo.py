from typing import Annotated, Any

from flow_tracer_api.integrations.odoo.client import OdooJson2Client
from flow_tracer_api.schemas import EntrypointSignature, ModelDetail, ModelList
from pydantic import Field

from flowdoo_mcp import trace_view
from flowdoo_mcp.errors import odoo_errors_as_tool_errors
from flowdoo_mcp.server import ToolContext, mcp
from flowdoo_mcp.status import OdooStatus, check_status

SIGNATURE_ROUTE = "/flow_tracer/v1/signature"
MODELS_ROUTE = "/flow_tracer/v1/models"
MODEL_ROUTE = "/flow_tracer/v1/model"
MODEL_LIST_LIMIT = 100


@mcp.tool()
async def odoo_status(ctx: ToolContext) -> OdooStatus:
    """Is Odoo reachable and ready to trace? `problems` says what blocks it."""
    app = ctx.request_context.lifespan_context
    return await check_status(app.client, app.expected_login)


@mcp.tool()
async def describe_entrypoint(ctx: ToolContext, model: str, method: str) -> EntrypointSignature:
    """What a method expects: parameters, most derived module, whether it is model-level."""
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
    """Find models by a part of their name or description; at most 100 per call."""
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
async def describe_model(
    ctx: ToolContext,
    model: str,
    search: str = "",
    module: str | None = None,
    stored_only: bool = False,
) -> dict[str, Any]:
    """Inheritance of a model and its fields, filtered by name or label, module or stored.

    Large models have hundreds of fields, so filter if you can; `fields_total` tells the rest.
    """
    with odoo_errors_as_tool_errors():
        answer = await ctx.request_context.lifespan_context.client.post(
            MODEL_ROUTE, {"model": model}, target=f"{model} model"
        )
    return _compact_model(ModelDetail.model_validate(answer), search, module, stored_only)


def _compact_model(
    detail: ModelDetail, search: str, module: str | None, stored_only: bool
) -> dict[str, Any]:
    """Most field attributes are empty, and they make up most of the answer."""
    needle = search.casefold()
    fields = [
        {key: value for key, value in field.model_dump().items() if value}
        for field in detail.fields
        if (needle in field.name.casefold() or needle in (field.string or "").casefold())
        and (module is None or field.module == module)
        and (not stored_only or field.stored)
    ]
    shown = trace_view.fitting(fields)
    head = detail.model_dump(exclude={"fields"})
    return {
        **{key: value for key, value in head.items() if value},
        "fields_total": len(fields),
        "fields": shown,
    }
