"""Checks whether the configured Odoo can be used for tracing (CLAUDE.md section 3)."""

from dataclasses import dataclass, field
from typing import Any

from flow_tracer_api.integrations.odoo import (
    OdooAuthenticationError,
    OdooClientError,
    OdooDatabaseNotFoundError,
)
from flow_tracer_api.schemas import OdooConnectionStatus
from flow_tracer_api.services.common.ports import OdooClient

SUPPORTED_ODOO_SERIE = "19.0"
ADDON_NAME = "flow_tracer"
ADDON_STATUS_ROUTE = "/flow_tracer/v1/status"
NEUTRALIZE_BANNER = "web.neutralize_banner"


@dataclass
class _Findings:
    """What the checks found so far; becomes the connection status once they are done."""

    status: OdooConnectionStatus
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def record(self, **facts: Any) -> None:
        """Add checked facts to the status (it is frozen, so it is replaced)."""
        self.status = self.status.model_copy(update=facts)

    def result(self) -> OdooConnectionStatus:
        return self.status.model_copy(
            update={"ok": not self.problems, "problems": self.problems, "warnings": self.warnings}
        )


class OdooConnectionService:
    def __init__(
        self,
        client: OdooClient | None,
        *,
        url: str | None,
        database: str | None,
        expected_login: str | None = None,
    ) -> None:
        self._client = client
        self._url = url
        self._database = database
        self._expected_login = expected_login

    async def check(self) -> OdooConnectionStatus:
        """Run the checks in order; stop where later checks cannot work any more."""
        if self._client is None:
            return self._not_configured()
        client = self._client
        findings = _Findings(
            OdooConnectionStatus(configured=True, url=self._url, database=self._database)
        )
        for check in (
            self._check_server,
            self._check_user,
            self._check_addon,
            self._check_addon_status,
            self._check_neutralization,
        ):
            if not await check(client, findings):
                break
        return findings.result()

    # Each check records what it found and returns whether the later checks can still run.

    @staticmethod
    def _not_configured() -> OdooConnectionStatus:
        return OdooConnectionStatus(
            configured=False,
            problems=["Odoo connection is not configured: set ODOO_URL, ODOO_DB and ODOO_API_KEY"],
        )

    async def _check_server(self, client: OdooClient, findings: _Findings) -> bool:
        """Reachable and the right Odoo version (no database or key needed)."""
        try:
            version = await client.version_info()
        except OdooClientError as exc:
            findings.problems.append(exc.message)
            return False
        supported = version.server_serie == SUPPORTED_ODOO_SERIE
        findings.record(
            reachable=True, server_version=version.server_version, version_supported=supported
        )
        if not supported:
            findings.problems.append(
                f"Odoo {version.server_serie} is not supported; "
                f"Odoo Flow Tracer only works with Odoo {SUPPORTED_ODOO_SERIE}"
            )
        return True

    async def _check_user(self, client: OdooClient, findings: _Findings) -> bool:
        """Database served and API key accepted, for the expected user."""
        try:
            login = await self._fetch_login(client)
        except (OdooAuthenticationError, OdooDatabaseNotFoundError) as exc:
            findings.problems.append(exc.message)
            return False
        except OdooClientError as exc:
            findings.problems.append(f"Could not identify the API key's user: {exc.message}")
            return False
        findings.record(authenticated=True, user_login=login)
        if self._expected_login and login != self._expected_login:
            findings.problems.append(
                f"The API key belongs to {login!r}, but ODOO_LOGIN is {self._expected_login!r}"
            )
        return True

    @staticmethod
    async def _fetch_login(client: OdooClient) -> str:
        """Login of the user the API key belongs to."""
        context = await client.call("res.users", "context_get")
        uid = int(context["uid"])
        [user] = await client.call("res.users", "read", ids=[uid], fields=["login"])
        login: str = user["login"]
        return login

    async def _check_addon(self, client: OdooClient, findings: _Findings) -> bool:
        """Recorder addon present and installed."""
        try:
            modules = await client.call(
                "ir.module.module",
                "search_read",
                domain=[["name", "=", ADDON_NAME]],
                fields=["state"],
            )
        except OdooClientError as exc:
            findings.problems.append(f"Could not check the {ADDON_NAME} addon: {exc.message}")
            return False
        state = modules[0]["state"] if modules else None
        findings.record(addon_state=state, addon_installed=state == "installed")
        if state is None:
            findings.problems.append(
                f"The {ADDON_NAME} addon is not available in this Odoo: add "
                f"odoo-addons/{ADDON_NAME} to the addons path and install it"
            )
        elif state != "installed":
            findings.problems.append(f"The {ADDON_NAME} addon is not installed (state: {state})")
        return True

    async def _check_addon_status(self, client: OdooClient, findings: _Findings) -> bool:
        """The addon's server switch (the "dev flag"), recorder and the key's rights.

        Only an installed addon can answer, so this is skipped otherwise.
        """
        if not findings.status.addon_installed:
            return True
        try:
            addon = await client.post(ADDON_STATUS_ROUTE, {}, target=f"{ADDON_NAME} status")
        except OdooClientError as exc:
            findings.problems.append(f"Could not read the {ADDON_NAME} status: {exc.message}")
            return False
        enabled = addon.get("enabled") is True
        recorder = addon.get("recorder_available") is True
        admin = addon.get("is_admin") is True
        findings.record(tracing_enabled=enabled, recorder_available=recorder, user_is_admin=admin)
        if not enabled:
            findings.problems.append(
                "Tracing is switched off on the Odoo server: set "
                "flow_tracer_enabled = True in its configuration (development servers only)"
            )
        if not recorder:
            findings.problems.append(
                f"The {ADDON_NAME} recorder is not available on the Odoo server "
                "(it needs Python 3.12+)"
            )
        if not admin:
            findings.problems.append(
                "The API key's user must be in the Settings (Administration) group to trace"
            )
        return True

    async def _check_neutralization(self, client: OdooClient, findings: _Findings) -> bool:
        """Neutralised database? `odoo neutralize` activates the web.neutralize_banner view.

        Only ever a warning: tracing works either way.
        """
        try:
            banners = await client.call(
                "ir.ui.view",
                "search_count",
                domain=[["key", "=", NEUTRALIZE_BANNER], ["active", "=", True]],
            )
        except OdooClientError as exc:
            findings.warnings.append(
                f"Could not check whether the database is neutralised: {exc.message}"
            )
            return True
        neutralized = bool(banners)
        findings.record(database_neutralized=neutralized)
        if not neutralized:
            findings.warnings.append(
                "The database is not neutralised (odoo neutralize): mail servers, crons "
                "and payment providers stay active while tracing"
            )
        return True
