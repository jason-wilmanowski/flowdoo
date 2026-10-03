"""CORS: the configured frontend origin may call the API, other origins may not."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from flow_tracer_api.api.app import create_app
from flow_tracer_api.core.config import Settings

FRONTEND = "http://localhost:5173"
OTHER = "http://evil.example"


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    settings = Settings(
        database_url=SecretStr("postgresql+asyncpg://u:p@localhost:1/unused"), _env_file=None
    )
    app = create_app(settings)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


def _preflight(origin: str, method: str = "POST") -> dict[str, str]:
    return {
        "Origin": origin,
        "Access-Control-Request-Method": method,
        "Access-Control-Request-Headers": "content-type",
    }


async def test_preflight_from_frontend_is_allowed(client: AsyncClient) -> None:
    response = await client.options("/traces", headers=_preflight(FRONTEND))

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "access-control-allow-credentials" not in response.headers


async def test_preflight_from_other_origin_is_rejected(client: AsyncClient) -> None:
    response = await client.options("/traces", headers=_preflight(OTHER))

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


async def test_preflight_for_unlisted_method_is_rejected(client: AsyncClient) -> None:
    response = await client.options("/traces", headers=_preflight(FRONTEND, method="PUT"))

    assert response.status_code == 400


async def test_simple_request_gets_allow_origin_only_for_frontend(client: AsyncClient) -> None:
    allowed = await client.get("/health", headers={"Origin": FRONTEND})
    other = await client.get("/health", headers={"Origin": OTHER})

    assert allowed.headers["access-control-allow-origin"] == FRONTEND
    assert "access-control-allow-origin" not in other.headers
