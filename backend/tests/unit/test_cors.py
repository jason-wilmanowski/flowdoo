"""CORS: only the configured FRONTEND_URL may call the API from a browser."""

from httpx import ASGITransport, AsyncClient

from flow_tracer_api.main import create_app
from tests.settings import FRONTEND_URL, make_settings


def _client() -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=create_app(make_settings())), base_url="http://t"
    )


async def test_frontend_url_is_allowed() -> None:
    async with _client() as client:
        preflight = await client.options(
            "/traces",
            headers={"Origin": FRONTEND_URL, "Access-Control-Request-Method": "POST"},
        )
        simple = await client.get("/health", headers={"Origin": FRONTEND_URL})

    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == FRONTEND_URL
    assert simple.headers["access-control-allow-origin"] == FRONTEND_URL


async def test_other_origins_are_not_allowed() -> None:
    async with _client() as client:
        preflight = await client.options(
            "/traces",
            headers={"Origin": "http://other.test", "Access-Control-Request-Method": "POST"},
        )
        simple = await client.get("/health", headers={"Origin": "http://other.test"})

    assert preflight.status_code == 400
    assert "access-control-allow-origin" not in preflight.headers
    assert "access-control-allow-origin" not in simple.headers
