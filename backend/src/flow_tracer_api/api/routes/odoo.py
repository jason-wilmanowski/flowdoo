"""Endpoints about the connection to the user's Odoo."""

from fastapi import APIRouter, HTTPException, status

from flow_tracer_api.api.dependencies import (
    EntrypointServiceDep,
    OdooConnectionServiceDep,
    RegistryServiceDep,
)
from flow_tracer_api.api.schemas import error_responses
from flow_tracer_api.schemas import (
    EntrypointSignature,
    ModelDetail,
    ModelList,
    OdooConnectionStatus,
)
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


@router.get(
    "/models",
    summary="List the models of the connected Odoo",
    description=(
        "Every model of the registry with the modules that define and extend it, the models "
        "it inherits from, delegations (`_inherits`) and its relational fields. Read from "
        "the running Odoo, not from source files."
    ),
    responses=error_responses(
        status.HTTP_403_FORBIDDEN,
        status.HTTP_502_BAD_GATEWAY,
        status.HTTP_503_SERVICE_UNAVAILABLE,
    ),
)
async def list_models(service: RegistryServiceDep) -> ModelList:
    try:
        return await service.list_models()
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get(
    "/models/{model}",
    summary="Describe one model and its fields",
    description=(
        "Inheritance of the model and every field: type, target model, required, stored, "
        "computed or related, and the module that defined it."
    ),
    responses=error_responses(
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_502_BAD_GATEWAY,
        status.HTTP_503_SERVICE_UNAVAILABLE,
    ),
)
async def describe_model(model: str, service: RegistryServiceDep) -> ModelDetail:
    try:
        return await service.describe_model(model)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
