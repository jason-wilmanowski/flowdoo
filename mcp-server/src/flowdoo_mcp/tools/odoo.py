from typing import Any

from flow_tracer_api.integrations.odoo.client import OdooJson2Client
from flow_tracer_api.schemas import EntrypointSignature, ModelDetail

from flowdoo_mcp import trace_view
from flowdoo_mcp.errors import odoo_errors_as_tool_errors
from flowdoo_mcp.server import ToolContext, mcp

SIGNATURE_ROUTE = "/flow_tracer/v1/signature"
MODEL_ROUTE = "/flow_tracer/v1/model"
METHOD_ROUTE = "/flow_tracer_mcp/v1/method"
FIELD_ROUTE = "/flow_tracer_mcp/v1/field"


@mcp.tool()
async def resolve_method(ctx: ToolContext, model: str, method: str) -> dict[str, Any]:
    """Every active override of a method without running it: order, module, file, line, super()."""
    with odoo_errors_as_tool_errors():
        return dict(
            await ctx.request_context.lifespan_context.client.post(
                METHOD_ROUTE, {"model": model, "method": method}, target=f"{model}.{method}"
            )
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
async def describe_model(
    ctx: ToolContext,
    model: str,
    search: str = "",
    module: str | None = None,
    stored_only: bool = False,
    field: str | None = None,
) -> dict[str, Any]:
    """Fields and inheritance of a model; filter them. `field` tells how one field gets its value.

    With `field`: compute method, what it depends on and which stored fields it recomputes.
    """
    client = ctx.request_context.lifespan_context.client
    with odoo_errors_as_tool_errors():
        if field:
            return dict(
                await client.post(
                    FIELD_ROUTE, {"model": model, "field": field}, target=f"{model}.{field}"
                )
            )
        answer = await client.post(MODEL_ROUTE, {"model": model}, target=f"{model} model")
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
