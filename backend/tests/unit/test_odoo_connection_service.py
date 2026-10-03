from typing import Any

import pytest

from flow_tracer_api.integrations.odoo import (
    OdooAuthenticationError,
    OdooCallError,
    OdooClientError,
    OdooDatabaseNotFoundError,
    OdooUnreachableError,
)
from flow_tracer_api.schemas import OdooVersionInfo
from flow_tracer_api.services.odoo_connection_service import OdooConnectionService
from flow_tracer_api.services.ports import OdooClient


class FakeOdooClient:
    """Answers like a healthy Odoo 19 with flow_tracer installed, unless told otherwise."""

    def __init__(
        self,
        *,
        serie: str = "19.0",
        login: str = "admin",
        addon_state: str | None = "installed",
        version_error: OdooClientError | None = None,
        call_errors: dict[str, OdooClientError] | None = None,
    ) -> None:
        self.serie = serie
        self.login = login
        self.addon_state = addon_state
        self.version_error = version_error
        self.call_errors = call_errors or {}
        self.calls: list[tuple[str, str]] = []

    async def version_info(self) -> OdooVersionInfo:
        if self.version_error:
            raise self.version_error
        return OdooVersionInfo(server_version=f"{self.serie}-20260926", server_serie=self.serie)

    async def call(
        self,
        model: str,
        method: str,
        *,
        ids: list[int] | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        self.calls.append((model, method))
        if error := self.call_errors.get(f"{model}.{method}"):
            raise error
        if (model, method) == ("res.users", "context_get"):
            return {"lang": "en_US", "tz": False, "uid": 2}
        if (model, method) == ("res.users", "read"):
            assert ids == [2]
            return [{"id": 2, "login": self.login}]
        if (model, method) == ("ir.module.module", "search_read"):
            assert kwargs["domain"] == [["name", "=", "flow_tracer"]]
            return [] if self.addon_state is None else [{"id": 9, "state": self.addon_state}]
        raise AssertionError(f"unexpected call {model}.{method}")

    async def post(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        timeout_seconds: float | None = None,
        target: str | None = None,
    ) -> Any:
        raise AssertionError(f"unexpected POST {path}")


async def _check(client: FakeOdooClient | None, **kwargs: Any) -> Any:
    typed: OdooClient | None = client  # fakes must satisfy the port
    service = OdooConnectionService(typed, url="http://odoo:8069", database="dev", **kwargs)
    return await service.check()


async def test_healthy_connection_is_ok_with_dev_warning() -> None:
    status = await _check(FakeOdooClient(), expected_login="admin")

    assert status.ok is True
    assert status.problems == []
    assert status.reachable is True
    assert status.version_supported is True
    assert status.authenticated is True
    assert status.server_version == "19.0-20260926"
    assert status.user_login == "admin"
    assert status.addon_installed is True
    assert status.url == "http://odoo:8069"
    assert status.database == "dev"
    assert any("production database" in w for w in status.warnings)


async def test_not_configured() -> None:
    status = await _check(None)

    assert status.configured is False
    assert status.ok is False
    assert "set ODOO_URL, ODOO_DB and ODOO_API_KEY" in status.problems[0]


async def test_unreachable_stops_after_first_check() -> None:
    client = FakeOdooClient(version_error=OdooUnreachableError("Cannot reach Odoo: ConnectError"))

    status = await _check(client)

    assert status.ok is False
    assert status.reachable is False
    assert status.problems == ["Cannot reach Odoo: ConnectError"]
    assert client.calls == []


async def test_wrong_version_is_a_problem_but_other_checks_still_run() -> None:
    client = FakeOdooClient(serie="18.0")

    status = await _check(client)

    assert status.version_supported is False
    assert status.authenticated is True
    assert status.problems == [
        "Odoo 18.0 is not supported; Odoo Flow Tracer only works with Odoo 19.0"
    ]


@pytest.mark.parametrize(
    "error",
    [
        OdooAuthenticationError("Odoo rejected the API key: Invalid apikey"),
        OdooDatabaseNotFoundError("Odoo does not serve database 'dev'"),
    ],
)
async def test_auth_or_database_failure_stops(error: OdooClientError) -> None:
    client = FakeOdooClient(call_errors={"res.users.context_get": error})

    status = await _check(client)

    assert status.reachable is True
    assert status.authenticated is False
    assert status.problems == [error.message]
    assert ("ir.module.module", "search_read") not in client.calls


async def test_login_mismatch() -> None:
    status = await _check(FakeOdooClient(login="demo"), expected_login="admin")

    assert status.ok is False
    assert status.problems == ["The API key belongs to 'demo', but ODOO_LOGIN is 'admin'"]


@pytest.mark.parametrize(
    ("addon_state", "expected"),
    [
        (None, "is not available in this Odoo"),
        ("uninstalled", "is not installed (state: uninstalled)"),
        ("to install", "is not installed (state: to install)"),
    ],
)
async def test_addon_missing_or_not_installed(addon_state: str | None, expected: str) -> None:
    status = await _check(FakeOdooClient(addon_state=addon_state))

    assert status.ok is False
    assert status.addon_installed is False
    assert status.addon_state == addon_state
    assert len(status.problems) == 1
    assert expected in status.problems[0]


async def test_addon_check_failure_is_reported() -> None:
    error = OdooCallError("ir.module.module.search_read failed with HTTP 403: Access Denied")
    client = FakeOdooClient(call_errors={"ir.module.module.search_read": error})

    status = await _check(client)

    assert status.ok is False
    assert status.problems == [f"Could not check the flow_tracer addon: {error.message}"]
