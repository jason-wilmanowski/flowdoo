"""Dependency injection wiring: request-scoped resources -> services.

Endpoints declare ``service: TraceServiceDep``; FastAPI builds the request-scoped
``AsyncSession`` (``core.dependencies.get_session``) and hands it to ``TraceService``,
which creates its repository on that session. ``OdooConnectionServiceDep`` works the same
way with a request-scoped Odoo client that is closed after the response.
"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from flow_tracer_api.core.config import Settings, get_settings
from flow_tracer_api.core.dependencies import SessionDep
from flow_tracer_api.integrations.odoo import FlowTracerGateway, OdooJson2Client
from flow_tracer_api.services import TraceService
from flow_tracer_api.services.odoo_connection_service import OdooConnectionService
from flow_tracer_api.services.payload_validation import SchemaPayloadValidator
from flow_tracer_api.services.ports import OdooGateway, TracePayloadValidator

SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_odoo_client(settings: SettingsDep) -> AsyncIterator[OdooJson2Client | None]:
    """JSON-2 client for the configured Odoo, or ``None`` if it is not configured.

    One client per request; closed after the response.
    """
    if settings.odoo_url is None or not settings.odoo_db or settings.odoo_api_key is None:
        yield None
        return
    async with OdooJson2Client(
        base_url=str(settings.odoo_url),
        database=settings.odoo_db,
        api_key=settings.odoo_api_key.get_secret_value(),
        timeout_seconds=settings.odoo_timeout_seconds,
    ) as client:
        yield client


OdooClientDep = Annotated[OdooJson2Client | None, Depends(get_odoo_client)]


def get_odoo_gateway(client: OdooClientDep, settings: SettingsDep) -> OdooGateway | None:
    """``None`` = no Odoo connection configured; ``POST /traces`` then answers 503."""
    if client is None:
        return None
    return FlowTracerGateway(client, timeout_seconds=settings.odoo_trace_timeout_seconds)


def get_payload_validator() -> TracePayloadValidator:
    return SchemaPayloadValidator()


def get_trace_service(
    session: SessionDep,
    gateway: Annotated[OdooGateway | None, Depends(get_odoo_gateway)],
    validator: Annotated[TracePayloadValidator, Depends(get_payload_validator)],
    settings: SettingsDep,
) -> TraceService:
    return TraceService(
        session,
        gateway,
        validator,
        allow_non_dry_run=settings.allow_non_dry_run,
    )


TraceServiceDep = Annotated[TraceService, Depends(get_trace_service)]


def get_odoo_connection_service(
    client: OdooClientDep, settings: SettingsDep
) -> OdooConnectionService:
    return OdooConnectionService(
        client,
        url=str(settings.odoo_url) if settings.odoo_url else None,
        database=settings.odoo_db,
        expected_login=settings.odoo_login,
    )


OdooConnectionServiceDep = Annotated[OdooConnectionService, Depends(get_odoo_connection_service)]
