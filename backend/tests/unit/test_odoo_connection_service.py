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
        addon_status: dict[str, Any] | None = None,
        neutralized: bool = True,
    ) -> None:
        self.addon_status = addon_status or {
            "addon_version": "19.0.0.3.0",
            "odoo_version": serie,
            "enabled": True,
            "is_admin": True,
            "recorder_available": True,
        }
        self.neutralized = neutralized
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
        if (model, method) == ("ir.ui.view", "search_count"):
            assert kwargs["domain"] == [
                ["key", "=", "web.neutralize_banner"],
                ["active", "=", True],
            ]
            return 1 if self.neutralized else 0
        raise AssertionError(f"unexpected call {model}.{method}")

    async def post(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        timeout_seconds: float | None = None,
        target: str | None = None,
    ) -> Any:
        self.calls.append(("POST", path))
        if error := self.call_errors.get(path):
            raise error
        assert path == "/flow_tracer/v1/status"
        return self.addon_status


async def _check(client: FakeOdooClient | None, **kwargs: Any) -> Any:
    typed: OdooClient | None = client  # fakes must satisfy the port
    service = OdooConnectionService(typed, url="http://odoo:8069", database="dev", **kwargs)
    return await service.check()


async def test_healthy_connection_is_ok() -> None:
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
    assert status.tracing_enabled is True
    assert status.recorder_available is True
    assert status.user_is_admin is True
    assert status.database_neutralized is True
    assert status.warnings == []


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


@pytest.mark.parametrize(
    ("addon_status", "expected"),
    [
        ({"enabled": False, "recorder_available": True, "is_admin": True}, "switched off"),
        ({"enabled": True, "recorder_available": False, "is_admin": True}, "Python 3.12+"),
        (
            {"enabled": True, "recorder_available": True, "is_admin": False},
            "Settings (Administration)",
        ),
    ],
)
async def test_addon_status_problems(addon_status: dict[str, Any], expected: str) -> None:
    status = await _check(FakeOdooClient(addon_status=addon_status))

    assert status.ok is False
    assert len(status.problems) == 1
    assert expected in status.problems[0]


async def test_addon_status_not_queried_when_addon_missing() -> None:
    client = FakeOdooClient(addon_state=None)

    status = await _check(client)

    assert ("POST", "/flow_tracer/v1/status") not in client.calls
    assert status.tracing_enabled is False


async def test_addon_status_failure_is_reported() -> None:
    error = OdooCallError("flow_tracer status failed with HTTP 404: no details")
    client = FakeOdooClient(call_errors={"/flow_tracer/v1/status": error})

    status = await _check(client)

    assert status.ok is False
    assert status.problems == [f"Could not read the flow_tracer status: {error.message}"]


async def test_not_neutralised_database_is_a_warning_not_a_problem() -> None:
    status = await _check(FakeOdooClient(neutralized=False))

    assert status.ok is True
    assert status.database_neutralized is False
    assert len(status.warnings) == 1
    assert "not neutralised" in status.warnings[0]


async def test_neutralisation_check_failure_is_a_warning() -> None:
    error = OdooCallError("ir.ui.view.search_count failed with HTTP 403: Access Denied")
    client = FakeOdooClient(call_errors={"ir.ui.view.search_count": error})

    status = await _check(client)

    assert status.ok is True
    assert status.database_neutralized is None
    assert status.warnings == [
        f"Could not check whether the database is neutralised: {error.message}"
    ]
