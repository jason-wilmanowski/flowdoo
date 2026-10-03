"""Dependency injection wiring: request session -> service.

Endpoints declare ``service: TraceServiceDep``; FastAPI builds the request-scoped
``AsyncSession`` (``core.dependencies.get_session``) and hands it to ``TraceService``,
which creates its repository on that session.
"""

from typing import Annotated

from fastapi import Depends

from flow_tracer_api.core.config import Settings, get_settings
from flow_tracer_api.core.dependencies import SessionDep
from flow_tracer_api.services import TraceService
from flow_tracer_api.services.ports import (
    OdooGateway,
    OpaquePayloadValidator,
    TracePayloadValidator,
)


def get_odoo_gateway() -> OdooGateway | None:
    """``None`` = no Odoo connection; ``POST /traces`` then answers 503."""
    # TODO(odoo-gateway): return the JSON-RPC implementation once it exists.
    return None


def get_payload_validator() -> TracePayloadValidator:
    # TODO(trace-schema): switch to the validator generated from the trace schema.
    return OpaquePayloadValidator()


def get_trace_service(
    session: SessionDep,
    gateway: Annotated[OdooGateway | None, Depends(get_odoo_gateway)],
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
