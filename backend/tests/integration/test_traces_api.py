"""/traces endpoints end to end: HTTP -> Depends(session) -> TraceService -> Postgres.

Each request gets its own session from the overridden session factory, exactly like in
production. Requests commit for real, so the table is truncated after every test.
"""

import uuid
from collections.abc import AsyncIterator, Callable

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from flow_tracer_api.api.dependencies import get_odoo_gateway
from flow_tracer_api.core.config import Settings, get_settings
from flow_tracer_api.core.dependencies import get_session_factory
from flow_tracer_api.main import create_app
from flow_tracer_api.schemas import GatewayResult
from flow_tracer_api.services.payload_validation import SCHEMA_VERSION
from flow_tracer_api.services.ports import OdooGateway, OdooGatewayError
from tests.fixtures import load_fixture
from tests.settings import make_settings
from tests.unit.fakes import FakeOdooGateway, answer_for

pytestmark = pytest.mark.integration

CONFIRM = {"entrypoint_model": "sale.order", "entrypoint_method": "action_confirm"}


def _settings(**overrides: object) -> Settings:
    return make_settings(**overrides)


@pytest.fixture
async def make_client(
    migrated_engine: AsyncEngine,
) -> AsyncIterator[Callable[..., AsyncClient]]:
    factory = async_sessionmaker(migrated_engine, expire_on_commit=False)

    def _make(gateway: OdooGateway | None = None, settings: Settings | None = None) -> AsyncClient:
        settings = settings or _settings()
        app: FastAPI = create_app(settings)
        app.dependency_overrides[get_session_factory] = lambda: factory
        app.dependency_overrides[get_odoo_gateway] = lambda: gateway
        app.dependency_overrides[get_settings] = lambda: settings
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    yield _make

    async with migrated_engine.begin() as conn:
        await conn.execute(text("TRUNCATE traces"))


async def test_start_trace_returns_201_with_stored_trace(make_client) -> None:
    payload = load_fixture("trace-small")
    gateway = FakeOdooGateway(GatewayResult(payload=payload, odoo_version="19.0"))
    async with make_client(gateway) as client:
        response = await client.post("/traces", json={**CONFIRM, "record_ids": [1]})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["dry_run"] is True
    assert body["payload"] == answer_for(gateway.requests[0], payload)
    assert body["schema_version"] == SCHEMA_VERSION
    assert body["odoo_version"] == "19.0"
    assert gateway.requests[0].record_ids == (1,)


async def test_failed_recording_is_still_created(make_client) -> None:
    gateway = FakeOdooGateway(error=OdooGatewayError("Odoo unreachable"))
    async with make_client(gateway) as client:
        response = await client.post("/traces", json=CONFIRM)

    assert response.status_code == 201
    assert response.json()["status"] == "failed"
    assert response.json()["error"] == "Odoo unreachable"


async def test_start_trace_without_odoo_connection_is_503(make_client) -> None:
    async with make_client(gateway=None) as client:
        response = await client.post("/traces", json=CONFIRM)
        listed = await client.get("/traces")

    assert response.status_code == 503
    assert "No connection to Odoo" in response.json()["detail"]
    assert listed.json()["total"] == 0  # nothing was written


async def test_non_dry_run_is_403_unless_enabled(make_client) -> None:
    body = {**CONFIRM, "dry_run": False}
    async with make_client(FakeOdooGateway()) as client:
        forbidden = await client.post("/traces", json=body)
    async with make_client(FakeOdooGateway(), _settings(allow_non_dry_run=True)) as client:
        allowed = await client.post("/traces", json=body)

    assert forbidden.status_code == 403
    assert "dry_run=false is disabled" in forbidden.json()["detail"]
    assert allowed.status_code == 201
    assert allowed.json()["dry_run"] is False


async def test_invalid_body_is_422(make_client) -> None:
    async with make_client(FakeOdooGateway()) as client:
        response = await client.post("/traces", json={"entrypoint_model": ""})

    assert response.status_code == 422


async def test_get_list_delete_roundtrip(make_client) -> None:
    async with make_client(FakeOdooGateway()) as client:
        created = (await client.post("/traces", json=CONFIRM)).json()
        await client.post(
            "/traces", json={"entrypoint_model": "account.move", "entrypoint_method": "action_post"}
        )

        fetched = await client.get(f"/traces/{created['id']}")
        assert fetched.status_code == 200
        assert fetched.json() == created

        page = await client.get("/traces", params={"entrypoint_model": "sale.order"})
        assert page.status_code == 200
        assert page.json()["total"] == 1
        assert [item["id"] for item in page.json()["items"]] == [created["id"]]
        assert "payload" not in page.json()["items"][0]

        everything = await client.get("/traces", params={"limit": 1})
        assert everything.json()["total"] == 2
        assert len(everything.json()["items"]) == 1

        deleted = await client.delete(f"/traces/{created['id']}")
        assert deleted.status_code == 204
        assert (await client.get(f"/traces/{created['id']}")).status_code == 404


async def test_unknown_trace_is_404(make_client) -> None:
    async with make_client() as client:
        missing = uuid.uuid4()
        not_found = await client.get(f"/traces/{missing}")
        assert not_found.status_code == 404
        assert not_found.json() == {"detail": f"Trace {missing} not found"}
        assert (await client.delete(f"/traces/{missing}")).status_code == 404
        assert (await client.get("/traces/not-a-uuid")).status_code == 422


async def test_list_query_is_validated(make_client) -> None:
    async with make_client() as client:
        assert (await client.get("/traces", params={"limit": 0})).status_code == 422
        assert (await client.get("/traces", params={"status": "bogus"})).status_code == 422


async def test_openapi_documents_trace_endpoints(make_client) -> None:
    async with make_client() as client:
        spec = (await client.get("/openapi.json")).json()

    assert set(spec["paths"]) >= {"/health", "/traces", "/traces/{trace_id}"}
    assert {"post", "get"} <= set(spec["paths"]["/traces"])
    assert "404" in spec["paths"]["/traces/{trace_id}"]["get"]["responses"]


async def test_start_trace_passes_kwargs(make_client) -> None:
    gateway = FakeOdooGateway()
    async with make_client(gateway) as client:
        response = await client.post(
            "/traces",
            json={
                "entrypoint_model": "res.partner",
                "entrypoint_method": "name_create",
                "kwargs": {"name": "Grace Hopper"},
            },
        )

    assert response.status_code == 201, response.text
    assert gateway.requests[0].call_kwargs == {"name": "Grace Hopper"}
    assert response.json()["payload"]["entrypoint"]["kwargs"] == {"name": "Grace Hopper"}
