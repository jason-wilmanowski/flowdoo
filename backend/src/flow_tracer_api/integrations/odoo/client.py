"""Async client for Odoo 19's external JSON-2 API.

* Model calls: ``POST /json/2/<model>/<method>`` with ``Authorization: bearer <api key>``
  and the ``X-Odoo-Database`` header (Odoo 19 ``rpc`` module, ``controllers/json2.py``).
  ``/xmlrpc`` and ``/jsonrpc`` are deprecated in Odoo 19 and are not used.
* Server version: ``/web/webclient/version_info`` (JSON-RPC route of the ``web`` module,
  ``auth="none"``), which returns ``odoo.service.common.exp_version()``.

The API key is only ever placed in the Authorization header; it is never logged and never
part of an error message.
"""

from types import TracebackType
from typing import Any, Self

import httpx

from flow_tracer_api.integrations.odoo.errors import (
    OdooAuthenticationError,
    OdooCallError,
    OdooClientError,
    OdooDatabaseNotFoundError,
    OdooUnreachableError,
)
from flow_tracer_api.schemas import OdooVersionInfo


class OdooJson2Client:
    def __init__(
        self,
        *,
        base_url: str,
        database: str,
        api_key: str,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._database = database
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            transport=transport,
            headers={"Authorization": f"bearer {api_key}", "X-Odoo-Database": database},
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def version_info(self) -> OdooVersionInfo:
        response = await self._post(
            "/web/webclient/version_info",
            {"jsonrpc": "2.0", "method": "call", "params": {}},
        )
        body = _json_or_none(response)
        if response.status_code != httpx.codes.OK or not isinstance(body, dict):
            raise OdooCallError(
                f"Unexpected answer from version_info (HTTP {response.status_code})"
            )
        if "error" in body:
            raise OdooCallError(f"version_info failed: {_error_message(body['error'])}")
        return OdooVersionInfo.model_validate(body.get("result"))

    async def call(
        self,
        model: str,
        method: str,
        *,
        ids: list[int] | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Call ``model.method`` via JSON-2 and return the decoded JSON result."""
        payload: dict[str, Any] = dict(kwargs)
        if ids:
            payload["ids"] = ids
        if context:
            payload["context"] = context
        return await self.post(f"/json/2/{model}/{method}", payload, target=f"{model}.{method}")

    async def post(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        timeout_seconds: float | None = None,
        target: str | None = None,
    ) -> Any:
        """POST a JSON-2 request (bearer key, database header) to ``path``; return the JSON.

        Used for ``/json/2`` model calls and for the flow_tracer addon's own routes.
        """
        response = await self._post(path, payload, timeout_seconds)
        if response.is_success:
            return response.json()
        raise self._error_for(response, target or path)

    async def _post(
        self, path: str, payload: dict[str, Any], timeout_seconds: float | None = None
    ) -> httpx.Response:
        timeout = httpx.USE_CLIENT_DEFAULT if timeout_seconds is None else timeout_seconds
        try:
            return await self._http.post(path, json=payload, timeout=timeout)
        except httpx.TimeoutException as exc:
            raise OdooUnreachableError(
                f"Odoo did not answer in time ({type(exc).__name__})"
            ) from exc
        except httpx.HTTPError as exc:
            raise OdooUnreachableError(f"Cannot reach Odoo: {type(exc).__name__}") from exc

    def _error_for(self, response: httpx.Response, target: str) -> OdooClientError:
        body = _json_or_none(response)
        message = _error_message(body) if isinstance(body, dict) else None
        if response.status_code == httpx.codes.UNAUTHORIZED:
            return OdooAuthenticationError(
                f"Odoo rejected the API key: {message or 'unauthorized'}"
            )
        if response.status_code == httpx.codes.NOT_FOUND and body is None:
            # Odoo answers 404 with an HTML page when no database is selected.
            return OdooDatabaseNotFoundError(
                f"Odoo does not serve database {self._database!r} (or JSON-2 is not available)"
            )
        return OdooCallError(
            f"{target} failed with HTTP {response.status_code}: {message or 'no details'}"
        )


def _json_or_none(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def _error_message(error: dict[str, Any]) -> str:
    # Odoo's serialize_exception(): name, message, arguments, context, debug (traceback).
    # Only "message" is used; the traceback stays out of our responses and logs.
    nested = error.get("data")
    if isinstance(nested, dict) and "message" in nested:  # JSON-RPC error envelope
        return str(nested["message"])
    return str(error.get("message", "unknown error"))
