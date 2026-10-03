"""Fixtures for tests against the real Odoo 19 test container (pytest marker ``odoo``).

Needs ODOO_TEST_URL, ODOO_TEST_DB and ODOO_TEST_API_KEY (environment or .env), see
README.md in this folder. Without them the tests are skipped with an explicit reason.
"""

from collections.abc import AsyncIterator

import pytest
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from flow_tracer_api.integrations.odoo import OdooJson2Client


class OdooTestSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ODOO_TEST_", env_file=("../.env", ".env"), extra="ignore"
    )

    url: str | None = None
    db: str | None = None
    api_key: SecretStr | None = None


@pytest.fixture(scope="session")
def odoo_test_settings() -> OdooTestSettings:
    settings = OdooTestSettings()
    if not (settings.url and settings.db and settings.api_key):
        pytest.skip("Test Odoo not configured: set ODOO_TEST_URL, ODOO_TEST_DB, ODOO_TEST_API_KEY")
    return settings


def make_client(
    settings: OdooTestSettings, *, database: str | None = None, api_key: str | None = None
) -> OdooJson2Client:
    assert settings.url is not None
    assert settings.db is not None
    assert settings.api_key is not None
    return OdooJson2Client(
        base_url=settings.url,
        database=database or settings.db,
        api_key=api_key or settings.api_key.get_secret_value(),
    )


@pytest.fixture
async def odoo_client(odoo_test_settings: OdooTestSettings) -> AsyncIterator[OdooJson2Client]:
    async with make_client(odoo_test_settings) as client:
        yield client
