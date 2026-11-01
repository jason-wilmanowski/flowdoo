from typing import Any

from flow_tracer_api.schemas import EntrypointSignature, ModelDetail, ModelList

from flowdoo_mcp.server import mcp, odoo_client
from flowdoo_mcp.status import OdooStatus, check_status

SIGNATURE_ROUTE = "/flow_tracer/v1/signature"
MODELS_ROUTE = "/flow_tracer/v1/models"
MODEL_ROUTE = "/flow_tracer/v1/model"
MODEL_LIST_LIMIT = 100


@mcp.tool()
async def odoo_status() -> OdooStatus:
    """Check whether Flowdoo can reach the user's Odoo and is ready to trace.

    Call this first, before any other Flowdoo tool. `ok` is true only if everything works:
    Odoo reachable, version 19.0, API key valid, the flow_tracer addon installed and
    switched on, the recorder available and the key's user an administrator. `problems`
    says what blocks tracing, `warnings` what could not be verified or should be known
    (e.g. a database that is not neutralised, which run_trace refuses).
    """
    async with odoo_client() as client:
        return await check_status(client)


@mcp.tool()
async def describe_entrypoint(model: str, method: str) -> EntrypointSignature:
    """Show what a method expects, before tracing it.

    Returns its parameters (only keyword arguments can be passed), the module of the most
    derived implementation and whether it is a model-level method, called without record ids.
    """
    async with odoo_client() as client:
        answer = await client.post(
            SIGNATURE_ROUTE,
            {"model": model, "method": method},
            target=f"{model}.{method} signature",
        )
    return EntrypointSignature.model_validate(answer)


@mcp.tool()
async def list_models(search: str = "") -> dict[str, Any]:
    """Find models of the connected Odoo by a part of their technical name or description.

    Returns at most 100 models; `total` tells how many matched, so narrow `search` if it
    is higher.
    """
    async with odoo_client() as client:
        answer = await client.post(MODELS_ROUTE, {}, target="model registry")
    needle = search.casefold()
    matches = [
        {"model": item.model, "description": item.description, "module": item.module}
        for item in ModelList.model_validate(answer).models
        if needle in item.model.casefold() or needle in (item.description or "").casefold()
    ]
    return {"total": len(matches), "models": matches[:MODEL_LIST_LIMIT]}


@mcp.tool()
async def describe_model(model: str) -> ModelDetail:
    """Show the fields, relations and inheritance of one model."""
    async with odoo_client() as client:
        answer = await client.post(MODEL_ROUTE, {"model": model}, target=f"{model} model")
    return ModelDetail.model_validate(answer)
