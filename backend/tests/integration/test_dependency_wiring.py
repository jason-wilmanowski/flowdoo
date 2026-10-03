"""Endpoint -> get_trace_service(session) -> TraceService, wired through FastAPI DI."""

import uuid
from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from flow_tracer_api.api.app import create_app
from flow_tracer_api.api.dependencies import TraceServiceDep, get_odoo_gateway
from flow_tracer_api.core.config import Settings, get_settings
from flow_tracer_api.core.dependencies import get_session_factory
from flow_tracer_api.schemas import StartTraceCommand, TraceDetail
from flow_tracer_api.services import TraceNotFoundError
from tests.unit.fakes import FakeOdooGateway

pytestmark = pytest.mark.integration


@pytest.fixture
async def app(migrated_engine: AsyncEngine) -> AsyncIterator[FastAPI]:
    settings = Settings(database_url=SecretStr("postgresql+asyncpg://u:p@localhost:1/x"))
    app = create_app(settings)

    # Test-only routes: the real endpoints come later. They prove the DI chain.
    @app.post("/_probe/traces")
    async def start(command: StartTraceCommand, service: TraceServiceDep) -> TraceDetail:
        return await service.start_trace(command)

    @app.get("/_probe/traces/{trace_id}")
    async def get(trace_id: uuid.UUID, service: TraceServiceDep) -> TraceDetail:
        return await service.get_trace(trace_id)

    @app.delete("/_probe/traces/{trace_id}", status_code=204)
    async def delete(trace_id: uuid.UUID, service: TraceServiceDep) -> None:
        await service.delete_trace(trace_id)

    factory = async_sessionmaker(migrated_engine, expire_on_commit=False, class_=AsyncSession)
    app.dependency_overrides[get_session_factory] = lambda: factory
    app.dependency_overrides[get_odoo_gateway] = lambda: FakeOdooGateway()
    app.dependency_overrides[get_settings] = lambda: settings
    yield app

    # These requests commit for real; leave the shared test database empty.
    async with migrated_engine.begin() as conn:
        await conn.execute(text("TRUNCATE traces"))


async def test_endpoint_gets_service_with_request_session(app: FastAPI) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/_probe/traces",
            json={"entrypoint_model": "sale.order", "entrypoint_method": "action_confirm"},
        )
        assert created.status_code == 200
        trace_id = created.json()["id"]
        assert created.json()["status"] == "succeeded"

        # A new request (new session) sees the committed trace.
        fetched = await client.get(f"/_probe/traces/{trace_id}")
        assert fetched.status_code == 200
        assert fetched.json() == created.json()

        deleted = await client.delete(f"/_probe/traces/{trace_id}")
        assert deleted.status_code == 204
        with pytest.raises(TraceNotFoundError):
            await client.get(f"/_probe/traces/{trace_id}")


async def test_gateway_dependency_is_explicitly_not_implemented() -> None:
    settings = Settings(database_url=SecretStr("postgresql+asyncpg://u:p@localhost:1/x"))
    app = create_app(settings)

    @app.get("/_probe/gateway")
    async def probe(service: TraceServiceDep) -> None:  # pragma: no cover - never reached
        return None

    # Unbound factory: creating a session does not connect, the gateway fails first.
    app.dependency_overrides[get_session_factory] = lambda: async_sessionmaker()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/_probe/gateway")

    assert response.status_code == 501
