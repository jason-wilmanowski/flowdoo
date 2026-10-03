"""Checks whether the configured Odoo can be used for tracing (CLAUDE.md section 3)."""

from flow_tracer_api.integrations.odoo import (
    OdooAuthenticationError,
    OdooClientError,
    OdooDatabaseNotFoundError,
)
from flow_tracer_api.schemas import OdooConnectionStatus
from flow_tracer_api.services.ports import OdooClient

SUPPORTED_ODOO_SERIE = "19.0"
ADDON_NAME = "flow_tracer"
ADDON_STATUS_ROUTE = "/flow_tracer/v1/status"
NEUTRALIZE_BANNER = "web.neutralize_banner"


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
            return OdooConnectionStatus(
                configured=False,
                problems=[
                    "Odoo connection is not configured: set ODOO_URL, ODOO_DB and ODOO_API_KEY"
                ],
            )
        client = self._client
        status = OdooConnectionStatus(configured=True, url=self._url, database=self._database)
        problems: list[str] = []
        warnings: list[str] = []

        def finish() -> OdooConnectionStatus:
            return status.model_copy(
                update={"ok": not problems, "problems": problems, "warnings": warnings}
            )

        # 1. Reachable and the right Odoo version (no database or key needed).
        try:
            version = await client.version_info()
        except OdooClientError as exc:
            problems.append(exc.message)
            return finish()
        supported = version.server_serie == SUPPORTED_ODOO_SERIE
        status = status.model_copy(
            update={
                "reachable": True,
                "server_version": version.server_version,
                "version_supported": supported,
            }
        )
        if not supported:
            problems.append(
                f"Odoo {version.server_serie} is not supported; "
                f"Odoo Flow Tracer only works with Odoo {SUPPORTED_ODOO_SERIE}"
            )

        # 2. Database served and API key accepted.
        try:
            context = await client.call("res.users", "context_get")
            uid = int(context["uid"])
            [user] = await client.call("res.users", "read", ids=[uid], fields=["login"])
        except (OdooAuthenticationError, OdooDatabaseNotFoundError) as exc:
            problems.append(exc.message)
            return finish()
        except OdooClientError as exc:
            problems.append(f"Could not identify the API key's user: {exc.message}")
            return finish()
        status = status.model_copy(update={"authenticated": True, "user_login": user["login"]})
        if self._expected_login and user["login"] != self._expected_login:
            problems.append(
                f"The API key belongs to {user['login']!r}, but ODOO_LOGIN is "
                f"{self._expected_login!r}"
            )

        # 3. Recorder addon installed.
        try:
            modules = await client.call(
                "ir.module.module",
                "search_read",
                domain=[["name", "=", ADDON_NAME]],
                fields=["state"],
            )
        except OdooClientError as exc:
            problems.append(f"Could not check the {ADDON_NAME} addon: {exc.message}")
            return finish()
        state = modules[0]["state"] if modules else None
        status = status.model_copy(
            update={"addon_state": state, "addon_installed": state == "installed"}
        )
        if state is None:
            problems.append(
                f"The {ADDON_NAME} addon is not available in this Odoo: add "
                f"odoo-addons/{ADDON_NAME} to the addons path and install it"
            )
        elif state != "installed":
            problems.append(f"The {ADDON_NAME} addon is not installed (state: {state})")

        # 4. The addon's server switch (the "dev flag"), recorder and the key's rights.
        if state == "installed":
            try:
                addon = await client.post(ADDON_STATUS_ROUTE, {}, target=f"{ADDON_NAME} status")
            except OdooClientError as exc:
                problems.append(f"Could not read the {ADDON_NAME} status: {exc.message}")
                return finish()
            enabled = addon.get("enabled") is True
            recorder = addon.get("recorder_available") is True
            admin = addon.get("is_admin") is True
            status = status.model_copy(
                update={
                    "tracing_enabled": enabled,
                    "recorder_available": recorder,
                    "user_is_admin": admin,
                }
            )
            if not enabled:
                problems.append(
                    "Tracing is switched off on the Odoo server: set "
                    "flow_tracer_enabled = True in its configuration (development servers only)"
                )
            if not recorder:
                problems.append(
                    f"The {ADDON_NAME} recorder is not available on the Odoo server "
                    "(it needs Python 3.12+)"
                )
            if not admin:
                problems.append(
                    "The API key's user must be in the Settings (Administration) group to trace"
                )

        # 5. Neutralised database? `odoo neutralize` activates the web.neutralize_banner view.
        try:
            banners = await client.call(
                "ir.ui.view",
                "search_count",
                domain=[["key", "=", NEUTRALIZE_BANNER], ["active", "=", True]],
            )
        except OdooClientError as exc:
            warnings.append(f"Could not check whether the database is neutralised: {exc.message}")
        else:
            neutralized = bool(banners)
            status = status.model_copy(update={"database_neutralized": neutralized})
            if not neutralized:
                warnings.append(
                    "The database is not neutralised (odoo neutralize): mail servers, crons "
                    "and payment providers stay active while tracing"
                )
        return finish()
