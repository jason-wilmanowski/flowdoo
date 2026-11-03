"""Can this Odoo be traced? The essential checks of the backend's connection service."""

from flow_tracer_api.integrations.odoo.client import OdooJson2Client
from flow_tracer_api.integrations.odoo.errors import OdooClientError
from pydantic import BaseModel, Field

SUPPORTED_ODOO_SERIE = "19.0"
ADDON_STATUS_ROUTE = "/flow_tracer/v1/status"
NEUTRALIZE_BANNER = "web.neutralize_banner"


class OdooStatus(BaseModel):
    ok: bool = False
    server_version: str | None = None
    user_login: str | None = None
    tracing_enabled: bool = False
    recorder_available: bool = False
    user_is_admin: bool = False
    # None if it could not be checked.
    database_neutralized: bool | None = None
    problems: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


async def check_status(client: OdooJson2Client, expected_login: str | None = None) -> OdooStatus:
    """Run the checks in order; stop where later checks cannot work any more."""
    status = OdooStatus()
    if (
        await _check_server(client, status)
        and await _check_user(client, status, expected_login)
        and await _check_addon(client, status)
    ):
        await _check_neutralization(client, status)
    status.ok = not status.problems
    return status


async def _check_server(client: OdooJson2Client, status: OdooStatus) -> bool:
    try:
        version = await client.version_info()
    except OdooClientError as exc:
        status.problems.append(exc.message)
        return False
    status.server_version = version.server_version
    if version.server_serie != SUPPORTED_ODOO_SERIE:
        status.problems.append(
            f"Odoo {version.server_serie} is not supported, only {SUPPORTED_ODOO_SERIE}"
        )
    return True


async def _check_user(
    client: OdooJson2Client, status: OdooStatus, expected_login: str | None
) -> bool:
    """Database served and API key accepted, for the expected user."""
    try:
        context = await client.call("res.users", "context_get")
        [user] = await client.call("res.users", "read", ids=[context["uid"]], fields=["login"])
    except OdooClientError as exc:
        status.problems.append(exc.message)
        return False
    status.user_login = user["login"]
    if expected_login and status.user_login != expected_login:
        status.problems.append(
            f"The API key belongs to {status.user_login!r}, but ODOO_LOGIN is {expected_login!r}"
        )
    return True


async def _check_addon(client: OdooJson2Client, status: OdooStatus) -> bool:
    try:
        addon = await client.post(ADDON_STATUS_ROUTE, {}, target="flow_tracer status")
    except OdooClientError as exc:
        status.problems.append(f"{exc.message}; is the flow_tracer addon installed?")
        return False
    status.tracing_enabled = addon.get("enabled") is True
    status.recorder_available = addon.get("recorder_available") is True
    status.user_is_admin = addon.get("is_admin") is True
    if not status.tracing_enabled:
        status.problems.append(
            "Tracing is switched off on the Odoo server: set flow_tracer_enabled = True "
            "in its configuration (development servers only)"
        )
    if not status.recorder_available:
        status.problems.append("The flow_tracer recorder needs Python 3.12+ on the Odoo server")
    if not status.user_is_admin:
        status.problems.append(
            "The API key's user must be in the Settings (Administration) group to trace"
        )
    return True


async def _check_neutralization(client: OdooJson2Client, status: OdooStatus) -> None:
    """`odoo neutralize` activates the web.neutralize_banner view."""
    try:
        banners = await client.call(
            "ir.ui.view",
            "search_count",
            domain=[["key", "=", NEUTRALIZE_BANNER], ["active", "=", True]],
        )
    except OdooClientError as exc:
        status.warnings.append(
            f"Could not check whether the database is neutralised: {exc.message}"
        )
        return
    status.database_neutralized = bool(banners)
    if not banners:
        status.warnings.append(
            "The database is not neutralised (odoo neutralize): mail servers, crons and "
            "payment providers stay active, and run_trace refuses to run"
        )
