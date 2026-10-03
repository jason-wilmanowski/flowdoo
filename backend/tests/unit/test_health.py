from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from flow_tracer_api.api.app import create_app
from flow_tracer_api.core.config import Settings


async def test_health_returns_ok() -> None:
    settings = Settings(database_url=SecretStr("postgresql+asyncpg://u:p@localhost:1/x"))
    app = create_app(settings)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
