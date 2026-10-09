"""Odoo client and connection check against the real Odoo 19 test container."""

import pytest

from flow_tracer_api.integrations.odoo import (
    OdooAuthenticationError,
    OdooCallError,
    OdooDatabaseNotFoundError,
    OdooJson2Client,
)
from flow_tracer_api.services.odoo_connection_service import OdooConnectionService
from tests.integration.odoo.conftest import OdooTestSettings, make_client

pytestmark = pytest.mark.odoo


async def test_version_is_odoo_19(odoo_client: OdooJson2Client) -> None:
    info = await odoo_client.version_info()

    assert info.server_serie == "19.0"


async def test_json2_call_returns_api_key_user(odoo_client: OdooJson2Client) -> None:
    context = await odoo_client.call("res.users", "context_get")
    [user] = await odoo_client.call("res.users", "read", ids=[context["uid"]], fields=["login"])

    assert user["login"] == "admin"


async def test_unknown_model_is_a_call_error(odoo_client: OdooJson2Client) -> None:
    with pytest.raises(OdooCallError, match="does not exist"):
        await odoo_client.call("no.such.model", "search_read")


async def test_wrong_api_key_is_rejected(odoo_test_settings: OdooTestSettings) -> None:
    async with make_client(odoo_test_settings, api_key="wrong-key") as client:
        with pytest.raises(OdooAuthenticationError, match="Invalid apikey"):
            await client.call("res.users", "context_get")


async def test_unknown_database_is_detected(odoo_test_settings: OdooTestSettings) -> None:
    async with make_client(odoo_test_settings, database="no_such_db") as client:
        with pytest.raises(OdooDatabaseNotFoundError, match="no_such_db"):
            await client.call("res.users", "context_get")


async def test_connection_check_passes_with_addon_installed(
    odoo_client: OdooJson2Client, odoo_test_settings: OdooTestSettings
) -> None:
    service = OdooConnectionService(
        odoo_client,
        url=odoo_test_settings.url,
        database=odoo_test_settings.db,
        expected_login="admin",
    )

    status = await service.check()

    assert status.reachable is True
    assert status.version_supported is True
    assert status.authenticated is True
    assert status.user_login == "admin"
    assert status.addon_installed is True
    assert status.addon_state == "installed"
    # docker/odoo-test/odoo.conf switches tracing on; the image runs Python 3.12
    assert status.tracing_enabled is True
    assert status.recorder_available is True
    assert status.user_is_admin is True
    assert status.problems == []
    assert status.ok is True
    # The test database is not neutralised: a warning, not a problem.
    assert status.database_neutralized is False
    assert len(status.warnings) == 1


async def test_entrypoint_signature_from_the_addon(odoo_client: OdooJson2Client) -> None:
    from flow_tracer_api.services.entrypoint_service import EntrypointService

    service = EntrypointService(odoo_client)

    write = await service.describe("res.partner", "write")
    name_create = await service.describe("res.partner", "name_create")

    assert [(p.name, p.required) for p in write.parameters] == [("vals", True)]
    assert write.model_level is False
    assert name_create.model_level is True
    assert [p.name for p in name_create.parameters] == ["name"]


async def test_model_registry_from_the_addon(odoo_client: OdooJson2Client) -> None:
    from flow_tracer_api.services.registry_service import RegistryService

    service = RegistryService(odoo_client)

    listing = await service.list_models()
    partner = next(m for m in listing.models if m.model == "res.partner")
    assert partner.module == "base"
    assert any(r.field == "parent_id" and r.target == "res.partner" for r in partner.relations)

    detail = await service.describe_model("res.partner")
    assert {f.name for f in detail.fields} >= {"name", "parent_id", "child_ids"}
