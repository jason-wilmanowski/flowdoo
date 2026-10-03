"""Endpoints about the connection to the user's Odoo."""

from fastapi import APIRouter, HTTPException

from flow_tracer_api.api.dependencies import OdooConnectionServiceDep
from flow_tracer_api.schemas import OdooConnectionStatus
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
