"""Endpoints about the connection to the user's Odoo."""

from fastapi import APIRouter, HTTPException, status

from flow_tracer_api.api.dependencies import EntrypointServiceDep, OdooConnectionServiceDep
from flow_tracer_api.api.schemas import error_responses
from flow_tracer_api.schemas import EntrypointSignature, OdooConnectionStatus
from flow_tracer_api.services import ServiceError

router = APIRouter(prefix="/odoo", tags=["odoo"])


@router.get(
    "/status",
    summary="Check the connection to the configured Odoo",
    description=(
        "Checks, in order: configuration, reachability, Odoo 19.0, database and API key "
        "(optionally the expected login), and whether the flow_tracer addon is installed. "
        "Always answers 200; `ok` tells whether tracing can work, `problems` explains why "
        "not. Credentials are never part of the response."
    ),
)
async def odoo_status(service: OdooConnectionServiceDep) -> OdooConnectionStatus:
    try:
        return await service.check()
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get(
    "/entrypoints/{model}/{method}",
    summary="Describe a method before tracing it",
    description=(
        "Parameters of `model.method` as the flow_tracer addon sees them: which keyword "
        "arguments it takes, which are required, defaults, and whether it is a model-level "
        "method (call it without record ids)."
    ),
    responses=error_responses(
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_502_BAD_GATEWAY,
        status.HTTP_503_SERVICE_UNAVAILABLE,
    ),
)
async def describe_entrypoint(
    model: str, method: str, service: EntrypointServiceDep
) -> EntrypointSignature:
    try:
        return await service.describe(model, method)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
