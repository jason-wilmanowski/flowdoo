"""Settings for tests: no .env file, dummy values for everything required."""

from typing import Any

from pydantic import SecretStr

from flow_tracer_api.core.config import Settings

FRONTEND_URL = "http://frontend.test:5173"


def make_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "database_url": SecretStr("postgresql+asyncpg://u:p@localhost:1/unused"),
        "frontend_url": FRONTEND_URL,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)
