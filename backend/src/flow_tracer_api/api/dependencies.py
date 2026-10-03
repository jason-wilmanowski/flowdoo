"""Dependency injection wiring: request session -> service.

Endpoints declare ``service: TraceServiceDep``; FastAPI builds the request-scoped
``AsyncSession`` (``core.dependencies.get_session``) and hands it to ``TraceService``,
which creates its repository on that session.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status

from flow_tracer_api.core.config import Settings, get_settings
from flow_tracer_api.core.dependencies import SessionDep
from flow_tracer_api.services import TraceService
from flow_tracer_api.services.ports import (
    OdooGateway,
    OpaquePayloadValidator,
    TracePayloadValidator,
)


def get_odoo_gateway() -> OdooGateway:
    # TODO(odoo-gateway): return the JSON-RPC implementation once it exists.
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Odoo gateway is not implemented yet",
    )


def get_payload_validator() -> TracePayloadValidator:
    # TODO(trace-schema): switch to the validator generated from the trace schema.
    return OpaquePayloadValidator()


def get_trace_service(
    session: SessionDep,
    gateway: Annotated[OdooGateway, Depends(get_odoo_gateway)],
    validator: Annotated[TracePayloadValidator, Depends(get_payload_validator)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TraceService:
    return TraceService(
        session,
        gateway,
        validator,
        allow_non_dry_run=settings.allow_non_dry_run,
    )


TraceServiceDep = Annotated[TraceService, Depends(get_trace_service)]
