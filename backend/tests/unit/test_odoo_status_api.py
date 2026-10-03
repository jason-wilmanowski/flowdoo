"""GET /odoo/status through FastAPI DI, with the Odoo client replaced by a fake."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from flow_tracer_api.api.dependencies import get_odoo_client, get_odoo_gateway
from flow_tracer_api.core.config import Settings, get_settings
from flow_tracer_api.integrations.odoo import FlowTracerGateway, OdooJson2Client
from flow_tracer_api.main import create_app
from tests.settings import make_settings
from tests.unit.test_odoo_connection_service import FakeOdooClient

API_KEY = "very-secret-api-key"


def _settings(**odoo: object) -> Settings:
    return make_settings(**odoo)


CONFIGURED = {
    "odoo_url": "http://odoo:8069",
    "odoo_db": "dev",
    "odoo_login": "admin",
    "odoo_api_key": SecretStr(API_KEY),
}


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    settings = _settings(**CONFIGURED)
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_odoo_client] = lambda: FakeOdooClient(addon_state=None)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def test_status_reports_checks_and_problems(client: AsyncClient) -> None:
    response = await client.get("/odoo/status")

    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is True
    assert body["reachable"] is True
    assert body["server_version"] == "19.0-20260926"
    assert body["authenticated"] is True
    assert body["user_login"] == "admin"
    assert body["addon_installed"] is False
    assert body["ok"] is False
    assert "flow_tracer addon is not available" in body["problems"][0]
    assert body["url"] == "http://odoo:8069/"
    assert API_KEY not in response.text


async def test_status_when_odoo_is_not_configured() -> None:
    settings = _settings()
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/odoo/status")

    assert response.status_code == 200
    assert response.json()["configured"] is False
    assert response.json()["ok"] is False


async def test_real_client_is_built_from_settings_and_closed() -> None:
    settings = _settings(**CONFIGURED)
    dependency = get_odoo_client(settings)

    odoo_client = await anext(dependency)
    assert isinstance(odoo_client, OdooJson2Client)
    with pytest.raises(StopAsyncIteration):
        await anext(dependency)

    assert odoo_client._http.is_closed  # the HTTP connection pool is released


async def test_gateway_is_built_on_the_request_client() -> None:
    settings = _settings(**CONFIGURED)
    client = OdooJson2Client(base_url="http://odoo:8069", database="dev", api_key="k")

    gateway = get_odoo_gateway(client, settings)

    assert isinstance(gateway, FlowTracerGateway)
    assert get_odoo_gateway(None, settings) is None
    await client.aclose()


async def test_entrypoint_signature_endpoint() -> None:
    from tests.unit.test_entrypoint_service import SIGNATURE, SignatureClient

    settings = _settings(**CONFIGURED)
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_odoo_client] = lambda: SignatureClient()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/odoo/entrypoints/res.partner/write")

    assert response.status_code == 200
    assert response.json() == SIGNATURE


async def test_entrypoint_signature_endpoint_passes_404_on() -> None:
    from flow_tracer_api.integrations.odoo import OdooCallError
    from tests.unit.test_entrypoint_service import SignatureClient

    settings = _settings(**CONFIGURED)
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_odoo_client] = lambda: SignatureClient(
        error=OdooCallError("The method 'res.partner.nope' does not exist", 404)
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/odoo/entrypoints/res.partner/nope")

    assert response.status_code == 404
    assert response.json() == {"detail": "The method 'res.partner.nope' does not exist"}
